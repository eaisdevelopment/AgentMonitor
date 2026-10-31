"use strict";

import { readFileSync } from "node:fs";
import { join } from "node:path";
import { chromium } from "@playwright/test";

const [origin, accountId, screenshotDirectory] = process.argv.slice(2);
const { credential, expectedEmail } = JSON.parse(readFileSync(0, "utf8"));
let browser;
let stage = "login";

function requireTruth(condition, reason) {
  if (!condition) throw new Error(reason);
}

try {
  browser = await chromium.launch({ channel: "chrome", headless: true });
  const page = await browser.newPage({ baseURL: origin, viewport: { width: 1440, height: 1000 }, reducedMotion: "reduce" });
  const pageErrors = [];
  page.on("pageerror", (error) => pageErrors.push(error.name));
  await page.goto(`${origin}/login`);
  await page.getByLabel("Administrator password").fill(credential);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.getByRole("heading", { name: "AgentMonitor", exact: true }).waitFor();
  stage = "real_api";
  // Same-origin authenticated reads reconcile UI labels with the real API.
  const read = async (path) => page.evaluate(async (selectedPath) => {
    const response = await fetch(selectedPath);
    if (!response.ok) throw new Error("live_api_read_failed");
    return response.json();
  }, path);
  const account = await read(`/api/v1/accounts/${encodeURIComponent(accountId)}`);
  const organizations = await read("/api/v1/organizations?limit=200");
  stage = "real_process_locations";
  const liveProcesses = await read("/api/v1/process-locations");
  stage = "real_identity_receipt";
  let identity;
  let capacity;
  const deadline = Date.now() + 330_000;
  do {
    identity = await read(`/api/v1/accounts/${encodeURIComponent(accountId)}/observed-identity`);
    capacity = await read(`/api/v1/accounts/${encodeURIComponent(accountId)}/capacity`);
    if (identity.state === "verified" && capacity.items.length > 0 && capacity.items.every((item) => item.windows.every((window) => window.collection_run_id === identity.collection_run_id))) break;
    await page.waitForTimeout(1000);
  } while (Date.now() < deadline);
  requireTruth(identity.state === "verified" && identity.email === expectedEmail, "provider_identity_not_verified");
  requireTruth(capacity.items.length > 0 && capacity.items.every((item) => item.windows.every((window) => window.collection_run_id === identity.collection_run_id)), "identity_quota_lineage_mismatch");
  const organization = organizations.items.find((item) => item.organization_id === account.organization_id);
  stage = "workspace_table";
  await page.goto(`${origin}/accounts/${encodeURIComponent(accountId)}`);
  await page.getByRole("heading", { name: expectedEmail, exact: true }).waitFor();
  await page.screenshot({ path: join(screenshotDirectory, "account-before-or-after.png"), fullPage: false });
  const table = page.getByRole("table", { name: "Account activity" });
  await table.waitFor({ timeout: 10_000 });
  requireTruth(JSON.stringify(await table.locator("thead th").allTextContents()) === JSON.stringify(["Account", "State", "Left", "Path"]), "account_columns_missing");
  const summary = page.getByRole("region", { name: "Account activity", exact: true });
  requireTruth((await summary.innerText()).includes(expectedEmail), "account_identity_not_attributed");
  requireTruth((await summary.innerText()).includes(organization?.name ?? "Ungrouped"), "organization_not_attributed");
  for (const item of capacity.items) {
    const selected = item.windows.find((window) => window.window_id === item.health?.constraining_window_id);
    for (const window of selected === undefined ? item.windows : [selected]) {
      const ratio = window.remaining_ratio;
      const used = window.used;
      const percentage = ratio.availability === "available" && ratio.value?.unit === "ratio"
        ? Number(ratio.value.coefficient) * 10 ** (2 - ratio.value.scale)
        : used.availability === "available" && used.value?.unit === "percent"
          ? 100 - Number(used.value.coefficient) * 10 ** -used.value.scale : null;
      if (percentage !== null) requireTruth((await table.innerText()).includes(`${Number(percentage.toFixed(2))}%`), "real_remaining_percentage_missing");
      if (percentage !== null) {
        requireTruth(window.allowance?.input_observation_id === window.current_observation_id, "allowance_lineage_missing");
        requireTruth(window.allowance?.remaining_percentage.value_kind === "derived", "calculation_mislabeled_as_provider_value");
      }
    }
  }
  requireTruth(!/\bWorking\b/u.test(await table.innerText()), "working_state_invented_without_api_evidence");
  stage = "real_paths";
  requireTruth(liveProcesses.availability.state === "available" && liveProcesses.items.length > 0, "real_running_processes_required");
  const processesTable = page.getByRole("table", { name: "Live Claude processes" });
  await processesTable.waitFor();
  const processText = await processesTable.innerText();
  requireTruth(liveProcesses.items.some((item) => item.working_directory !== null && processText.includes(item.working_directory)), "real_working_directory_missing");
  requireTruth(processText.includes("Account unresolved") && !processText.includes(expectedEmail), "unproven_process_ownership_assigned");
  await page.getByRole("heading", { name: "Usage allowance", exact: true }).waitFor();
  const settings = page.locator("details.account-settings");
  requireTruth(await settings.getAttribute("open") === null, "settings_dominate_initial_view");
  stage = "responsive";
  for (const [width, height] of [[1440, 1000], [1920, 1080], [390, 844]]) {
    await page.setViewportSize({ width, height });
    await page.screenshot({ path: join(screenshotDirectory, `account-${width}.png`), fullPage: false });
    if (await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1)) {
      const overflow = await page.evaluate(() => [...document.querySelectorAll("body *")].filter((element) => element.getBoundingClientRect().right > innerWidth + 1).slice(0, 12).map((element) => ({ tag: element.tagName, className: element.className, right: Math.round(element.getBoundingClientRect().right) })));
      console.error(JSON.stringify({ viewport: width, overflow }));
    }
    requireTruth(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1), "horizontal_overflow");
    requireTruth(await table.isVisible(), "primary_table_hidden");
    requireTruth(await processesTable.isVisible(), "live_process_table_hidden");
  }
  requireTruth(pageErrors.length === 0, "browser_exception");
  await browser.close();
  console.log("ACCOUNT WORKSPACE: PASSED — real owner account, organization, selected quota, responsive browser");
} catch (error) {
  if (browser) await browser.close();
  const reason = (error instanceof Error ? error.message : "unknown").replaceAll(credential, "[redacted]");
  console.error(`ACCOUNT WORKSPACE: FAILED — ${stage}: ${reason}`);
  process.exitCode = 1;
}
