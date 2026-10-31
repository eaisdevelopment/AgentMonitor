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

  stage = "alert_navigation";
  await page.getByRole("button", { name: "Alerts", exact: true }).click();
  await page.getByRole("heading", { name: "Alerts", exact: true }).waitFor();
  await page.getByText("No active alerts.").waitFor();
  if (await page.getByText("0 critical", { exact: true }).count() !== 1) {
    throw new Error("real_empty_count_missing");
  }
  if (externalRequests.length) throw new Error("external_request");

  stage = "responsive";
  await page.setViewportSize({ width: 390, height: 844 });
  if (await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1)) {
    throw new Error("horizontal_overflow");
  }
  await browser.close();
  console.log("P02 ALERT CONSOLE: PASSED — real empty SQLite, HTTP, and built browser");
} catch (error) {
  if (browser) await browser.close();
  console.error(`P02 ALERT CONSOLE: FAILED — ${stage}: ${error instanceof Error ? error.message : "unknown"}`);
  process.exitCode = 1;
}
