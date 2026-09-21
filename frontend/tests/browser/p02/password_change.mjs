"use strict";

import { readFileSync } from "node:fs";
import { randomBytes } from "node:crypto";
import { chromium } from "@playwright/test";

const origin = process.argv[2];
const initialCredential = readFileSync(0, "utf8");
const nextCredential = randomBytes(32).toString("base64url");
let browser;
let stage = "browser_launch";
try {
  browser = await chromium.launch({ channel: "chrome", headless: true });
  const page = await browser.newPage({ baseURL: origin });
  await page.goto(`${origin}/login`);
  await page.getByRole("heading", { name: "Sign in" }).waitFor();
  await page.getByLabel("Administrator password").fill(initialCredential);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.getByRole("heading", { name: "AgentMonitor" }).waitFor();
  stage = "password_form";
  await page.getByRole("button", { name: "Change password" }).click();
  await page.getByLabel("Current password").fill(initialCredential);
  await page.getByLabel("New password", { exact: true }).fill(nextCredential);
  await page.getByLabel("Confirm new password").fill(nextCredential);
  await page.getByRole("button", { name: "Save new password" }).click();
  stage = "password_rotated";
  await page.getByText("Password changed. Other browser sessions were revoked.").waitFor();
  await page.getByRole("button", { name: "Sign out" }).click();
  await page.getByRole("heading", { name: "Sign in" }).waitFor();
  stage = "old_credential_denied";
  await page.getByLabel("Administrator password").fill(initialCredential);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.getByText(/Sign-in failed/).waitFor();
  stage = "new_credential_accepted";
  await page.getByLabel("Administrator password").fill(nextCredential);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.getByRole("heading", { name: "AgentMonitor" }).waitFor();
  await browser.close();
  console.log("P02 PASSWORD CHANGE BROWSER: PASSED");
} catch {
  if (browser) await browser.close();
  console.error(`P02 PASSWORD CHANGE BROWSER: FAILED — ${stage}`);
  process.exitCode = 1;
}
