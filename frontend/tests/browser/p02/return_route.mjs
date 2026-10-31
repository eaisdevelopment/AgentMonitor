"use strict";

import { readFileSync } from "node:fs";
import { chromium } from "@playwright/test";

const origin = process.argv[2];
const credential = readFileSync(0, "utf8");
let browser;
let stage = "browser_launch";

async function signIn(page) {
  await page.getByRole("heading", { name: "Sign in" }).waitFor();
  await page.getByLabel("Administrator password").fill(credential);
  await page.getByRole("button", { name: "Sign in" }).click();
}

try {
  browser = await chromium.launch({ channel: "chrome", headless: true });
  const allowed = await browser.newContext({ baseURL: origin });
  const pageA = await allowed.newPage();
  stage = "allowed_return_route";
  await pageA.goto(`${origin}/login?next=%2Fsettings%2Fapi-tokens`);
  await signIn(pageA);
  await pageA.getByRole("heading", { name: "API tokens" }).waitFor();
  if (new URL(pageA.url()).pathname !== "/settings/api-tokens") throw new Error("allowed_route_not_resumed");
  await pageA.goBack();
  if (new URL(pageA.url()).pathname === "/login") throw new Error("login_history_retained");

  stage = "hostile_return_route";
  const hostile = await browser.newContext({ baseURL: origin });
  const pageB = await hostile.newPage();
  let externalRequests = 0;
  pageB.on("request", (item) => {
    if (new URL(item.url()).origin !== origin) externalRequests += 1;
  });
  await pageB.goto(`${origin}/login?next=${encodeURIComponent("https://outside.invalid/secret")}`);
  await signIn(pageB);
  await pageB.getByRole("heading", { name: "AgentMonitor" }).waitFor();
  const address = new URL(pageB.url());
  if (address.pathname !== "/" || address.search || address.hash || externalRequests) {
    throw new Error("hostile_return_route_accepted");
  }
  await browser.close();
  console.log("P02 RETURN ROUTE BROWSER: PASSED");
} catch {
  if (browser) await browser.close();
  console.error(`P02 RETURN ROUTE BROWSER: FAILED — ${stage}`);
  process.exitCode = 1;
}
