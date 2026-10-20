"use strict";

import { readFileSync } from "node:fs";
import { randomBytes } from "node:crypto";
import { chromium } from "@playwright/test";

const origin = process.argv[2];
const initialCredential = readFileSync(0, "utf8");
const nextCredential = randomBytes(32).toString("base64url");
const expectedMutationRequests = [
  ["GET", "/api/v1/session"],
  ["PATCH", "/api/v1/session/password"],
  ["GET", "/api/v1/session"],
];
const expectedSessionPasswordExchange = [
  ["request", "GET", "/api/v1/session"],
  ["response", "GET", "/api/v1/session", 200],
  ["request", "PATCH", "/api/v1/session/password"],
  ["response", "PATCH", "/api/v1/session/password", 204],
  ["request", "GET", "/api/v1/session"],
  ["response", "GET", "/api/v1/session", 200],
];
const expectedMutationExchange = [
  ...expectedSessionPasswordExchange,
  ["feature-request"],
];

function ensure(value) {
  if (!value) throw new Error("password_change_assertion_failed");
}

function apiPath(url) {
  const parsed = new URL(url);
  return parsed.origin === origin && parsed.pathname.startsWith("/api/v1/")
    ? parsed.pathname
    : null;
}

let browser;
let stage = "browser_launch";
try {
  browser = await chromium.launch({ channel: "chrome", headless: true });
  const page = await browser.newPage({ baseURL: origin });
  const requestEvents = [];
  const exchangeEvents = [];
  page.on("request", (request) => {
    const path = apiPath(request.url());
    if (path === null) return;
    const event = {
      method: request.method(),
      path,
      startTime: Date.now(),
    };
    requestEvents.push(event);
    exchangeEvents.push({ kind: "request", ...event });
  });
  page.on("response", (response) => {
    const path = apiPath(response.url());
    if (path === null) return;
    exchangeEvents.push({
      kind: "response",
      method: response.request().method(),
      path,
      status: response.status(),
    });
  });

  stage = "initial_login";
  await page.goto(`${origin}/login`);
  await page.getByRole("heading", { name: "Sign in" }).waitFor();
  await page.getByLabel("Administrator password").fill(initialCredential);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.getByRole("heading", { name: "AgentMonitor" }).waitFor();

  await page.evaluate(() => {
    const frame = document.querySelector(".dashboard-frame");
    if (!(frame instanceof HTMLElement)) throw new Error("password_lifecycle_missing");
    const trace = [];
    Object.defineProperty(globalThis, "__agentmonitorPasswordLifecycleTrace", {
      configurable: true,
      value: trace,
    });
    new MutationObserver((records) => {
      const observedAt = performance.timeOrigin + performance.now();
      for (const record of records) {
        if (record.type === "attributes" && record.target === frame
          && record.attributeName === "data-password-lifecycle") {
          trace.push({ kind: "phase", oldValue: record.oldValue, at: observedAt });
        } else if (record.type === "attributes" && record.target === frame
          && record.attributeName === "data-password-cleanup-acknowledged") {
          trace.push({ kind: "cleanup-ack", oldValue: record.oldValue, at: observedAt });
        } else if (record.type === "attributes" && record.target === frame
          && record.attributeName === "data-session-action") {
          trace.push({
            kind: "session-action",
            oldValue: record.oldValue,
            value: frame.getAttribute("data-session-action"),
            at: observedAt,
          });
        } else if (record.type === "childList") {
          for (const node of record.addedNodes) {
            if (!(node instanceof HTMLElement)) continue;
            trace.push({
              kind: "content",
              preparation: node.textContent?.includes("Preparing secure password change") ?? false,
              interactive: node.matches("#current-password") || node.querySelector("#current-password") !== null,
              at: observedAt,
            });
          }
        }
      }
    }).observe(frame, {
      attributeFilter: [
        "data-password-cleanup-acknowledged",
        "data-password-lifecycle",
        "data-session-action",
      ],
      attributeOldValue: true,
      attributes: true,
      childList: true,
      subtree: true,
    });
    const changeControl = Array.from(document.querySelectorAll("button"))
      .find((button) => button.textContent?.trim() === "Change password");
    if (!(changeControl instanceof HTMLButtonElement)) throw new Error("password_control_missing");
    changeControl.addEventListener("click", () => {
      trace.push({ kind: "boundary", name: "open", at: performance.timeOrigin + performance.now() });
    }, { capture: true, once: true });
  });

  stage = "password_open";
  const crossingSessionResponse = page.waitForResponse((response) =>
    response.request().method() === "GET" && apiPath(response.url()) === "/api/v1/session",
  );
  await page.evaluate(() => {
    const buttons = Array.from(document.querySelectorAll("button"));
    const checkSession = buttons.find((button) => button.textContent?.trim() === "Check session");
    const changePassword = buttons.find((button) => button.textContent?.trim() === "Change password");
    if (!(checkSession instanceof HTMLButtonElement)
      || !(changePassword instanceof HTMLButtonElement)) throw new Error("header_crossing_controls_missing");
    checkSession.click();
    changePassword.click();
  });
  stage = "password_draining";
  await page.locator('.dashboard-frame[data-password-lifecycle="ready"]').waitFor();
  ensure((await crossingSessionResponse).status() === 200);
  const firstTrace = await page.evaluate(() => globalThis.__agentmonitorPasswordLifecycleTrace);
  const firstClosed = firstTrace.findIndex((entry) => entry.kind === "phase" && entry.oldValue === "closed");
  const preparation = firstTrace.findIndex((entry) => entry.kind === "content" && entry.preparation && !entry.interactive);
  const cleanupAcknowledged = firstTrace.findIndex((entry) => entry.kind === "cleanup-ack" && entry.oldValue === "false");
  const firstReady = firstTrace.findIndex((entry) => entry.kind === "phase" && entry.oldValue === "draining");
  const firstInteractive = firstTrace.findIndex((entry) => entry.kind === "content" && entry.interactive);
  ensure(firstClosed >= 0);
  ensure(preparation >= 0);
  ensure(cleanupAcknowledged > firstClosed && cleanupAcknowledged > preparation);
  ensure(firstReady > cleanupAcknowledged);
  ensure(firstInteractive > cleanupAcknowledged);

  stage = "password_ready";
  await page.locator('.dashboard-frame[data-session-action="idle"]').waitFor();
  ensure(await page.getByText("Dashboard session is active.").count() === 0);
  ensure(await page.getByRole("heading", { name: "Sign in" }).count() === 0);
  ensure(await page.locator(".operations-console").count() === 0);
  ensure(await page.getByRole("button", { name: "Check session" }).isDisabled());
  ensure(await page.getByRole("button", { name: "Sign out" }).isDisabled());
  ensure(await page.getByRole("navigation", { name: "Primary" }).getByRole("button").evaluateAll(
    (buttons) => buttons.length > 0 && buttons.every((button) => button.disabled),
  ));
  ensure(await page.evaluate(() => document.activeElement?.id === "current-password"));
  await page.evaluate(() => {
    history.pushState(null, "", "/accounts");
    dispatchEvent(new PopStateEvent("popstate"));
  });
  ensure(await page.evaluate(() => location.pathname === "/"));

  stage = "password_cancel";
  await page.getByRole("button", { name: "Cancel" }).click();
  const passwordControl = page.getByRole("button", { name: "Change password" });
  await passwordControl.waitFor();
  ensure(await passwordControl.evaluate((button) => button === document.activeElement));

  stage = "password_open";
  await page.evaluate(() => {
    const trace = globalThis.__agentmonitorPasswordLifecycleTrace;
    trace.splice(0);
    const changeControl = Array.from(document.querySelectorAll("button"))
      .find((button) => button.textContent?.trim() === "Change password");
    if (!(changeControl instanceof HTMLButtonElement)) throw new Error("password_control_missing");
    changeControl.addEventListener("click", () => {
      trace.push({ kind: "boundary", name: "open", at: performance.timeOrigin + performance.now() });
    }, { capture: true, once: true });
  });
  await passwordControl.click();
  await page.locator('.dashboard-frame[data-password-lifecycle="ready"]').waitFor();
  ensure(await page.evaluate(() => document.activeElement?.id === "current-password"));
  await page.evaluate(() => {
    const form = document.querySelector(".password-form");
    if (!(form instanceof HTMLFormElement)) throw new Error("password_form_missing");
    form.addEventListener("submit", () => {
      globalThis.__agentmonitorPasswordLifecycleTrace.push({
        kind: "boundary",
        name: "submit",
        at: performance.timeOrigin + performance.now(),
      });
    }, { capture: true, once: true });
  });
  const readyRequestCount = requestEvents.length;
  await page.getByLabel("Current password").fill(initialCredential);
  await page.getByLabel("New password", { exact: true }).fill(nextCredential);
  await page.getByLabel("Confirm new password").fill(nextCredential);
  ensure(requestEvents.length === readyRequestCount);

  stage = "password_submit";
  const requestStart = requestEvents.length;
  const exchangeStart = exchangeEvents.length;
  const firstRemountedOverviewRequest = page.waitForRequest((request) => {
    const path = apiPath(request.url());
    return path !== null && path !== "/api/v1/session" && path !== "/api/v1/session/password";
  });
  await page.evaluate(() => {
    const form = document.querySelector(".password-form");
    const submit = form?.querySelector('button[type="submit"]');
    if (!(form instanceof HTMLFormElement) || !(submit instanceof HTMLButtonElement)) {
      throw new Error("password_submit_control_missing");
    }
    submit.click();
    form.dispatchEvent(new SubmitEvent("submit", {
      bubbles: true,
      cancelable: true,
      submitter: submit,
    }));
  });
  stage = "password_request_oracle";
  await page.getByText("Password changed. Other browser sessions were revoked.").waitFor();
  await firstRemountedOverviewRequest;

  const firstRemountedFeatureRequestIndex = exchangeEvents.findIndex((event, index) =>
    index >= exchangeStart
      && event.kind === "request"
      && event.path !== "/api/v1/session"
      && event.path !== "/api/v1/session/password",
  );
  ensure(firstRemountedFeatureRequestIndex >= exchangeStart);
  const mutationExchange = exchangeEvents
    .slice(exchangeStart, firstRemountedFeatureRequestIndex + 1)
    .filter((event, index, events) =>
      event.path === "/api/v1/session"
        || event.path === "/api/v1/session/password"
        || index === events.length - 1,
    )
    .map((event) => {
      if (event.path !== "/api/v1/session" && event.path !== "/api/v1/session/password") {
        return ["feature-request"];
      }
      return event.kind === "response"
        ? [event.kind, event.method, event.path, event.status]
        : [event.kind, event.method, event.path];
    });
  ensure(JSON.stringify(mutationExchange) === JSON.stringify(expectedMutationExchange));

  stage = "password_success";
  const finalTrace = await page.evaluate(() => globalThis.__agentmonitorPasswordLifecycleTrace);
  const secondClosed = finalTrace.findIndex((entry) => entry.kind === "phase" && entry.oldValue === "closed");
  const secondPreparation = finalTrace.findIndex((entry) => entry.kind === "content" && entry.preparation && !entry.interactive);
  const secondCleanupAcknowledged = finalTrace.findIndex((entry) => entry.kind === "cleanup-ack" && entry.oldValue === "false");
  const secondReady = finalTrace.findIndex((entry) => entry.kind === "phase" && entry.oldValue === "draining");
  const secondInteractive = finalTrace.findIndex((entry) => entry.kind === "content" && entry.interactive);
  const submitting = finalTrace.findIndex((entry) => entry.kind === "phase" && entry.oldValue === "ready");
  const successfulClose = finalTrace.findIndex((entry) => entry.kind === "phase" && entry.oldValue === "submitting");
  const openBoundary = finalTrace.find((entry) => entry.kind === "boundary" && entry.name === "open")?.at;
  const readyBoundary = finalTrace.find((entry) => entry.kind === "phase" && entry.oldValue === "draining")?.at;
  const submitBoundary = finalTrace.find((entry) => entry.kind === "boundary" && entry.name === "submit")?.at;
  const closeBoundary = finalTrace.find((entry) => entry.kind === "phase" && entry.oldValue === "submitting")?.at;
  ensure(secondClosed >= 0);
  ensure(secondPreparation >= 0);
  ensure(secondCleanupAcknowledged > secondClosed && secondCleanupAcknowledged > secondPreparation);
  ensure(secondReady > secondCleanupAcknowledged);
  ensure(secondInteractive > secondCleanupAcknowledged);
  ensure(submitting > secondInteractive);
  ensure(successfulClose > submitting);
  ensure(typeof openBoundary === "number");
  ensure(typeof readyBoundary === "number" && readyBoundary >= openBoundary);
  ensure(typeof submitBoundary === "number" && submitBoundary >= readyBoundary);
  ensure(typeof closeBoundary === "number" && closeBoundary >= submitBoundary);
  const drainingRequests = requestEvents.filter(({ startTime }) =>
    startTime >= openBoundary && startTime < readyBoundary);
  const readyRequests = requestEvents.filter(({ startTime }) =>
    startTime >= readyBoundary && startTime < submitBoundary);
  const submittingRequests = requestEvents.filter(({ startTime }) =>
    startTime >= submitBoundary && startTime < closeBoundary)
    .map(({ method, path }) => [method, path]);
  ensure(drainingRequests.length === 0);
  ensure(readyRequests.length === 0);
  ensure(JSON.stringify(submittingRequests) === JSON.stringify(expectedMutationRequests));
  const firstRemountedFeatureRequest = requestEvents.slice(requestStart)
    .find(({ path }) => path !== "/api/v1/session" && path !== "/api/v1/session/password");
  ensure(firstRemountedFeatureRequest !== undefined
    && firstRemountedFeatureRequest.startTime >= closeBoundary);
  ensure(await page.locator('.dashboard-frame[data-password-lifecycle="closed"]').count() === 1);
  ensure(await page.locator(".operations-console").count() === 1);
  const successStatus = page.getByText("Password changed. Other browser sessions were revoked.");
  ensure(await successStatus.evaluate((status) => status.closest("[role=status]") === document.activeElement));

  stage = "route_stable";
  ensure(await page.evaluate(() => location.pathname === "/"));
  await page.locator(".fleet-overview[aria-busy=false]").waitFor();
  ensure(await page.getByRole("heading", { name: "Sign in" }).count() === 0);
  ensure(await successStatus.count() === 1);
  const stableExchangeCheckpoint = exchangeEvents.length;
  const completeSessionPasswordExchange = exchangeEvents
    .slice(exchangeStart, stableExchangeCheckpoint)
    .filter(({ path }) => path === "/api/v1/session" || path === "/api/v1/session/password")
    .map((event) => event.kind === "response"
      ? [event.kind, event.method, event.path, event.status]
      : [event.kind, event.method, event.path]);
  ensure(JSON.stringify(completeSessionPasswordExchange)
    === JSON.stringify(expectedSessionPasswordExchange));

  stage = "password_rotated";
  const logoutTraceStart = await page.evaluate(() => globalThis.__agentmonitorPasswordLifecycleTrace.length);
  await page.evaluate(() => {
    const buttons = Array.from(document.querySelectorAll("button"));
    const signOut = buttons.find((button) => button.textContent?.trim() === "Sign out");
    const changePassword = buttons.find((button) => button.textContent?.trim() === "Change password");
    if (!(signOut instanceof HTMLButtonElement)
      || !(changePassword instanceof HTMLButtonElement)) throw new Error("logout_crossing_controls_missing");
    signOut.click();
    changePassword.click();
  });
  await page.getByRole("heading", { name: "Sign in" }).waitFor();
  const logoutTrace = (await page.evaluate(() => globalThis.__agentmonitorPasswordLifecycleTrace))
    .slice(logoutTraceStart);
  ensure(logoutTrace.some((entry) => entry.kind === "session-action" && entry.oldValue === "idle"));
  ensure(!logoutTrace.some((entry) => entry.kind === "phase" && entry.oldValue === "closed"));
  stage = "old_credential_denied";
  await page.getByLabel("Administrator password").fill(initialCredential);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.getByText(/Sign-in failed/).waitFor();
  stage = "new_credential_accepted";
  await page.getByLabel("Administrator password").fill(nextCredential);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.getByRole("heading", { name: "AgentMonitor" }).waitFor();
  await browser.close();
  console.log("P02 PASSWORD CHANGE BROWSER: PASSED");
} catch {
  if (browser) {
    try {
      await browser.close();
    } catch {
      // Teardown cannot widen the scenario's closed failure output.
    }
  }
  console.error(`P02 PASSWORD CHANGE BROWSER: FAILED — ${stage}`);
  process.exitCode = 1;
}
