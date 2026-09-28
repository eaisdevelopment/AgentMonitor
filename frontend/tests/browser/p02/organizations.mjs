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

  stage = "organization_navigation";
  await page.getByRole("button", { name: "Organizations", exact: true }).click();
  await page.getByRole("heading", { name: "Organizations", exact: true }).waitFor();
  await page.getByText("No organizations have been created.").waitFor();

  stage = "organization_creation";
  await page.getByLabel("Organization name").fill("Browser-created organization");
  await page.getByRole("button", { name: "Create organization" }).click();
  await page.getByText("Browser-created organization", { exact: true }).waitFor();
  stage = "organization_lifecycle";
  await page.getByLabel("Rename organization").fill("Renamed browser organization");
  await page.getByRole("button", { name: "Save organization name" }).click();
  await page.getByText("Renamed browser organization", { exact: true }).waitFor();
  await page.getByRole("button", { name: "Archive organization" }).click();
  await page.getByRole("button", { name: "Restore organization" }).waitFor();
  await page.getByRole("button", { name: "Restore organization" }).click();
  await page.getByRole("button", { name: "Archive organization" }).waitFor();
  stage = "organization_order";
  await page.getByLabel("Organization name").fill("Second browser organization");
  await page.getByRole("button", { name: "Create organization" }).click();
  await page.getByText("Second browser organization", { exact: true }).waitFor();
  await page.getByRole("button", { name: "Move Second browser organization up" }).click();
  await page.getByText("Organization order saved.").waitFor();
  if (await page.getByText("No organizations have been created.").count()) {
    throw new Error("empty_state_remained_after_create");
  }
  if (externalRequests.length) throw new Error("external_request");

  stage = "responsive";
  await page.setViewportSize({ width: 390, height: 844 });
  if (await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1)) {
    throw new Error("horizontal_overflow");
  }
  await browser.close();
  console.log("P02 ORGANIZATIONS: PASSED — real API, SQLite, and built browser");
} catch (error) {
  if (browser) await browser.close();
  console.error(`P02 ORGANIZATIONS: FAILED — ${stage}: ${error instanceof Error ? error.message : "unknown"}`);
  process.exitCode = 1;
}
