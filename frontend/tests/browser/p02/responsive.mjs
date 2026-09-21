"use strict";

import { readFileSync } from "node:fs";
import { chromium } from "@playwright/test";

const origin = process.argv[2];
const credential = readFileSync(0, "utf8");
const viewports = [
  [1920, 1080], [1440, 900], [1280, 720],
  [1024, 768], [768, 1024], [390, 844],
];
let browser;
let stage = "browser_launch";

async function assertNoDocumentOverflow(page) {
  const overflow = await page.evaluate(() =>
    document.documentElement.scrollWidth > window.innerWidth + 1);
  if (overflow) throw new Error("document_horizontal_overflow");
}

try {
  browser = await chromium.launch({ channel: "chrome", headless: true });
  const context = await browser.newContext({
    baseURL: origin, viewport: { width: 1920, height: 1080 }, reducedMotion: "reduce",
  });
  const page = await context.newPage();
  await page.goto(`${origin}/login`);
  await page.getByRole("heading", { name: "Sign in" }).waitFor();
  for (const [width, height] of viewports) {
    stage = `login_${width}`;
    await page.setViewportSize({ width, height });
    await assertNoDocumentOverflow(page);
    if (!await page.getByLabel("Administrator password").isVisible()) throw new Error("credential_input_hidden");
  }
  stage = "keyboard_sign_in";
  await page.getByLabel("Administrator password").focus();
  if (!await page.evaluate(() => document.activeElement?.id === "administrator-password")) {
    throw new Error("credential_focus_failed");
  }
  await page.getByLabel("Administrator password").fill(credential);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.getByRole("heading", { name: "AgentMonitor" }).waitFor();
  await page.getByRole("button", { name: "API tokens" }).click();
  await page.getByRole("heading", { name: "API tokens" }).waitFor();
  for (const [width, height] of viewports) {
    stage = `token_settings_${width}`;
    await page.setViewportSize({ width, height });
    await assertNoDocumentOverflow(page);
    if (!await page.getByLabel("Token name").isVisible()) throw new Error("token_form_hidden");
    if (!await page.getByRole("button", { name: "Sign out" }).isVisible()) throw new Error("logout_hidden");
  }
  await browser.close();
  console.log("P02 RESPONSIVE BROWSER: PASSED — six viewports, reduced motion and focus");
} catch {
  if (browser) await browser.close();
  console.error(`P02 RESPONSIVE BROWSER: FAILED — ${stage}`);
  process.exitCode = 1;
}
