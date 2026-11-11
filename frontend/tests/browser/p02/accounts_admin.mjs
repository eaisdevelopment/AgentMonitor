"use strict";

import { readFileSync } from "node:fs";
import assert from "node:assert/strict";
import { chromium } from "@playwright/test";

const origin = process.argv[2];
const credential = readFileSync(0, "utf8");
let browser;
let stage = "browser_launch";

try {
  browser = await chromium.launch({ channel: "chrome", headless: true });
  const page = await browser.newPage({ baseURL: origin, viewport: { width: 1280, height: 800 } });
  stage = "login";
  await page.goto(`${origin}/login`);
  await page.getByLabel("Administrator password").fill(credential);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.getByRole("heading", { name: "AgentMonitor" }).waitFor();
  stage = "create_organization";
  await page.getByRole("button", { name: "Organizations", exact: true }).click();
  await page.getByLabel("Organization name").fill("Browser organization");
  await page.getByRole("button", { name: "Create organization" }).click();
  await page.getByText("Browser organization", { exact: true }).waitFor();
  stage = "create_api_billing_account";
  await page.getByRole("button", { name: "Accounts", exact: true }).click();
  const apiMode = page.getByRole("button", { name: "Add API billing account", exact: true });
  await apiMode.focus();
  await page.keyboard.press("Enter");
  assert.equal(await apiMode.getAttribute("aria-pressed"), "true");
  assert.deepEqual(await page.getByLabel("Provider", { exact: true }).locator("option").allTextContents(),
    ["Choose a provider", "Anthropic API", "OpenAI API", "Ollama Cloud"]);
  await page.getByLabel("Provider", { exact: true }).selectOption("claude");
  await page.getByLabel("Account name").fill("Browser API billing account");
  await page.getByLabel("Organization", { exact: true }).selectOption({ label: "Browser organization" });
  const creation = page.waitForResponse((response) =>
    response.url().endsWith("/api/v1/accounts") && response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Create API billing account", exact: true }).click();
  const createdResponse = await creation;
  assert.equal(createdResponse.status(), 201);
  const created = await createdResponse.json();
  assert.equal(created.initial_connection_purpose, "api");
  assert.equal(created.monitoring_preference, "disabled");
  assert.equal(created.identity_state, "unresolved");
  await page.getByRole("heading", { name: "Browser API billing account", exact: true }).waitFor();
  assert.ok(new URL(page.url()).pathname.endsWith(`/accounts/${created.account_id}`));
  stage = "api_only_detail";
  await page.getByRole("heading", { name: "API billing setup", exact: true }).waitFor();
  stage = "create_billing_connection";
  await page.getByLabel("Provider billing scope (optional)").fill("billing-scope-browser");
  const bindingCreation = page.waitForResponse((response) =>
    response.url().endsWith(`/accounts/${created.account_id}/billing-connections`) && response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Add API billing connection", exact: true }).click();
  const bindingResponse = await bindingCreation;
  assert.equal(bindingResponse.status(), 201);
  assert.equal(bindingResponse.request().headers()["if-match"], `"${created.account_id}.${created.record_version}"`);
  assert.ok(bindingResponse.request().headers()["idempotency-key"]);
  const binding = await bindingResponse.json();
  assert.equal(binding.account_id, created.account_id);
  assert.equal(binding.lifecycle, "pending");
  assert.equal(binding.monitoring_preference, "disabled");
  assert.equal(binding.scope_evidence, "owner_asserted");
  await page.getByText("billing-scope-browser", { exact: true }).waitFor();
  await page.getByText("API monitoring is off.", { exact: true }).waitFor();
  await page.getByText("Access has not been verified.", { exact: true }).waitFor();
  assert.equal(await page.getByRole("button", { name: "Connect Claude", exact: true }).count(), 0);
  assert.equal(await page.locator("details.quota-history, [data-account-sessions]").count(), 0);
  assert.equal(await page.getByRole("heading", { name: "Account activity", exact: true }).count(), 0);
  assert.equal(await page.getByRole("heading", { name: "Agents using this account", exact: true }).count(), 0);
  assert.equal(await page.locator('input[type="email"]').count(), 0);
  assert.equal(await page.locator('input[type="password"]').count(), 0);
  await page.reload();
  await page.getByRole("heading", { name: "API billing setup", exact: true }).waitFor();
  await page.getByText("billing-scope-browser", { exact: true }).waitFor();
  assert.equal(await page.getByRole("button", { name: "Add API billing connection", exact: true }).count(), 0);
  stage = "api_only_responsive";
  await page.setViewportSize({ width: 390, height: 844 });
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1), false);
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.getByRole("button", { name: "Accounts", exact: true }).click();
  const apiCard = page.getByRole("article").filter({ hasText: "Browser API billing account" });
  assert.equal(await apiCard.getByRole("button", { name: "Connect Claude", exact: true }).count(), 0);
  stage = "create_account";
  await page.getByLabel("Provider", { exact: true }).fill("claude");
  await page.getByLabel("Account name").fill("Browser account");
  await page.getByLabel("Organization", { exact: true }).selectOption({ label: "Browser organization" });
  await page.getByRole("button", { name: "Add account" }).click();
  await page.getByText("Browser account", { exact: true }).waitFor();
  const subscriptionCard = page.getByRole("article").filter({ hasText: "Browser account" });
  await subscriptionCard.getByText("pending · monitoring disabled").waitFor();
  stage = "account_edit";
  await subscriptionCard.getByRole("button", { name: "Open account" }).click();
  stage = "subscription_billing_collapsed";
  await page.getByRole("heading", { name: "Account activity", exact: true }).waitFor();
  const subscriptionBillingAction = page.getByRole("button", { name: "Add API billing connection", exact: true, includeHidden: true });
  await subscriptionBillingAction.waitFor({ state: "attached" });
  assert.equal(await subscriptionBillingAction.isVisible(), false);
  await page.locator("details[data-billing-connection] > summary").click();
  await page.getByRole("button", { name: "Add API billing connection", exact: true }).waitFor();
  stage = "account_edit";
  const mixedCreation = page.waitForResponse((response) =>
    response.url().endsWith("/billing-connections") && response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Add API billing connection", exact: true }).click();
  const mixedResponse = await mixedCreation;
  assert.equal(mixedResponse.status(), 201);
  const mixedBinding = await mixedResponse.json();
  assert.equal(mixedBinding.scope_id, null);
  assert.equal(mixedBinding.scope_evidence, "unresolved");
  assert.equal(mixedBinding.monitoring_preference, "disabled");
  await page.getByText("Provider billing scope has not been specified.", { exact: true }).waitFor();
  await page.getByRole("heading", { name: "Account activity", exact: true }).waitFor();
  await page.getByRole("button", { name: "Edit account" }).click();
  await page.getByText("Withheld from dashboard", { exact: true }).waitFor();
  await page.getByText("Account names and organization assignments are administrator managed.", { exact: true }).waitFor();
  await page.getByLabel("Rename account").fill("Renamed browser account");
  await page.getByRole("button", { name: "Save account name" }).click();
  await page.getByText("Account name saved.").waitFor();
  await page.getByRole("heading", { name: "Renamed browser account" }).waitFor();
  await page.getByRole("button", { name: "Archive account" }).click();
  await page.getByRole("button", { name: "Restore account" }).waitFor();
  await page.getByRole("button", { name: "Restore account" }).click();
  await page.getByRole("button", { name: "Archive account" }).waitFor();
  stage = "automatic_capacity_refresh";
  await page.locator("details.quota-history > summary").click();
  await page.getByRole("heading", { name: "Capacity history", exact: true }).waitFor();
  await page.waitForResponse((response) =>
    response.url().includes("/capacity") && response.request().method() === "GET" && response.status() === 200,
    { timeout: 35_000 },
  );
  stage = "responsive";
  await page.setViewportSize({ width: 390, height: 844 });
  if (await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1)) {
    throw new Error("horizontal_overflow");
  }
  stage = "ollama_existing_cloud_required";
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.getByRole("button", { name: "Accounts", exact: true }).click();
  await page.getByRole("button", { name: "Add API billing account", exact: true }).click();
  await page.getByLabel("Provider", { exact: true }).selectOption("ollama");
  await page.getByLabel("Account name").fill("Browser cloud billing account");
  await page.getByRole("button", { name: "Create API billing account", exact: true }).click();
  await page.getByRole("heading", { name: "Browser cloud billing account", exact: true }).waitFor();
  await page.getByText("Ollama Cloud billing uses the existing cloud connection flow. API-only setup is not available yet.", { exact: true }).waitFor();
  assert.equal(await page.getByRole("button", { name: "Add API billing connection", exact: true }).count(), 0);
  await browser.close();
  console.log("P02 ACCOUNTS ADMIN: PASSED — real API, SQLite, and built browser");
} catch (error) {
  if (browser) await browser.close();
  console.error(`P02 ACCOUNTS ADMIN: FAILED — ${stage}: ${error instanceof Error ? error.message : "unknown"}`);
  process.exitCode = 1;
}
