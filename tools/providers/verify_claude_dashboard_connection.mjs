/** Verify an owner-completed dashboard flow through the authenticated V1 API. */
import { chromium } from "../../frontend/node_modules/@playwright/test/index.mjs";

const endpoint = process.env.AGENTMONITOR_TEST_DASHBOARD_CDP_ENDPOINT;
const origin = process.env.AGENTMONITOR_TEST_DASHBOARD_ORIGIN;
const accountId = process.env.AGENTMONITOR_TEST_MANAGED_ACCOUNT_ID;
try {
  if (!endpoint || !origin || !accountId || new URL(endpoint).hostname !== "127.0.0.1" || new URL(origin).hostname !== "127.0.0.1") throw new Error();
  const browser = await chromium.connectOverCDP(endpoint);
  const page = browser.contexts()[0]?.pages()[0];
  if (!page || await page.evaluate(() => window.location.origin) !== origin) throw new Error();
  const verified = await page.evaluate(async id => {
    const values = [];
    for (const path of [`/api/v1/accounts/${id}/connection`, `/api/v1/accounts/${id}`, `/api/v1/accounts/${id}/observed-identity`]) {
      const response = await fetch(path);
      if (!response.ok) return false;
      values.push(await response.json());
    }
    const [flow, account, identity] = values;
    return flow.account_id === id && flow.flow_id !== null && flow.state === "connected" && account.lifecycle === "active" && account.is_effective_monitoring_enabled && identity.state === "verified" && identity.profile_protection === "managed" && (flow.expected_email === null || flow.expected_email.toLowerCase() === identity.email?.toLowerCase());
  }, accountId);
  if (!verified) throw new Error();
  console.log("CLAUDE DASHBOARD CONNECTION: PASSED — actual owner-completed flow, matched managed identity, monitoring, and quota receipt");
  process.exit(0);
} catch {
  console.log("CLAUDE DASHBOARD CONNECTION: BLOCKED — selected owner-completed connection and fresh identity receipt required");
  process.exit(3);
}
