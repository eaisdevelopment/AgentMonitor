"use strict";

import { createServer } from "node:http";
import { readFileSync } from "node:fs";
import { chromium } from "@playwright/test";

const origin = process.argv[2];
const credential = readFileSync(0, "utf8");
const attacker = createServer((_request, response) => {
  response.writeHead(200, { "Content-Type": "text/html; charset=utf-8" });
  response.end("<!doctype html><title>Independent origin</title>");
});
let browser;
let stage = "attacker_server";
const requireTruth = (condition, reason) => {
  if (!condition) throw new Error(reason);
};

try {
  const host = new URL(origin).hostname;
  await new Promise((resolve) => attacker.listen(0, host, resolve));
  const address = attacker.address();
  requireTruth(address && typeof address !== "string", "attacker_socket_missing");
  const attackOrigin = `http://${host}:${address.port}`;
  requireTruth(attackOrigin !== origin, "attacker_origin_not_distinct");

  stage = "browser_login";
  browser = await chromium.launch({ channel: "chrome", headless: true });
  const context = await browser.newContext();
  const login = await context.newPage();
  await login.goto(`${origin}/login`);
  await login.getByLabel("Administrator password").fill(credential);
  await login.getByRole("button", { name: "Sign in" }).click();
  await login.getByRole("heading", { name: "AgentMonitor" }).waitFor();
  await login.close();

  // Actual elapsed time is necessary: session activity is coalesced for 60 seconds.
  stage = "elapsed_idle_window";
  await new Promise((resolve) => setTimeout(resolve, 62000));
  const page = await context.newPage();
  const cdp = await context.newCDPSession(page);
  const targetRequests = new Set();
  const targetStatus = new Map();
  await cdp.send("Network.enable");
  cdp.on("Network.requestWillBeSent", (event) => {
    if (new URL(event.request.url).pathname === "/api/v1/session")
      targetRequests.add(event.requestId);
  });
  cdp.on("Network.responseReceived", (event) => {
    targetStatus.set(event.requestId, event.response.status);
  });
  cdp.on("Network.responseReceivedExtraInfo", (event) => {
    targetStatus.set(event.requestId, event.statusCode);
  });
  await page.goto(attackOrigin);
  const attempted = [];
  context.on("request", (request) => {
    if (new URL(request.url()).pathname !== "/api/v1/session") return;
    attempted.push(request);
  });

  stage = "hostile_image";
  await page.evaluate(async ({ target, noReferrer }) => {
    await new Promise((resolve) => {
      const image = new Image();
      image.onload = resolve;
      image.onerror = resolve;
      if (noReferrer) image.referrerPolicy = "no-referrer";
      image.src = `${target}/api/v1/session${noReferrer ? "?probe=no-referrer" : ""}`;
      document.body.append(image);
    });
  }, { target: origin, noReferrer: false });
  await page.waitForTimeout(250);
  stage = "hostile_image_without_referrer";
  await page.evaluate(async ({ target, noReferrer }) => {
    await new Promise((resolve) => {
      const image = new Image();
      image.onload = resolve;
      image.onerror = resolve;
      if (noReferrer) image.referrerPolicy = "no-referrer";
      image.src = `${target}/api/v1/session${noReferrer ? "?probe=no-referrer" : ""}`;
      document.body.append(image);
    });
  }, { target: origin, noReferrer: true });
  await page.waitForTimeout(250);

  requireTruth(attempted.length === 2, "target_request_count_unexpected");
  requireTruth(
    attempted.every((request) => !Object.hasOwn(request.headers(), "origin")),
    "origin_header_unexpected"
  );
  const statuses = [...targetRequests].map((id) => targetStatus.get(id) ?? null);
  requireTruth(statuses.length === 2, "target_network_count_unexpected");

  await browser.close();
  await new Promise((resolve) => attacker.close(resolve));
  console.log(`P02 HOSTILE RESOURCE: image_status=${statuses[0]}`);
  console.log(`P02 HOSTILE RESOURCE: no_referrer_status=${statuses[1]}`);
} catch (error) {
  if (browser) await browser.close();
  await new Promise((resolve) => attacker.close(resolve));
  console.error(`P02 HOSTILE RESOURCE: FAILED — ${stage} (${error?.name ?? "unknown"})`);
  process.exitCode = 1;
}
