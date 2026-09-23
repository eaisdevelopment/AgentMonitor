"use strict";

import { readFileSync } from "node:fs";
import { chromium } from "@playwright/test";

const origin = process.argv[2];
const credential = readFileSync(0, "utf8");
let browser;
let stage = "browser_launch";
const requireTruth = (condition, reason) => {
  if (!condition) throw new Error(reason);
};

try {
  browser = await chromium.launch({ channel: "chrome", headless: true });
  const context = await browser.newContext({ baseURL: origin });
  const page = await context.newPage();
  const externalRequests = [];
  const pageErrors = [];
  const observationGets = [];
  page.on("request", (request) => {
    if (new URL(request.url()).origin !== origin) externalRequests.push(new URL(request.url()).hostname);
  });
  page.on("pageerror", (error) => pageErrors.push(error.name));
  page.on("response", (response) => {
    const request = response.request();
    const url = new URL(response.url());
    if (url.origin === origin && request.method() === "GET" && url.pathname.startsWith("/api/v1/")) {
      observationGets.push({ route: `${url.pathname}${url.search}`, status: response.status() });
    }
  });

  stage = "entry_document";
  const document = await page.goto(`${origin}/login`);
  requireTruth(document?.status() === 200, "dashboard_entry_missing");
  requireTruth(await page.locator("#agentmonitor-dashboard-root").count() === 1, "dashboard_root_missing");
  stage = "login_form";
  await page.getByRole("heading", { name: "Sign in" }).waitFor();
  await page.getByLabel("Administrator password").fill(credential);
  await page.getByRole("button", { name: "Sign in" }).click();
  stage = "authenticated_shell";
  await page.getByRole("heading", { name: "AgentMonitor" }).waitFor();
  stage = "monitoring_dashboard";
  for (const region of ["Accounts", "Providers", "Collection runs", "Sessions"]) {
    await page.getByRole("region", { name: region }).waitFor();
  }
  await page.locator('[data-monitoring-state="api"]').waitFor();
  for (const emptyState of [
    "No monitored accounts are registered.",
    "No provider installations were discovered.",
    "No collection runs have been recorded.",
    "No observed sessions are available.",
  ]) await page.getByText(emptyState, { exact: true }).waitFor();
  for (const requiredRoute of [
    "/api/v1/accounts?limit=200",
    "/api/v1/provider-installations?limit=200",
    "/api/v1/collection-runs?limit=50",
    "/api/v1/process-metrics?limit=200",
    "/api/v1/sessions?limit=200",
  ]) {
    const calls = observationGets.filter((entry) => entry.route === requiredRoute);
    requireTruth(calls.length > 0, `observation_get_missing_${requiredRoute}`);
    requireTruth(calls.every((entry) => entry.status === 200), `observation_get_not_200_${requiredRoute}`);
  }
  const sessionCookie = (await context.cookies(origin)).find((item) => item.name === "agentmonitor_session");
  requireTruth(sessionCookie?.httpOnly === true, "session_cookie_not_httponly");
  const storageEmpty = await page.evaluate(() => localStorage.length === 0 && sessionStorage.length === 0);
  requireTruth(storageEmpty, "auth_material_in_browser_storage");
  stage = "route_focus";
  await page.getByRole("button", { name: "API tokens" }).click();
  await page.getByRole("heading", { name: "API tokens" }).waitFor();
  requireTruth(await page.evaluate(() => document.activeElement?.id === "page-title"), "token_heading_not_focused");
  await page.getByRole("button", { name: "Overview" }).click();
  await page.getByRole("heading", { name: "AgentMonitor" }).waitFor();
  requireTruth(await page.evaluate(() => document.activeElement?.id === "page-title"), "overview_heading_not_focused");
  stage = "logout";
  await page.getByRole("button", { name: "Sign out" }).click();
  await page.getByRole("heading", { name: "Sign in" }).waitFor();
  stage = "server_logout_revocation";
  const afterLogout = await context.request.get("/api/v1/session");
  requireTruth(afterLogout.status() === 401, "logout_only_changed_ui");
  requireTruth(!(await context.cookies(origin)).some((item) => item.name === "agentmonitor_session"), "logout_cookie_retained");

  stage = "csrf_missing_fail_closed";
  await page.getByLabel("Administrator password").fill(credential);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.getByRole("heading", { name: "AgentMonitor" }).waitFor();
  let logoutRequests = 0;
  page.on("request", (request) => {
    if (request.method() === "DELETE" && new URL(request.url()).pathname === "/api/v1/session") {
      logoutRequests += 1;
    }
  });
  await page.evaluate(() => { document.cookie = "agentmonitor_csrf=; Max-Age=0; Path=/"; });
  await page.getByRole("button", { name: "Sign out" }).click();
  await page.getByRole("heading", { name: "AgentMonitor" }).waitFor();
  await page.getByText(/The session remains active/).waitFor();
  requireTruth(logoutRequests === 0, "unsafe_request_sent_without_csrf");
  await page.getByRole("button", { name: "Check session" }).click();
  await page.getByText("Dashboard session is active.").waitFor();
  stage = "csrf_reauthentication";
  await page.evaluate(() => { document.cookie = "agentmonitor_csrf=; Max-Age=0; Path=/"; });
  await page.getByRole("button", { name: "Sign out" }).click();
  await page.getByRole("button", { name: "Sign in again" }).click();
  await page.getByRole("heading", { name: "Sign in" }).waitFor();
  await page.getByLabel("Administrator password").fill(credential);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await page.getByRole("heading", { name: "AgentMonitor" }).waitFor();
  await page.getByRole("button", { name: "Sign out" }).click();
  await page.getByRole("heading", { name: "Sign in" }).waitFor();
  requireTruth(externalRequests.length === 0, "external_request");
  requireTruth(pageErrors.length === 0, "page_error");
  await browser.close();
  console.log("P02 AUTH BROWSER: PASSED");
} catch {
  if (browser) await browser.close();
  console.error(`P02 AUTH BROWSER: FAILED — ${stage}`);
  process.exitCode = 1;
}
