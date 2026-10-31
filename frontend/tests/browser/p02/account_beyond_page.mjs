"use strict";

import { readFileSync } from "node:fs";
import { chromium } from "@playwright/test";

const origin = process.argv[2];
const credential = readFileSync(0, "utf8");
let browser;
let stage = "browser_launch";

function requireTruth(condition, reason) {
  if (!condition) throw new Error(reason);
}

try {
  browser = await chromium.launch({ channel: "chrome", headless: true });
  const page = await browser.newPage({ baseURL: origin, viewport: { width: 1280, height: 800 } });
  stage = "login";
  await page.goto(`${origin}/login`);
  await page.getByLabel("Administrator password").fill(credential);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.getByRole("heading", { name: "AgentMonitor", exact: true }).waitFor();

  stage = "create_real_accounts";
  const targetAccount = await page.evaluate(async () => {
    const csrf = document.cookie
      .split(";")
      .map((entry) => entry.trim())
      .find((entry) => entry.startsWith("agentmonitor_csrf="))
      ?.slice("agentmonitor_csrf=".length);
    if (!csrf) throw new Error("csrf_cookie_missing");
    let lastCreated = null;
    for (let index = 0; index < 201; index += 1) {
      const response = await fetch("/api/v1/accounts", {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          "Idempotency-Key": crypto.randomUUID(),
          "X-CSRF-Token": decodeURIComponent(csrf),
        },
        body: JSON.stringify({
          provider_key: "codex",
          friendly_name: `Pagination Codex ${String(index).padStart(3, "0")}`,
          organization_id: null,
        }),
      });
      if (response.status !== 201) throw new Error(`account_create_${response.status}`);
      lastCreated = await response.json();
    }
    return lastCreated;
  });
  requireTruth(targetAccount?.friendly_name === "Pagination Codex 200", "account_creation_incomplete");

  stage = "visible_account_pagination";
  const accountListReads = [];
  page.on("response", (response) => {
    const url = new URL(response.url());
    if (url.pathname === "/api/v1/accounts" && response.request().method() === "GET") {
      accountListReads.push({ cursor: url.searchParams.get("cursor"), status: response.status() });
    }
  });
  await page.getByRole("button", { name: "Accounts", exact: true }).click();
  await page.getByRole("heading", { name: "Accounts", exact: true }).waitFor();
  requireTruth(
    await page.getByText(targetAccount.friendly_name, { exact: true }).count() === 0,
    "second_page_target_was_not_beyond_first_page",
  );
  await page.getByRole("button", { name: "Load more accounts", exact: true }).click();
  const targetName = page.getByText(targetAccount.friendly_name, { exact: true });
  await targetName.waitFor();
  requireTruth(
    accountListReads.some(read => read.status === 200 && typeof read.cursor === "string" && read.cursor.length > 0),
    "generated_cursor_account_read_missing",
  );
  requireTruth(
    await page.getByRole("button", { name: "Load more accounts", exact: true }).count() === 0,
    "account_pagination_did_not_finish",
  );

  stage = "visible_account_open";
  const detailPath = `/api/v1/accounts/${encodeURIComponent(targetAccount.account_id)}`;
  const accountReads = [];
  page.on("response", (response) => {
    const url = new URL(response.url());
    if (url.pathname === detailPath && response.request().method() === "GET") {
      accountReads.push(response.status());
    }
  });
  const targetCard = page.locator("article.record-card", { has: targetName });
  requireTruth(await targetCard.count() === 1, "second_page_target_card_missing");
  await targetCard.getByRole("button", { name: "Open account", exact: true }).click();
  await page.getByRole("heading", { name: targetAccount.friendly_name, exact: true }).waitFor();
  await page.getByRole("button", { name: "Connect Codex", exact: true }).waitFor();
  requireTruth(accountReads.includes(200), "generated_direct_account_get_missing");

  await browser.close();
  console.log("P02 ACCOUNT BEYOND PAGE: PASSED — visible cursor pagination and generated detail GET over real API and file SQLite");
} catch (error) {
  if (browser) await browser.close();
  console.error(`P02 ACCOUNT BEYOND PAGE: FAILED — ${stage}: ${error instanceof Error ? error.message : "unknown"}`);
  process.exitCode = 1;
}
