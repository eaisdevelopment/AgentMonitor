/** Genuine duplicate identity presentation; read only, no injected data. */
import { chromium } from "../../frontend/node_modules/@playwright/test/index.mjs";

const endpoint = process.env.AGENTMONITOR_TEST_DASHBOARD_CDP_ENDPOINT;
const origin = process.env.AGENTMONITOR_TEST_DASHBOARD_ORIGIN;
let stage = "prerequisites";
const requireResult = (value, reason) => { if (!value) throw new Error(reason); };
try {
  requireResult(endpoint && origin && new URL(endpoint).hostname === "127.0.0.1" && new URL(origin).hostname === "127.0.0.1", "explicit_shared_dashboard_required");
  const browser = await chromium.connectOverCDP(endpoint);
  const page = browser.contexts()[0]?.pages()[0];
  requireResult(page && await page.evaluate(() => location.origin) === origin, "authenticated_dashboard_required");
  const groups = await page.evaluate(async () => {
    const query = async path => { const response = await fetch(path); if (!response.ok) throw Error("authenticated_read_required"); return response.json(); };
    const accounts = (await query("/api/v1/accounts?limit=200")).items.filter(account => account.lifecycle !== "archived");
    const groups = new Map();
    for (const account of accounts) {
      const identity = await query("/api/v1/accounts/" + account.account_id + "/observed-identity");
      if (identity.state !== "verified" || identity.email === null || identity.provider_organization === null) continue;
      const key = JSON.stringify([account.provider_key, account.organization_id, identity.email, identity.provider_organization]);
      groups.set(key, [...(groups.get(key) ?? []), account]);
    }
    return [...groups.values()].filter(group => group.length > 1).map(group => ({ ids: group.map(account => account.account_id), names: group.map(account => account.friendly_name) }));
  });
  requireResult(groups.length > 0, "genuine_duplicate_provider_identity_required");
  await page.goto(origin);
  const table = page.getByRole("table", { name: "Account quota overview", exact: true });
  await table.waitFor();
  stage = "duplicate_identity_presentation";
  for (const group of groups) {
    const rows = table.locator(group.ids.map(id => 'tbody tr[data-account-id="' + id + '"]').join(","));
    requireResult(await rows.count() === 1, "duplicate_identity_quota_displayed_twice");
    requireResult((await rows.textContent()).includes(group.ids.length + " connected profiles"), "duplicate_connection_count_missing");
    requireResult(await rows.getByRole("button", { name: /^Review .+ connection$/ }).count() === group.ids.length - 1, "additional_connection_review_missing");
  }
  console.log(JSON.stringify({ status: "Passed", boundary: "genuine duplicate Claude identity overview", duplicateGroups: groups.length }));
  process.exit(0);
} catch (error) {
  const reason = error instanceof Error && /^[a-z0-9_]+$/.test(error.message) ? error.message : "real_duplicate_check_unavailable";
  console.error("DUPLICATE IDENTITY: BLOCKED — " + stage + ": " + reason);
  process.exit(3);
}
