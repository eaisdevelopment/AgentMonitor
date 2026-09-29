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
  const externalRequests = [];
  page.on("request", (request) => {
    if (new URL(request.url()).origin !== origin) externalRequests.push(request.url());
  });

  stage = "login";
  await page.goto(`${origin}/login`);
  await page.getByLabel("Administrator password").fill(credential);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.getByRole("heading", { name: "AgentMonitor" }).waitFor();

  stage = "rule_navigation";
  await page.getByRole("button", { name: "Alert rules", exact: true }).click();
  await page.getByRole("heading", { name: "Alert rules", exact: true }).waitFor();
  await page.getByText("No custom alert rules yet.").waitFor();

  stage = "rule_create";
  await page.getByLabel("Warning when left is at or below").fill("20");
  await page.getByLabel("Critical when left is at or below").fill("10");
  await page.getByRole("button", { name: "Create rule" }).click();
  const row = page.getByRole("row", { name: /Capacity remaining.*Global/ });
  await row.waitFor();
  await row.getByText("20% warning · 10% critical").waitFor();

  stage = "rule_disable";
  await row.getByRole("button", { name: "Disable rule" }).click();
  await row.getByText("Disabled", { exact: true }).waitFor();

  stage = "rule_archive";
  page.once("dialog", (dialog) => dialog.accept());
  await row.getByRole("button", { name: "Archive rule" }).click();
  await page.getByText("No custom alert rules yet.").waitFor();
  if (externalRequests.length) throw new Error("external_request");

  stage = "responsive";
  await page.setViewportSize({ width: 390, height: 844 });
  if (await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1)) {
    throw new Error("horizontal_overflow");
  }
  await browser.close();
  console.log("P02 ALERT RULES: PASSED — real IAM, rules SQLite, HTTP, and built browser");
} catch (error) {
  if (browser) await browser.close();
  console.error(`P02 ALERT RULES: FAILED — ${stage}: ${error instanceof Error ? error.message : "unknown"}`);
  process.exitCode = 1;
}
