"use strict";

import { readFileSync } from "node:fs";
import { randomUUID } from "node:crypto";
import { chromium } from "@playwright/test";

const origin = process.argv[2];
const credential = readFileSync(0, "utf8");
let browser;
let stage = "browser_launch";

async function signIn(page) {
  await page.goto(`${origin}/login`);
  await page.getByRole("heading", { name: "Sign in" }).waitFor();
  await page.getByLabel("Administrator password").fill(credential);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.getByRole("heading", { name: "AgentMonitor" }).waitFor();
}

async function recoverRevokedSession(page) {
  const signInHeading = page.getByRole("heading", { name: "Sign in" });
  await page.evaluate(() => {
    const isVisible = (element) => {
      const style = getComputedStyle(element);
      const bounds = element.getBoundingClientRect();
      return style.visibility !== "hidden"
        && style.display !== "none"
        && bounds.width > 0
        && bounds.height > 0;
    };
    const heading = Array.from(document.querySelectorAll("h1, h2, h3"))
      .find((element) => element.textContent?.trim() === "Sign in" && isVisible(element));
    if (heading) return;
    const action = Array.from(document.querySelectorAll("button"))
      .find((element) => element.textContent?.trim() === "Check session" && isVisible(element));
    if (action instanceof HTMLButtonElement && !action.disabled) action.click();
  });
  await signInHeading.waitFor();
}

try {
  browser = await chromium.launch({ channel: "chrome", headless: true });
  const primary = await browser.newContext({ baseURL: origin });
  const secondary = await browser.newContext({ baseURL: origin });
  const pageA = await primary.newPage();
  const pageB = await secondary.newPage();
  stage = "two_real_sessions";
  await signIn(pageA);
  await signIn(pageB);
  stage = "revoke_other_session";
  const status = await pageA.evaluate(async (key) => {
    const csrf = document.cookie.split(";").map((entry) => entry.trim())
      .find((entry) => entry.startsWith("agentmonitor_csrf="))
      ?.slice("agentmonitor_csrf=".length);
    const response = await fetch("/api/v1/iam/session-revocations", {
      method: "POST", credentials: "same-origin",
      headers: { "X-CSRF-Token": csrf ?? "", "Idempotency-Key": key },
    });
    return response.status;
  }, randomUUID());
  if (status !== 200) throw new Error("server_revocation_failed");
  stage = "revoked_recovery";
  await recoverRevokedSession(pageB);
  stage = "revoked_nav_absent";
  if (await pageB.getByRole("button", { name: "API tokens" }).count()) throw new Error("protected_navigation_retained");
  stage = "revoked_reload";
  await pageB.reload();
  stage = "revoked_reload_sign_in";
  await pageB.getByRole("heading", { name: "Sign in" }).waitFor();
  stage = "revoked_reload_nav_absent";
  if (await pageB.getByRole("button", { name: "API tokens" }).count()) throw new Error("protected_navigation_retained_after_reload");
  stage = "primary_check_click";
  await pageA.getByRole("button", { name: "Check session" }).click();
  stage = "primary_active_text";
  await pageA.getByText("Dashboard session is active.").waitFor();
  stage = "browser_close";
  await browser.close();
  console.log("P02 REVOCATION BROWSER: PASSED");
} catch {
  if (browser) {
    try { await browser.close(); } catch { /* Emit only the closed failure grammar below. */ }
  }
  console.error(`P02 REVOCATION BROWSER: FAILED — ${stage}`);
  process.exitCode = 1;
}
