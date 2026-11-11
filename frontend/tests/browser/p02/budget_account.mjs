"use strict";

import { readFileSync } from "node:fs";
import assert from "node:assert/strict";
import { chromium } from "@playwright/test";

const origin = process.argv[2];
const credential = readFileSync(0, "utf8");
let browser;
let stage = "browser_launch";
try {
  browser = await chromium.launch({ channel: "chrome", headless: true });
  const context = await browser.newContext({ baseURL: origin, viewport: { width: 1280, height: 800 } });
  const page = await context.newPage();
  page.setDefaultTimeout(10000);
  stage = "login";
  await page.goto(`${origin}/login`);
  await page.getByLabel("Administrator password").fill(credential);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await page.getByRole("heading", { name: "AgentMonitor", exact: true }).waitFor();
  stage = "create_metadata";
  await page.getByRole("button", { name: "Accounts", exact: true }).click();
  await page.getByRole("button", { name: "Add API billing account", exact: true }).click();
  await page.getByLabel("Provider", { exact: true }).selectOption("claude");
  await page.getByLabel("Account name").fill("Budget browser metadata");
  await page.getByRole("button", { name: "Create API billing account", exact: true }).click();
  await page.getByRole("heading", { name: "Budget browser metadata", exact: true }).waitFor();
  stage = "budget_panel";
  const panel = page.getByRole("region", { name: "API usage & spend", exact: true });
  await panel.waitFor();
  await panel.getByText("API billing is not set up.", { exact: true }).waitFor();
  stage = "configured_no_report";
  await page.getByRole("button", { name: "Add API billing connection", exact: true }).click();
  await panel.getByText("No report for this interval.", { exact: true }).waitFor();
  assert.equal(await panel.getByText("0.00 USD", { exact: true }).count(), 0);
  await panel.getByText("Remaining funds not reported.", { exact: true }).waitFor();
  assert.equal(await page.getByRole("heading", { name: "Account activity", exact: true }).count(), 0);
  stage = "range_and_read_only";
  const setup = page.getByRole("region", { name: "API billing setup", exact: true });
  const check = setup.getByRole("button", { name: "Check connection", exact: true });
  await check.waitFor();
  assert.equal(await check.isDisabled(), true);
  await setup.getByText("Store a credential locally before checking connection.", { exact: true }).waitFor();
  assert.equal(await setup.getByRole("button", { name: "Enable API monitoring", exact: true }).count(), 0);
  let mutations = 0;
  const observe = (request) => {
    if (!new Set(["GET", "HEAD", "OPTIONS"]).has(request.method())) mutations += 1;
  };
  page.on("request", observe);
  const [response] = await Promise.all([
    page.waitForResponse((response) => response.url().includes("/api-capacity?") && response.status() === 200),
    panel.getByLabel("Report range", { exact: true }).selectOption("30"),
  ]);
  const payload = await response.json();
  assert.equal((Date.parse(payload.period.end) - Date.parse(payload.period.start)) / 86400000, 30);
  assert.deepEqual(payload.resources[0].reported_spend, []);
  await panel.getByText("No report for this interval.", { exact: true }).waitFor();
  await Promise.all([
    page.waitForResponse((value) => value.url().includes("/api-capacity?") && value.status() === 200),
    panel.getByRole("button", { name: "Refresh readings", exact: true }).click(),
  ]);
  stage = "reload_narrow";
  await page.reload();
  await panel.getByText("No report for this interval.", { exact: true }).waitFor();
  await page.setViewportSize({ width: 768, height: 900 });
  assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
  await page.setViewportSize({ width: 390, height: 844 });
  assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
  assert.equal(mutations, 0);
  page.off("request", observe);
  console.log("M7 BUDGET ACCOUNT BROWSER: PASSED");
} catch {
  console.error(`M7 BUDGET ACCOUNT BROWSER: FAILED — ${stage}`);
  process.exitCode = 1;
} finally {
  if (browser) await browser.close();
}
