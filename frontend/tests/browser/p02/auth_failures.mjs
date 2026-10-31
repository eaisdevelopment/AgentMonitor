"use strict";

import { randomBytes } from "node:crypto";
import { chromium } from "@playwright/test";

const origin = process.argv[2];
let browser;
let stage = "browser_launch";
try {
  browser = await chromium.launch({ channel: "chrome", headless: true });
  const page = await browser.newPage({ baseURL: origin });
  await page.goto(`${origin}/login`);
  await page.getByRole("heading", { name: "Sign in" }).waitFor();
  for (let attempt = 1; attempt <= 5; attempt += 1) {
    stage = `invalid_attempt_${attempt}`;
    await page.getByLabel("Administrator password").fill(randomBytes(32).toString("base64url"));
    const response = page.waitForResponse((item) =>
      new URL(item.url()).pathname === "/api/v1/session" && item.request().method() === "POST");
    await page.getByRole("button", { name: "Sign in" }).click();
    const result = await response;
    if (attempt < 5) {
      if (result.status() !== 401) throw new Error("invalid_credential_not_denied");
      await page.getByText(/Sign-in failed/).waitFor();
      await page.getByText(/Code: invalid_dashboard_credentials\. Reference: [A-Za-z0-9._:-]+\./).waitFor();
    } else {
      if (result.status() !== 429) throw new Error("throttle_not_activated");
      const retry = Number(result.headers()["retry-after"]);
      if (!Number.isInteger(retry) || retry < 1 || retry > 900) throw new Error("retry_after_invalid");
      stage = "bounded_retry_guidance";
      await page.getByText(`Try again in ${retry} seconds.`, { exact: false }).waitFor();
    }
  }
  if (await page.getByRole("heading", { name: "AgentMonitor" }).count()) throw new Error("invalid_login_opened_dashboard");
  await browser.close();
  console.log("P02 AUTH FAILURES BROWSER: PASSED");
} catch {
  if (browser) await browser.close();
  console.error(`P02 AUTH FAILURES BROWSER: FAILED — ${stage}`);
  process.exitCode = 1;
}
