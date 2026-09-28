"use strict";

import { readFileSync } from "node:fs";
import { chromium } from "@playwright/test";

const origin = process.argv[2];
const credential = readFileSync(0, "utf8");
let browser;
let stage = "browser_launch";

try {
  browser = await chromium.launch({ channel: "chrome", headless: true });
  const page = await browser.newPage({ baseURL: origin, viewport: { width: 1280, height: 800 } });
  stage = "login";
  await page.goto(`${origin}/login`);
  await page.getByLabel("Administrator password").fill(credential);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.getByRole("heading", { name: "AgentMonitor" }).waitFor();
  stage = "create_organization";
  await page.getByRole("button", { name: "Organizations", exact: true }).click();
  await page.getByLabel("Organization name").fill("Browser organization");
  await page.getByRole("button", { name: "Create organization" }).click();
  await page.getByText("Browser organization", { exact: true }).waitFor();
  stage = "create_account";
  await page.getByRole("button", { name: "Accounts", exact: true }).click();
  await page.getByLabel("Provider key").fill("claude");
  await page.getByLabel("Account name").fill("Browser account");
  await page.getByLabel("Organization", { exact: true }).selectOption({ label: "Browser organization" });
  await page.getByRole("button", { name: "Add account" }).click();
  await page.getByText("Browser account", { exact: true }).waitFor();
  await page.getByText("pending · monitoring disabled").waitFor();
  stage = "account_edit";
  await page.getByRole("button", { name: "Open account" }).click();
  await page.getByText("Withheld from dashboard", { exact: true }).waitFor();
  await page.getByText("Account names and organization assignments are administrator managed.", { exact: true }).waitFor();
  await page.getByLabel("Rename account").fill("Renamed browser account");
  await page.getByRole("button", { name: "Save account name" }).click();
  await page.getByText("Account name saved.").waitFor();
  await page.getByRole("heading", { name: "Renamed browser account" }).waitFor();
  await page.getByRole("button", { name: "Archive account" }).click();
  await page.getByRole("button", { name: "Restore account" }).waitFor();
  await page.getByRole("button", { name: "Restore account" }).click();
  await page.getByRole("button", { name: "Archive account" }).waitFor();
  stage = "responsive";
  await page.setViewportSize({ width: 390, height: 844 });
  if (await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1)) {
    throw new Error("horizontal_overflow");
  }
  await browser.close();
  console.log("P02 ACCOUNTS ADMIN: PASSED — real API, SQLite, and built browser");
} catch (error) {
  if (browser) await browser.close();
  console.error(`P02 ACCOUNTS ADMIN: FAILED — ${stage}: ${error instanceof Error ? error.message : "unknown"}`);
  process.exitCode = 1;
}
