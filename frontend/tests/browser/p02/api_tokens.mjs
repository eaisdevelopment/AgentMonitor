"use strict";

import { readFileSync } from "node:fs";
import { randomUUID } from "node:crypto";
import { request, chromium } from "@playwright/test";

const origin = process.argv[2];
const credential = readFileSync(0, "utf8");
let browser;
let stage = "browser_launch";
const requireTruth = (condition, reason) => {
  if (!condition) throw new Error(reason);
};

try {
  browser = await chromium.launch({ channel: "chrome", headless: true });
  const context = await browser.newContext({ baseURL: origin, permissions: ["clipboard-read", "clipboard-write"] });
  const page = await context.newPage();
  const externalHosts = new Set();
  const pageErrors = [];
  page.on("request", (item) => {
    const url = new URL(item.url());
    if (url.origin !== origin) externalHosts.add(url.hostname);
  });
  page.on("pageerror", (item) => pageErrors.push(item.name));
  stage = "login";
  await page.goto(`${origin}/login`);
  await page.getByRole("heading", { name: "Sign in" }).waitFor();
  await page.getByLabel("Administrator password").fill(credential);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.getByRole("heading", { name: "AgentMonitor" }).waitFor();
  await page.getByRole("button", { name: "API tokens" }).click();

  stage = "empty_token_list";
  await page.getByRole("heading", { name: "API tokens" }).waitFor();
  await page.getByText("Read IAM security events in M2.").waitFor();
  await page.getByText("List, issue, rotate, and revoke API tokens, subject to this token’s own scopes and expiry.").waitFor();
  await page.getByText("No API tokens have been issued.").waitFor();
  stage = "token_create";
  await page.getByLabel("Token name").fill("p02-browser-owned");
  await page.getByRole("checkbox", { name: "Manage API tokens" }).check();
  await page.getByRole("button", { name: "Create token" }).click();
  const oneTime = page.getByRole("dialog", { name: "One-time API token" });
  await oneTime.waitFor();
  const firstCredential = await oneTime.getByLabel("New API token credential").inputValue();
  requireTruth(firstCredential.length > 20, "issued_credential_missing");
  const beforeCopy = await page.evaluate(() => navigator.clipboard.readText());
  requireTruth(beforeCopy !== firstCredential, "automatic_clipboard_copy");
  await oneTime.getByRole("button", { name: "Copy token" }).click();
  const copied = await page.evaluate(() => navigator.clipboard.readText());
  requireTruth(copied === firstCredential, "explicit_copy_failed");
  await oneTime.getByRole("button", { name: "Done" }).click();
  await page.getByText("p02-browser-owned").waitFor();
  requireTruth(await page.getByRole("dialog", { name: "One-time API token" }).count() === 0, "credential_reopened");
  const stored = await page.evaluate((secret) =>
    Object.values(localStorage).some((value) => String(value).includes(secret)) ||
    Object.values(sessionStorage).some((value) => String(value).includes(secret)), firstCredential);
  requireTruth(!stored, "credential_in_browser_storage");

  stage = "issued_bearer_real_http";
  const bearerClient = await request.newContext({ baseURL: origin });
  const firstAuth = await bearerClient.get("/api/v1/api-tokens", {
    headers: { Authorization: `Bearer ${firstCredential}` },
  });
  requireTruth(firstAuth.status() === 200, "new_token_not_usable");
  stage = "scope_attenuation";
  const deniedScope = await bearerClient.post("/api/v1/api-tokens", {
    headers: { Authorization: `Bearer ${firstCredential}`, "Idempotency-Key": randomUUID(), Origin: origin },
    data: { name: "denied-scope", scopes: ["read:diagnostics"] },
  });
  requireTruth(deniedScope.status() === 403, "scope_escalation_accepted");
  requireTruth((await deniedScope.json()).code === "scope_escalation_denied", "scope_denial_not_authorization");
  await page.getByRole("button", { name: "Refresh summaries" }).click();
  await page.getByRole("row", { name: /p02-browser-owned/ }).getByRole("button", { name: "Rotate" }).waitFor();

  stage = "token_rotate";
  let rotationReview = false;
  page.once("dialog", (dialog) => {
    rotationReview = dialog.message().includes("Current scopes: write:tokens") &&
      dialog.message().includes("Current expiry:");
    return dialog.accept();
  });
  stage = "rotate_click";
  await page.getByRole("row", { name: /p02-browser-owned/ }).getByRole("button", { name: "Rotate" }).click();
  stage = "rotate_one_time";
  try {
    await oneTime.waitFor({ timeout: 10000 });
  } catch {
    if (await page.getByText(/This item changed. Refresh before trying again./).count()) stage = "rotate_stale_etag";
    else if (await page.getByText(/The request could not be completed/).count()) stage = "rotate_safe_problem";
    else if (await page.getByText(/The local service is unavailable/).count()) stage = "rotate_transport";
    throw new Error("rotation_did_not_issue");
  }
  requireTruth(rotationReview, "rotation_review_incomplete");
  stage = "rotate_credential";
  const secondCredential = await oneTime.getByLabel("New API token credential").inputValue();
  requireTruth(secondCredential !== firstCredential && secondCredential.length > 20, "rotation_credential_invalid");
  stage = "rotate_close";
  await oneTime.getByRole("button", { name: "Done" }).click();
  stage = "rotate_predecessor_http";
  const predecessor = await bearerClient.get("/api/v1/api-tokens", {
    headers: { Authorization: `Bearer ${firstCredential}` },
  });
  requireTruth(predecessor.status() === 401, "rotated_predecessor_still_accepted");
  stage = "rotate_replacement_http";
  const replacement = await bearerClient.get("/api/v1/api-tokens", {
    headers: { Authorization: `Bearer ${secondCredential}` },
  });
  requireTruth(replacement.status() === 200, "replacement_not_accepted");

  stage = "reload_one_time_loss";
  await page.reload();
  await page.getByRole("heading", { name: "API tokens" }).waitFor();
  requireTruth(await oneTime.count() === 0, "credential_recovered_after_reload");
  const html = await page.locator("body").innerText();
  requireTruth(!html.includes(firstCredential) && !html.includes(secondCredential), "credential_in_visible_page");

  stage = "token_revoke";
  page.once("dialog", (dialog) => dialog.accept());
  await page.getByRole("row", { name: /p02-browser-owned/ }).filter({ has: page.getByText("Active") })
    .getByRole("button", { name: "Revoke" }).click();
  await page.getByText("Revoked", { exact: true }).first().waitFor();
  const revoked = await bearerClient.get("/api/v1/api-tokens", {
    headers: { Authorization: `Bearer ${secondCredential}` },
  });
  requireTruth(revoked.status() === 401, "revoked_token_still_accepted");

  stage = "one_time_replay_real_http";
  const csrf = (await context.cookies(origin)).find((item) => item.name === "agentmonitor_csrf")?.value;
  requireTruth(typeof csrf === "string", "csrf_cookie_missing");
  const idempotencyKey = randomUUID();
  const createRequest = {
    headers: { "X-CSRF-Token": csrf, "Idempotency-Key": idempotencyKey, Origin: origin },
    data: { name: "replay-owned", scopes: ["write:tokens"] },
  };
  const directIssue = await page.request.post("/api/v1/api-tokens", createRequest);
  stage = `direct_issue_status_${directIssue.status()}`;
  if (directIssue.status() !== 201) {
    const denied = await directIssue.json();
    stage = `direct_issue_code_${/^[a-z_]+$/.test(denied.code) ? denied.code : "unknown"}`;
  }
  requireTruth(directIssue.status() === 201, "direct_issue_failed");
  const directBody = await directIssue.json();
  const replay = await page.request.post("/api/v1/api-tokens", createRequest);
  stage = `replay_status_${replay.status()}`;
  requireTruth(replay.status() === 409, "same_key_replay_not_denied");
  const replayBody = await replay.json();
  requireTruth(replayBody.code === "one_time_secret_not_replayable", "replay_problem_wrong");
  requireTruth(!Object.hasOwn(replayBody, "bearer_credential"), "replay_revealed_credential");
  requireTruth(replayBody.committed_resource?.api_token_id === directBody.token.api_token_id, "replay_summary_wrong");

  stage = "stale_etag_real_http";
  await page.getByRole("button", { name: "Refresh summaries" }).click();
  const staleRow = page.getByRole("row", { name: /replay-owned/ });
  stage = "stale_row_loaded";
  await staleRow.getByRole("button", { name: "Rotate" }).waitFor();
  stage = "external_active_version_advance";
  const used = await bearerClient.get("/api/v1/api-tokens", {
    headers: { Authorization: `Bearer ${directBody.bearer_credential}` },
  });
  requireTruth(used.status() === 200, "bearer_touch_failed");
  page.once("dialog", (dialog) => dialog.accept());
  const staleResponse = page.waitForResponse((item) =>
    new URL(item.url()).pathname.endsWith(`/api-tokens/${directBody.token.api_token_id}/rotations`) &&
    item.request().method() === "POST");
  await staleRow.getByRole("button", { name: "Rotate" }).click();
  const stale = await staleResponse;
  stage = `stale_ui_status_${stale.status()}`;
  requireTruth(stale.status() === 412, "stale_etag_not_rejected");
  await page.getByText(/This item changed. Refresh before trying again/).waitFor();
  await page.getByRole("button", { name: "Refresh summaries" }).click();
  await staleRow.getByText("Active", { exact: true }).waitFor();

  stage = "token_csrf_missing_fail_closed";
  let unsafeTokenRequests = 0;
  page.on("request", (item) => {
    if (item.method() === "POST" && new URL(item.url()).pathname === "/api/v1/api-tokens") unsafeTokenRequests += 1;
  });
  await page.evaluate(() => { document.cookie = "agentmonitor_csrf=; Max-Age=0; Path=/"; });
  stage = "csrf_fill";
  await page.getByLabel("Token name").fill("csrf-not-sent");
  await page.getByRole("checkbox", { name: "Manage API tokens" }).check();
  stage = "csrf_create_click";
  await page.getByRole("button", { name: "Create token" }).click();
  stage = "csrf_renew_control";
  await page.getByRole("button", { name: "Sign in again" }).waitFor();
  requireTruth(unsafeTokenRequests === 0, "token_mutation_sent_without_csrf");
  stage = "csrf_session_check";
  await page.getByRole("button", { name: "Check session" }).click();
  await page.getByText("Dashboard session is active.").waitFor();
  stage = "csrf_renew_click";
  await page.getByRole("button", { name: "Sign in again" }).click();
  stage = "csrf_login";
  await page.getByRole("heading", { name: "Sign in" }).waitFor();
  await page.getByLabel("Administrator password").fill(credential);
  const renewalResponse = page.waitForResponse((item) =>
    new URL(item.url()).pathname === "/api/v1/session" && item.request().method() === "POST");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  const renewal = await renewalResponse;
  stage = `csrf_reauth_status_${renewal.status()}`;
  requireTruth(renewal.status() === 204, "renewal_login_denied");
  stage = "csrf_reauth_shell";
  await page.getByRole("heading", { name: "API tokens" }).waitFor();
  stage = "invalid_csrf_server_denial";
  await page.evaluate(() => { document.cookie = "agentmonitor_csrf=invalid; Path=/; SameSite=Strict"; });
  await page.getByLabel("Token name").fill("csrf-rejected");
  await page.getByRole("checkbox", { name: "Manage API tokens" }).check();
  const csrfDenial = page.waitForResponse((item) =>
    new URL(item.url()).pathname === "/api/v1/api-tokens" && item.request().method() === "POST");
  await page.getByRole("button", { name: "Create token" }).click();
  const rejected = await csrfDenial;
  requireTruth(rejected.status() === 403, "invalid_csrf_not_denied");
  await page.getByRole("button", { name: "Sign in again" }).waitFor();
  requireTruth(await oneTime.count() === 0, "invalid_csrf_issued_secret");
  await page.getByRole("button", { name: "Refresh summaries" }).click();
  requireTruth(await page.getByRole("row", { name: /csrf-rejected/ }).count() === 0, "invalid_csrf_created_token");
  await bearerClient.dispose();
  requireTruth(externalHosts.size === 0, "external_request");
  requireTruth(pageErrors.length === 0, "page_error");
  await browser.close();
  console.log("P02 API TOKENS BROWSER: PASSED");
} catch {
  if (browser) await browser.close();
  console.error(`P02 API TOKENS BROWSER: FAILED — ${stage}`);
  process.exitCode = 1;
}
