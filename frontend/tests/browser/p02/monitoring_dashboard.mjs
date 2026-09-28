"use strict";

import { readFileSync } from "node:fs";
import { chromium } from "@playwright/test";

const origin = process.argv[2];
const credential = readFileSync(0, "utf8");
let browser;
let stage = "browser_launch";
let accountDetailOutcome = "BLOCKED — no real registered account in the isolated database";

function requireTruth(condition, reason) {
  if (!condition) throw new Error(reason);
}

async function requireNoHorizontalOverflow(page) {
  const overflow = await page.evaluate(() => {
    if (document.documentElement.scrollWidth <= window.innerWidth + 1) return null;
    const offenders = [...document.querySelectorAll("body *")]
      .filter((element) => element.getBoundingClientRect().right > window.innerWidth + 1)
      .slice(-8)
      .map((element) => `${element.tagName.toLowerCase()}.${element.className}`);
    return `${document.documentElement.scrollWidth}/${window.innerWidth}:${offenders.join(",")}`;
  });
  requireTruth(overflow === null, `document_horizontal_overflow_${overflow}`);
}

try {
  browser = await chromium.launch({ channel: "chrome", headless: true });
  const context = await browser.newContext({
    baseURL: origin,
    viewport: { width: 1920, height: 1080 },
    reducedMotion: "reduce",
  });
  const page = await context.newPage();
  const externalRequests = [];
  const pageErrors = [];
  const observationGets = [];
  page.on("request", (request) => {
    if (new URL(request.url()).origin !== origin) externalRequests.push(request.url());
  });
  page.on("response", (response) => {
    const request = response.request();
    const url = new URL(response.url());
    if (url.origin === origin && request.method() === "GET" && url.pathname.startsWith("/api/v1/")) {
      observationGets.push({ route: `${url.pathname}${url.search}`, status: response.status() });
    }
  });
  page.on("pageerror", (error) => pageErrors.push(error.name));

  stage = "login";
  await page.goto(`${origin}/login`);
  await page.getByRole("heading", { name: "Sign in" }).waitFor();
  await page.getByLabel("Administrator password").fill(credential);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.getByRole("heading", { name: "AgentMonitor" }).waitFor();
  stage = "command_responsive";
  for (const [width, height] of [[1920, 1080], [1440, 900], [1280, 720], [1024, 768], [768, 1024], [390, 844]]) {
    await page.setViewportSize({ width, height });
    await requireNoHorizontalOverflow(page);
    requireTruth(await page.getByRole("heading", { name: "Accounts", exact: true }).isVisible(), `accounts_panel_hidden_${width}`);
    requireTruth(await page.getByRole("heading", { name: "Sessions", exact: true }).isVisible(), `sessions_panel_hidden_${width}`);
  }
  requireTruth(await page.getByText(/Claude|Codex|Ollama/).count() === 0, "invented_provider_presence");
  const requiredObservationGets = [
    "/api/v1/accounts?limit=200",
    "/api/v1/provider-installations?limit=200",
    "/api/v1/collection-runs?limit=50",
    "/api/v1/process-metrics?limit=200",
    "/api/v1/sessions?limit=200",
  ];
  for (const requiredRoute of requiredObservationGets) {
    const calls = observationGets.filter((entry) => entry.route === requiredRoute);
    requireTruth(calls.length > 0, `observation_get_missing_${requiredRoute}`);
    requireTruth(calls.every((entry) => entry.status === 200), `observation_get_not_200_${requiredRoute}`);
  }
  const accountLinks = page.getByRole("button", { name: "Open account", exact: true });
  if (await accountLinks.count() > 0) {
    stage = "account_detail_requests";
    const sessionResponse = page.waitForResponse((response) => {
      const url = new URL(response.url());
      return url.pathname === "/api/v1/sessions" && url.searchParams.has("account_id") && response.request().method() === "GET";
    });
    const capacityResponse = page.waitForResponse((response) => /^\/api\/v1\/accounts\/[^/]+\/capacity$/.test(new URL(response.url()).pathname));
    const quotaResponse = page.waitForResponse((response) => /^\/api\/v1\/accounts\/[^/]+\/quotas$/.test(new URL(response.url()).pathname));
    await accountLinks.first().click();
    await page.locator("details[data-account-sessions] > summary").click();
    await page.getByRole("heading", { name: "Running sessions", exact: true }).waitFor();
    const responses = await Promise.all([sessionResponse, capacityResponse, quotaResponse]);
    requireTruth(responses.every((response) => response.status() === 200), "account_detail_get_not_200");
    await page.getByText(/source|collected|freshness|version/i).first().waitFor();
    accountDetailOutcome = "PASSED — real registered account";
  }
  await page.setViewportSize({ width: 1920, height: 1080 });

  stage = "accounts_navigation";
  await page.getByRole("button", { name: "Accounts", exact: true }).click();
  await page.getByRole("heading", { name: "Accounts", exact: true }).waitFor();
  await page.getByText("No monitored accounts are registered.", { exact: true }).waitFor();

  stage = "providers_navigation";
  await page.getByRole("button", { name: "Providers", exact: true }).click();
  await page.getByRole("heading", { name: "Providers", exact: true }).waitFor();
  await page.getByText("No provider installations were discovered.", { exact: true }).waitFor();

  stage = "collectors_navigation";
  await page.getByRole("button", { name: "Collectors", exact: true }).click();
  await page.getByRole("heading", { name: "Collection runs", exact: true }).waitFor();
  await page.getByText("No collection runs have been recorded.", { exact: true }).waitFor();

  stage = "sessions_navigation";
  await page.getByRole("button", { name: "Sessions", exact: true }).click();
  await page.getByRole("heading", { name: "Sessions", exact: true }).waitFor();
  await page.getByText("No observed sessions are available.", { exact: true }).waitFor();

  stage = "direct_shell_routes";
  for (const [path, heading] of [["/accounts", "Accounts"], ["/providers", "Providers"], ["/collectors", "Collection runs"], ["/sessions", "Sessions"]]) {
    const response = await page.goto(`${origin}${path}`);
    requireTruth(response?.status() === 200, `shell_route_missing_${path}`);
    await page.getByRole("heading", { name: heading, exact: true }).waitFor();
  }

  stage = "truth_and_privacy";
  const visibleText = (await page.locator("body").innerText()).toLowerCase();
  for (const prohibited of ["sample", "demo", "placeholder"]) {
    requireTruth(!visibleText.includes(prohibited), `prohibited_${prohibited}_telemetry`);
  }
  requireTruth(externalRequests.length === 0, "external_request");
  requireTruth(pageErrors.length === 0, "page_error");
  requireTruth(
    await page.evaluate(() => localStorage.length === 0 && sessionStorage.length === 0),
    "monitoring_data_in_browser_storage",
  );
  await requireNoHorizontalOverflow(page);

  stage = "responsive";
  await page.setViewportSize({ width: 390, height: 844 });
  await requireNoHorizontalOverflow(page);
  requireTruth(await page.getByRole("button", { name: "Accounts", exact: true }).isVisible(), "mobile_accounts_hidden");
  requireTruth(await page.getByRole("button", { name: "Sign out" }).isVisible(), "mobile_logout_hidden");

  await browser.close();
  console.log(`P02 MONITORING DASHBOARD: PASSED — real database/API/browser; account detail ${accountDetailOutcome}`);
} catch (error) {
  if (browser) await browser.close();
  console.error(`P02 MONITORING DASHBOARD: FAILED — ${stage}: ${error instanceof Error ? error.message : "unknown"}`);
  process.exitCode = 1;
}
