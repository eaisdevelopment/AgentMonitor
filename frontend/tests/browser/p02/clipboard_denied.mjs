"use strict";

import { readFileSync } from "node:fs";
import { chromium } from "@playwright/test";

const origin = process.argv[2];
const credential = readFileSync(0, "utf8");
let browser;
let stage = "browser_launch";
try {
  browser = await chromium.launch({ channel: "chrome", headless: true });
  const context = await browser.newContext({ baseURL: origin });
  const page = await context.newPage();
  stage = "real_browser_permission";
  await context.grantPermissions(["clipboard-read"], { origin });
  await page.goto(`${origin}/login`);
  const permissionState = await page.evaluate(async () =>
    (await navigator.permissions.query({ name: "clipboard-write" })).state);
  stage = `permission_${permissionState}`;
  if (permissionState !== "denied") throw new Error("browser_denial_not_applied");
  stage = "token_issue";
  await page.getByRole("heading", { name: "Sign in" }).waitFor();
  await page.getByLabel("Administrator password").fill(credential);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.getByRole("heading", { name: "AgentMonitor" }).waitFor();
  await page.getByRole("button", { name: "API tokens" }).click();
  await page.getByText("No API tokens have been issued.").waitFor();
  await page.getByLabel("Token name").fill("clipboard-denial-owned");
  await page.getByRole("checkbox", { name: "Manage API tokens" }).check();
  await page.getByRole("button", { name: "Create token" }).click();
  const dialog = page.getByRole("dialog", { name: "One-time API token" });
  await dialog.waitFor();
  stage = "denied_copy_fallback";
  await dialog.getByRole("button", { name: "Copy token" }).click();
  await dialog.getByText("Clipboard access was denied. Select and copy the credential manually.").waitFor();
  stage = "manual_selection";
  const field = dialog.getByLabel("New API token credential");
  await field.focus();
  const canSelect = await page.evaluate(() => {
    const element = document.activeElement;
    return element instanceof HTMLInputElement && element.readOnly &&
      element.value.length > 20 && element.selectionStart === 0 &&
      element.selectionEnd === element.value.length;
  });
  if (!canSelect) throw new Error("manual_select_unavailable");
  await dialog.getByRole("button", { name: "Done" }).click();
  await browser.close();
  console.log("P02 CLIPBOARD DENIAL BROWSER: PASSED");
} catch {
  if (browser) await browser.close();
  console.error(`P02 CLIPBOARD DENIAL BROWSER: FAILED — ${stage}`);
  process.exitCode = 1;
}
