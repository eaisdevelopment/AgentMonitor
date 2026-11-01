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

async function assertMobileHeaderLayout(page) {
  const observation = await page.evaluate(() => {
    const header = document.querySelector(".dashboard-header");
    const brand = header?.firstElementChild;
    const actions = document.querySelector(".header-actions");
    const navigation = document.querySelector(".dashboard-nav");
    if (!(header instanceof HTMLElement)
      || !(brand instanceof HTMLElement)
      || !(actions instanceof HTMLElement)
      || !(navigation instanceof HTMLElement)) return null;
    const headerRect = header.getBoundingClientRect();
    const brandRect = brand.getBoundingClientRect();
    const actionsRect = actions.getBoundingClientRect();
    const buttonRects = Array.from(actions.querySelectorAll("button"), (button) =>
      button.getBoundingClientRect());
    return {
      actionCount: buttonRects.length,
      actionsContained: buttonRects.every((rect) =>
        rect.left >= headerRect.left
        && rect.right <= headerRect.right
        && rect.left >= 0
        && rect.right <= document.documentElement.clientWidth),
      headerDirection: getComputedStyle(header).flexDirection,
      actionsFollowBrand: actionsRect.top >= brandRect.bottom,
      navigationOverflow: getComputedStyle(navigation).overflowX,
      navigationScrollable: navigation.scrollWidth > navigation.clientWidth + 1,
    };
  });
  if (observation === null) throw new Error("mobile_header_structure_missing");
  if (observation.actionCount !== 2 || !observation.actionsContained) {
    throw new Error("mobile_header_controls_outside_viewport");
  }
  if (observation.headerDirection !== "column" || !observation.actionsFollowBrand) {
    throw new Error("mobile_header_not_two_rows");
  }
  if (observation.navigationOverflow !== "auto" || !observation.navigationScrollable) {
    throw new Error("mobile_navigation_scroll_missing");
  }
}

async function assertMobileHeaderKeyboardOrder(page) {
  await page.locator(".skip-link").focus();
  let reached = false;
  for (let attempt = 0; attempt < 12; attempt++) {
    await page.keyboard.press("Tab");
    if (await page.getByRole("button", { name: "Check session" }).evaluate(
      (button) => document.activeElement === button)) { reached = true; break; }
  }
  if (!reached) throw new Error("check_session_keyboard_unreachable");
  await page.keyboard.press("Tab");
  if (!await page.getByRole("button", { name: "Sign out" }).evaluate(
    (button) => document.activeElement === button)) {
    throw new Error("sign_out_keyboard_unreachable");
  }
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
    if (width === 390) {
      stage = "mobile_header_layout";
      await assertMobileHeaderLayout(page);
      stage = "mobile_header_keyboard";
      await assertMobileHeaderKeyboardOrder(page);
    }
  }
  stage = "browser_close";
  await browser.close();
  console.log("P02 RESPONSIVE BROWSER: PASSED — six viewports, reduced motion and focus");
} catch {
  if (browser) {
    try { await browser.close(); } catch { /* Emit only the closed failure grammar below. */ }
  }
  console.error(`P02 RESPONSIVE BROWSER: FAILED — ${stage}`);
  process.exitCode = 1;
}
