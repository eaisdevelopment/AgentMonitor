"use strict";

import { createServer } from "node:http";
import { readFileSync } from "node:fs";
import { chromium } from "@playwright/test";

const origin = process.argv[2];
const credential = readFileSync(0, "utf8");
let browser;
let attacker;
let stage = "attacker_server";
const requireTruth = (condition, reason) => {
  if (!condition) throw new Error(reason);
};

try {
  // A distinct real loopback HTTP origin supplies only an attacker-controlled page.
  // The target remains the production AgentMonitor server and real SQLite state.
  attacker = createServer((_request, response) => {
    response.writeHead(200, { "Content-Type": "text/html; charset=utf-8" });
    response.end("<!doctype html><html><head><title>Other origin</title></head><body>Other origin</body></html>");
  });
  await new Promise((resolve) => attacker.listen(0, "127.0.0.1", resolve));
  const address = attacker.address();
  requireTruth(address && typeof address !== "string", "attacker_socket_missing");
  const attackOrigin = `http://127.0.0.1:${address.port}`;
  requireTruth(attackOrigin !== origin, "attacker_origin_not_distinct");

  stage = "browser_login";
  browser = await chromium.launch({ channel: "chrome", headless: true });
  const context = await browser.newContext({ baseURL: origin });
  const page = await context.newPage();
  await page.goto(`${origin}/login`);
  await page.getByRole("heading", { name: "Sign in" }).waitFor();
  await page.getByLabel("Administrator password").fill(credential);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.getByRole("heading", { name: "AgentMonitor" }).waitFor();

  stage = "authenticated_state_before_attack";
  const before = await page.evaluate(async () => {
    const response = await fetch("/api/v1/session", { credentials: "same-origin" });
    if (response.status !== 200) return { status: response.status, sessionId: null };
    const body = await response.json();
    return { status: response.status, sessionId: body.session_id };
  });
  requireTruth(before.status === 200 && typeof before.sessionId === "string", "real_session_missing");

  stage = "hostile_page";
  const document = await page.goto(attackOrigin);
  requireTruth(document?.status() === 200, "attacker_page_missing");
  const denied = await page.evaluate(async (target) => {
    const attempt = async (method) => {
      try {
        const response = await fetch(`${target}/api/v1/session`, {
          method,
          credentials: "include",
        });
        // A readable cross-origin error is still a CORS boundary failure.
        return { opaque: false, status: response.status };
      } catch {
        return { opaque: true, status: null };
      }
    };
    return { read: await attempt("GET"), revoke: await attempt("DELETE") };
  }, origin);
  requireTruth(denied.read.opaque && denied.read.status === null, "cross_origin_readable");
  requireTruth(denied.revoke.opaque && denied.revoke.status === null, "cross_origin_mutation_readable");

  stage = "persisted_session_after_attack";
  await page.goto(`${origin}/settings/api-tokens`);
  await page.getByRole("heading", { name: "API tokens" }).waitFor();
  const after = await page.evaluate(async () => {
    const response = await fetch("/api/v1/session", { credentials: "same-origin" });
    if (response.status !== 200) return { status: response.status, sessionId: null };
    const body = await response.json();
    return { status: response.status, sessionId: body.session_id };
  });
  requireTruth(after.status === 200 && after.sessionId === before.sessionId, "real_session_changed_by_attack");
  await browser.close();
  await new Promise((resolve) => attacker.close(resolve));
  console.log("P02 SECURITY BOUNDARY BROWSER: PASSED");
} catch {
  if (browser) await browser.close();
  if (attacker) await new Promise((resolve) => attacker.close(resolve));
  console.error(`P02 SECURITY BOUNDARY BROWSER: FAILED — ${stage}`);
  process.exitCode = 1;
}
