"use strict";

import { readFileSync } from "node:fs";
import { randomUUID } from "node:crypto";
import { chromium } from "@playwright/test";

const origin = process.argv[2];
const credential = readFileSync(0, "utf8");
let browser;
let stage = "browser_launch";

try {
  browser = await chromium.launch({ channel: "chrome", headless: true });
  const page = await browser.newPage({ baseURL: origin, viewport: { width: 1280, height: 800 } });
  page.setDefaultTimeout(10_000);
  let signInMutations = 0;
  let statusReads = 0;
  page.on("request", (request) => {
    const path = new URL(request.url()).pathname;
    if (path.startsWith("/api/v1/accounts/") && path.endsWith("/connection")) {
      if (request.method() === "GET") statusReads += 1;
      else signInMutations += 1;
    }
  });

  stage = "login";
  await page.goto(`${origin}/login`);
  await page.getByLabel("Administrator password").fill(credential);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await page.getByRole("heading", { name: "AgentMonitor", exact: true }).waitFor();

  stage = "pending_account";
  await page.getByRole("button", { name: "Accounts", exact: true }).click();
  await page.getByLabel("Provider key").fill("claude");
  const name = `Connection browser record ${randomUUID()}`;
  await page.getByLabel("Account name").fill(name);
  await page.getByRole("button", { name: "Add account", exact: true }).click();
  const card = page.getByRole("article").filter({ has: page.getByText(name, { exact: true }) });
  await card.getByText("pending · monitoring disabled", { exact: true }).waitFor();

  stage = "pending_connect_control";
  await card.getByRole("button", { name: "Connect Claude", exact: true }).click();
  await page.getByRole("heading", { name, exact: true }).waitFor();
  const panel = page.getByRole("region", { name: "Connect Claude", exact: true });
  await panel.waitFor();

  stage = "connection_status";
  await panel.getByText("Ready to connect", { exact: true }).waitFor();
  const email = panel.getByLabel("Claude account email", { exact: true });
  if (await email.inputValue() !== "") throw new Error("non_email_label_used_as_identity");
  if (await email.getAttribute("type") !== "email") throw new Error("email_input_missing");
  const connect = panel.getByRole("button", { name: "Connect Claude", exact: true });
  if (!await connect.isDisabled()) throw new Error("empty_identity_can_start_sign_in");
  await email.fill("not an email");
  if (!await connect.isDisabled()) throw new Error("invalid_identity_can_start_sign_in");
  // This local form value is never submitted or represented as a provider account.
  await email.fill("owner@invalid.example");
  if (!await connect.isEnabled()) throw new Error("valid_identity_cannot_be_selected");
  await page.waitForTimeout(2_200);
  if (signInMutations !== 0) throw new Error("sign_in_started_without_explicit_owner_action");
  if (statusReads !== 1) throw new Error("idle_connection_polled_automatically");
  await Promise.all([
    page.waitForResponse((response) => new URL(response.url()).pathname.endsWith("/connection") && response.request().method() === "GET" && response.status() === 200),
    panel.getByRole("button", { name: "Check connection status", exact: true }).click(),
  ]);
  if (statusReads !== 2) throw new Error("manual_status_check_missing");

  stage = "pending_quota_overview";
  await page.getByRole("button", { name: "Overview", exact: true }).click();
  const overview = page.getByRole("table", { name: "Account quota overview", exact: true });
  await overview.waitFor();
  const pendingRow = overview.getByRole("row").filter({ hasText: name });
  stage = "pending_overview_state";
  await pendingRow.getByText("Not connected", { exact: true }).waitFor();
  stage = "pending_overview_empty_quota";
  await pendingRow.getByText("No reading yet", { exact: true }).first().waitFor();
  if (await pendingRow.getByRole("meter").count() !== 0) throw new Error("pending_account_has_invented_quota");
  stage = "pending_overview_detail_navigation";
  await pendingRow.getByRole("button", { name: `Open account ${name}`, exact: true }).click();
  await page.getByRole("heading", { name, exact: true }).waitFor();

  stage = "responsive";
  await page.setViewportSize({ width: 390, height: 844 });
  if (await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1)) throw new Error("horizontal_overflow");

  stage = "archived_account_protection";
  await page.getByRole("button", { name: "Edit account", exact: true }).click();
  await page.getByRole("button", { name: "Archive account", exact: true }).click();
  await page.getByRole("button", { name: "Restore account", exact: true }).waitFor();
  await page.getByRole("button", { name: "Connect Claude", exact: true }).waitFor({ state: "detached" });
  if (signInMutations !== 0) throw new Error("sign_in_started_during_navigation");
  await browser.close();
  console.log("P02 CLAUDE CONNECTION: PASSED — real admin/API/browser, explicit action required; provider sign-in not started");
} catch (error) {
  if (browser) await browser.close();
  const reason = error instanceof Error && /^[a-z_]+$/.test(error.message)
    ? error.message
    : error instanceof Error && error.name === "TimeoutError" ? "control_timeout" : "browser_error";
  console.error(`P02 CLAUDE CONNECTION: FAILED — ${stage}: ${reason}`);
  process.exitCode = 1;
}
