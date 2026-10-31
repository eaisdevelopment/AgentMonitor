"use strict";

import { readFileSync } from "node:fs";
import { chromium } from "@playwright/test";

const origin = process.argv[2];
const credential = readFileSync(0, "utf8");
let browser;
let stage = "browser_launch";

try {
  browser = await chromium.launch({ channel: "chrome", headless: true });
  const page = await browser.newPage({ baseURL: origin });
  const responseStatuses = [];
  let unsafeRequests = 0;
  page.on("response", (response) => {
    if (new URL(response.url()).pathname === "/api/v1/session" &&
        response.request().method() === "GET") responseStatuses.push(response.status());
  });
  page.on("request", (request) => {
    if (new URL(request.url()).pathname === "/api/v1/session" &&
        request.method() !== "GET") unsafeRequests += 1;
  });

  stage = "login";
  await page.goto(`${origin}/login`);
  await page.getByRole("heading", { name: "Sign in" }).waitFor();
  await page.getByLabel("Administrator password").fill(credential);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.getByRole("heading", { name: "AgentMonitor" }).waitFor();
  const unsafeAfterLogin = unsafeRequests;
  const startedAt = performance.now();
  stage = "real_idle_wait";
  await new Promise((resolve) => setTimeout(resolve, 86_405_000));
  if (performance.now() - startedAt < 86_400_000) throw new Error("elapsed_time_insufficient");
  stage = "expiry_recovery";
  await page.getByRole("button", { name: "Check session" }).click();
  await page.getByRole("heading", { name: "Sign in" }).waitFor({ timeout: 15_000 });
  if (responseStatuses.at(-1) !== 401) throw new Error("real_session_not_expired");
  if (unsafeRequests !== unsafeAfterLogin) throw new Error("unsafe_request_after_expiry");
  await browser.close();
  console.log("P02 SESSION EXPIRY BROWSER: PASSED — actual elapsed >= 86400 s");
} catch {
  if (browser) await browser.close();
  console.error(`P02 IDLE EXPIRY BROWSER: FAILED — ${stage}`);
  process.exitCode = 1;
}
