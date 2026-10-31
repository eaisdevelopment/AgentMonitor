/** Real isolated LAN browser; administrator password arrives only on private stdin. */
import { readFileSync } from "node:fs";
import { randomUUID } from "node:crypto";
import { chromium } from "../../frontend/node_modules/@playwright/test/index.mjs";

const origin = process.argv[2];
const credential = readFileSync(0, "utf8");
let browser;
let stage = "lan_browser";
let browserRandomUuidAvailable = true;
try {
  browser = await chromium.launch({ channel: "chrome", headless: true });
  const page = await browser.newPage({ baseURL: origin });
  let providerMutations = 0;
  const failedReads = [];
  page.on("response", response => {
    if (new URL(response.url()).pathname.startsWith("/api/v1/") && response.request().method() === "GET" && response.status() !== 200) failedReads.push(response.status());
  });
  page.on("request", request => {
    if (new URL(request.url()).pathname.endsWith("/connection") && !["GET", "HEAD"].includes(request.method())) providerMutations += 1;
  });
  await page.goto(origin + "/login");
  stage = "lan_sign_in";
  await page.getByLabel("Administrator password").fill(credential);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await page.getByRole("heading", { name: "AgentMonitor", exact: true }).waitFor();
  failedReads.length = 0;
  stage = "lan_overview";
  await page.getByText("No accounts are registered. Add an account from Accounts.", { exact: true }).waitFor();
  await page.getByRole("button", { name: "Refresh overview", exact: true }).click();
  await page.getByRole("button", { name: "Refresh overview", exact: true }).waitFor();
  stage = "lan_admin_navigation";
  await page.getByRole("button", { name: "Organizations", exact: true }).click();
  await page.getByRole("heading", { name: "Organizations", exact: true }).waitFor();
  stage = "lan_organization_create";
  const name = `LAN browser record ${randomUUID()}`;
  await page.getByLabel("Organization name", { exact: true }).fill(name);
  browserRandomUuidAvailable = await page.evaluate(() => typeof crypto.randomUUID === "function");
  await page.getByRole("button", { name: "Create organization", exact: true }).click();
  await page.getByRole("article").filter({ has: page.getByText(name, { exact: true }) }).waitFor({ timeout: 5_000 });
  stage = "lan_account_navigation";
  await page.getByRole("button", { name: "Accounts", exact: true }).click();
  await page.getByRole("heading", { name: "Accounts", exact: true }).waitFor();
  await page.reload();
  await page.getByRole("heading", { name: "Accounts", exact: true }).waitFor();
  if (providerMutations !== 0) throw new Error("provider_authentication_started");
  if (failedReads.length > 0) throw new Error("lan_versioned_read_denied");
  await browser.close();
  console.log("LAN DASHBOARD BROWSER: PASSED — real built Chrome, sign-in, overview refresh, organization creation and account/admin navigation");
} catch (error) {
  if (browser) await browser.close();
  const reason = error instanceof Error && /^[a-z_]+$/.test(error.message) ? error.message : stage === "lan_organization_create" && !browserRandomUuidAvailable ? "lan_http_idempotent_creation_failed" : "real_browser_unavailable";
  console.log(`LAN DASHBOARD BROWSER: FAILED — ${stage}: ${reason}`);
  process.exitCode = 1;
}
