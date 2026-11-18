// A real disposable Chrome context goes offline. No response interception,
// seeded telemetry, owner credentials, account mutation or shared browser use.
import { readFileSync } from "node:fs";
let browser, stage = "launch";
const origin = process.argv[2];
const password = readFileSync(0, "utf8");
const requireEvidence = value => { if (!value) throw new Error("evidence_missing"); };
try {
  requireEvidence(/^http:\/\/127\.0\.0\.1:\d+$/.test(origin ?? ""));
  let playwright;
  try { playwright = await import("@playwright/test"); }
  catch (error) {
    if (error?.code !== "ERR_MODULE_NOT_FOUND") throw error;
    playwright = await import("/home/dev/.local/share/agentmonitor/worktrees/dashboard-product-promotion/frontend/node_modules/@playwright/test/index.mjs");
  }
  browser = await playwright.chromium.launch({ channel: "chrome", headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();
  page.setDefaultTimeout(10000);
  stage = "sign_in";
  await page.goto(origin);
  const status = await page.evaluate(async password => (await fetch("/api/v1/session", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ password }), credentials: "same-origin",
  })).status, password);
  requireEvidence(status === 204);
  await page.goto(origin);
  await page.getByRole("button", { name: "Accounts", exact: true }).waitFor();
  let failedRegistryRequests = 0, unsafeRequests = 0;
  page.on("requestfailed", request => {
    if (["/api/v1/accounts", "/api/v1/organizations"].includes(new URL(request.url()).pathname)) failedRegistryRequests++;
  });
  page.on("request", request => { if (!["GET", "HEAD", "OPTIONS"].includes(request.method())) unsafeRequests++; });
  stage = "transport_failure";
  await context.setOffline(true);
  await page.getByRole("button", { name: "Accounts", exact: true }).click();
  await page.getByRole("button", { name: "Retry accounts", exact: true }).waitFor();
  requireEvidence(failedRegistryRequests > 0);
  requireEvidence(await page.getByRole("button", { name: "Add API billing account", exact: true }).count() === 0);
  stage = "transport_recovery";
  await context.setOffline(false);
  await page.getByRole("button", { name: "Retry accounts", exact: true }).click();
  await page.getByRole("button", { name: "Add API billing account", exact: true }).click();
  await page.getByRole("heading", { name: "Add API billing account", exact: true }).waitFor();
  requireEvidence(await page.getByRole("button", { name: "Create API billing account", exact: true }).isDisabled());
  requireEvidence(await page.getByLabel("Provider", { exact: true }).locator("option").evaluateAll(options => JSON.stringify(options.map(option => option.value))) === JSON.stringify(["", "claude", "codex", "ollama"]));
  requireEvidence(unsafeRequests === 0);
  console.log("M7 SETUP NETWORK RECOVERY: PASSED");
} catch {
  console.log(`M7 SETUP NETWORK RECOVERY: FAILED ${stage}`);
  process.exitCode = 1;
} finally {
  if (browser) await browser.close();
}
