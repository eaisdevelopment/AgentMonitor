"use strict";

import { readFileSync } from "node:fs";
import { randomUUID } from "node:crypto";
import { chromium } from "@playwright/test";

const origin = process.argv[2];
const password = readFileSync(0, "utf8");
let stage = "browser_launch";
let browser;
const externalHosts = new Set();
const requireTruth = (condition, code) => {
  if (!condition) throw new Error(code);
};

try {
  browser = await chromium.launch({ channel: "chrome", headless: true });
  const context = await browser.newContext({ baseURL: origin });
  const page = await context.newPage();
  let externalRequests = 0;
  let pageErrors = 0;
  const apiRequests = [];
  const headerTasks = [];
  page.on("request", (request) => {
    const url = new URL(request.url());
    if (url.origin !== origin) {
      externalRequests += 1;
      externalHosts.add(url.hostname);
    }
    if (url.origin === origin && url.pathname.startsWith("/api/v1/")) {
      headerTasks.push((async () => {
        const headers = await request.allHeaders();
        apiRequests.push({
          method: request.method(),
          path: url.pathname,
          cookie: Boolean(headers.cookie),
          csrf: Boolean(headers["x-csrf-token"]),
          bearer: Boolean(headers.authorization),
        });
      })());
    }
  });
  page.on("pageerror", () => { pageErrors += 1; });

  stage = "anonymous_docs";
  const anonymous = await page.goto(`${origin}/docs`);
  requireTruth(anonymous?.status() === 401, "anonymous_docs_not_denied");
  for (const path of ["/redoc", "/openapi.json"]) {
    const denied = await page.goto(`${origin}${path}`);
    requireTruth(denied?.status() === 401, "anonymous_documentation_not_denied");
  }
  stage = "browser_login";
  await page.goto(origin);
  const loginStatus = await page.evaluate(async (secret) => {
    const response = await fetch("/api/v1/session", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password: secret }),
      credentials: "same-origin",
    });
    return response.status;
  }, password);
  requireTruth(loginStatus === 204, "browser_login_failed");

  stage = "swagger_render";
  const swagger = await page.goto(`${origin}/docs`);
  requireTruth(swagger?.status() === 200, "swagger_page_failed");
  await page.locator(".swagger-ui .info").waitFor({ timeout: 15000 });
  requireTruth(await page.locator(".opblock").count() >= 13, "swagger_operations_missing");
  requireTruth(externalRequests === 0, "swagger_external_request");

  stage = "redoc_render";
  const redoc = await page.goto(`${origin}/redoc`);
  requireTruth(redoc?.status() === 200, "redoc_page_failed");
  stage = "redoc_heading";
  await page.locator("#redoc h1").first().waitFor({ timeout: 15000 });
  // The final assertion covers all documentation requests, including ReDoc.

  stage = "cookie_try_it_out";
  await page.goto(`${origin}/docs`);
  await page.locator(".swagger-ui .info").waitFor({ timeout: 15000 });
  const revokeOthers = page.locator(".opblock").filter({
    has: page.locator('[data-path="/api/v1/iam/session-revocations"]'),
  });
  requireTruth(await revokeOthers.count() === 1, "unsafe_operation_not_found");
  await revokeOthers.locator(".opblock-summary").click();
  await revokeOthers.getByRole("button", { name: "Try it out" }).click();
  await revokeOthers.locator('input[placeholder="Idempotency-Key"]').fill(randomUUID());
  await revokeOthers.getByRole("button", { name: "Execute" }).click();
  await revokeOthers.locator(".response-col_status").filter({ hasText: "200" }).waitFor({ timeout: 15000 });
  await Promise.all(headerTasks);
  const cookieCall = apiRequests.findLast((item) =>
    item.method === "POST" && item.path === "/api/v1/iam/session-revocations"
  );
  requireTruth(cookieCall?.cookie && cookieCall.csrf && !cookieCall.bearer, "cookie_csrf_try_it_out_failed");

  stage = "bearer_issue";
  const bearer = await page.evaluate(async (idempotencyKey) => {
    const csrf = document.cookie.split(";").map((entry) => entry.trim())
      .find((entry) => entry.startsWith("agentmonitor_csrf="))
      ?.slice("agentmonitor_csrf=".length);
    const response = await fetch("/api/v1/api-tokens", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": csrf,
        "Idempotency-Key": idempotencyKey,
      },
      credentials: "same-origin",
      body: JSON.stringify({ name: "docs-browser-scope", scopes: ["write:tokens"] }),
    });
    if (response.status !== 201) return null;
    return (await response.json()).bearer_credential;
  }, randomUUID());
  requireTruth(typeof bearer === "string" && bearer.length > 0, "bearer_issue_failed");

  stage = "bearer_try_it_out";
  await page.goto(`${origin}/docs`);
  await page.locator(".swagger-ui .info").waitFor({ timeout: 15000 });
  stage = "bearer_authorize_button";
  await page.getByRole("button", { name: "Authorize", exact: true }).first().click();
  const authorization = page.locator(".auth-container").filter({ hasText: "BearerTokenV1" });
  stage = "bearer_authorize_input";
  await authorization.locator('input[type="text"]').fill(bearer);
  stage = "bearer_authorize_submit";
  await authorization.locator("button.authorize").click();
  stage = "bearer_authorize_close";
  await authorization.locator("button.btn-done").click();
  stage = "bearer_success_try_it_out";
  const tokens = page.locator(".opblock.opblock-get").filter({
    has: page.locator('[data-path="/api/v1/api-tokens"]'),
  });
  stage = "bearer_tokens_operation";
  requireTruth(await tokens.count() === 1, "tokens_operation_not_found");
  stage = "bearer_tokens_click";
  await tokens.locator(".opblock-summary").click();
  await tokens.getByRole("button", { name: "Try it out" }).click();
  stage = "bearer_tokens_execute";
  const tokenResponse = page.waitForResponse((response) =>
    new URL(response.url()).pathname === "/api/v1/api-tokens" &&
      response.request().method() === "GET");
  await tokens.getByRole("button", { name: "Execute" }).click();
  stage = "bearer_tokens_response";
  const listedTokens = await tokenResponse;
  stage = `bearer_tokens_status_${listedTokens.status()}`;
  requireTruth(listedTokens.status() === 200, "bearer_token_list_failed");
  stage = "bearer_tokens_headers";
  await Promise.all(headerTasks);
  const successfulBearer = apiRequests.findLast((item) =>
    item.method === "GET" && item.path === "/api/v1/api-tokens"
  );
  requireTruth(successfulBearer?.bearer && !successfulBearer.cookie && !successfulBearer.csrf, "bearer_success_cookie_omission_failed");
  stage = "bearer_scope_denial";
  const events = page.locator(".opblock").filter({
    has: page.locator('[data-path="/api/v1/iam/security-events"]'),
  });
  stage = "bearer_events_operation";
  requireTruth(await events.count() === 1, "events_operation_not_found");
  stage = "bearer_events_click";
  await events.locator(".opblock-summary").click();
  await events.getByRole("button", { name: "Try it out" }).click();
  stage = "bearer_events_execute";
  const deniedResponse = page.waitForResponse((response) =>
    new URL(response.url()).pathname === "/api/v1/iam/security-events" &&
      response.request().method() === "GET");
  await events.getByRole("button", { name: "Execute" }).click();
  stage = "bearer_events_response";
  const denial = await deniedResponse;
  stage = `bearer_events_status_${denial.status()}`;
  requireTruth(denial.status() === 403, "bearer_scope_denial_failed");
  stage = "bearer_events_headers";
  await Promise.all(headerTasks);
  const bearerCall = apiRequests.findLast((item) =>
    item.method === "GET" && item.path === "/api/v1/iam/security-events"
  );
  requireTruth(bearerCall?.bearer && !bearerCall.cookie && !bearerCall.csrf, "bearer_cookie_omission_failed");

  stage = "authorization_reload";
  const stored = await page.evaluate((value) =>
    Object.values(localStorage).some((item) => String(item).includes(value)) ||
    Object.values(sessionStorage).some((item) => String(item).includes(value)), bearer);
  requireTruth(!stored, "bearer_persisted_in_storage");
  await page.reload();
  await page.locator(".swagger-ui .info").waitFor({ timeout: 15000 });
  const reloadEvents = page.locator(".opblock").filter({
    has: page.locator('[data-path="/api/v1/iam/security-events"]'),
  });
  await reloadEvents.locator(".opblock-summary").click();
  await reloadEvents.getByRole("button", { name: "Try it out" }).click();
  const reloadResponse = page.waitForResponse((response) =>
    new URL(response.url()).pathname === "/api/v1/iam/security-events" &&
      response.request().method() === "GET");
  await reloadEvents.getByRole("button", { name: "Execute" }).click();
  const reloaded = await reloadResponse;
  stage = `reload_events_status_${reloaded.status()}`;
  requireTruth(reloaded.status() === 200, "reload_cookie_request_failed");
  await Promise.all(headerTasks);
  const reloadCall = apiRequests.findLast((item) =>
    item.method === "GET" && item.path === "/api/v1/iam/security-events"
  );
  requireTruth(reloadCall?.cookie && !reloadCall.bearer, "authorization_persisted_after_reload");
  requireTruth(externalRequests === 0, "external_documentation_request");
  requireTruth(pageErrors === 0, "documentation_page_error");
  await browser.close();
  console.log("DOCS BROWSER: PASSED");
} catch {
  if (browser) await browser.close();
  console.error(`DOCS BROWSER: FAILED — ${stage}${externalHosts.size ? ` (${Array.from(externalHosts).join(",")})` : ""}`);
  process.exitCode = 1;
}
