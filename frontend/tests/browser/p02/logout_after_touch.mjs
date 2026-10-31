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
  await page.goto(`${origin}/login`);
  await page.getByRole("heading", { name: "Sign in" }).waitFor();
  await page.getByLabel("Administrator password").fill(credential);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.getByRole("heading", { name: "AgentMonitor" }).waitFor();
  const first = await page.evaluate(async () => {
    const response = await fetch("/api/v1/session", { credentials: "same-origin" });
    return { status: response.status, version: (await response.json()).record_version };
  });
  if (first.status !== 200) throw new Error("initial_session_missing");
  stage = "real_touch_wait";
  const started = performance.now();
  await new Promise((resolve) => setTimeout(resolve, 61_500));
  if (performance.now() - started < 61_000) throw new Error("elapsed_time_insufficient");
  const touched = await page.evaluate(async () => {
    const response = await fetch("/api/v1/session", { credentials: "same-origin" });
    return { status: response.status, version: (await response.json()).record_version };
  });
  if (touched.status !== 200 || touched.version <= first.version) throw new Error("durable_touch_not_observed");
  stage = "logout_with_current_server_version";
  const deletion = page.waitForResponse((response) =>
    new URL(response.url()).pathname === "/api/v1/session" && response.request().method() === "DELETE");
  await page.getByRole("button", { name: "Sign out" }).click();
  const result = await deletion;
  stage = `logout_status_${result.status()}`;
  if (result.status() !== 204) throw new Error("active_logout_stale_precondition");
  await page.getByRole("heading", { name: "Sign in" }).waitFor();
  const afterward = await page.request.get("/api/v1/session");
  if (afterward.status() !== 401) throw new Error("server_session_not_revoked");
  await browser.close();
  console.log("P02 LOGOUT AFTER TOUCH: PASSED — actual elapsed >= 61 s");
} catch {
  if (browser) await browser.close();
  console.error(`P02 LOGOUT AFTER TOUCH: FAILED — ${stage}`);
  process.exitCode = 1;
}
