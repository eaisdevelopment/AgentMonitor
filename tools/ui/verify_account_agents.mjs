/** Real owner dashboard check; never creates an account or assigns an agent. */
import { chromium } from "../../frontend/node_modules/@playwright/test/index.mjs";

const endpoint = process.env.AGENTMONITOR_TEST_DASHBOARD_CDP_ENDPOINT;
const origin = process.env.AGENTMONITOR_TEST_DASHBOARD_ORIGIN;
const accountId = process.env.AGENTMONITOR_TEST_AGENT_ACCOUNT_ID;
let stage = "prerequisites";
class VerificationError extends Error {
  constructor(message, blocked = false) { super(message); this.blocked = blocked; }
}
function requireResult(condition, reason) { if (!condition) throw new VerificationError(reason); }
function requireLive(condition, reason) { if (!condition) throw new VerificationError(reason, true); }

try {
  requireLive(endpoint && origin && accountId && new URL(endpoint).hostname === "127.0.0.1" && new URL(origin).hostname === "127.0.0.1", "explicit_owner_dashboard_and_account_required");
  let browser;
  try { browser = await chromium.connectOverCDP(endpoint); }
  catch { throw new VerificationError("shared_dashboard_required", true); }
  const page = browser.contexts().flatMap(context => context.pages())
    .find(candidate => new URL(candidate.url()).origin === origin);
  requireLive(page, "shared_dashboard_required");
  const read = async () => page.evaluate(async (id) => {
    const query = async path => { const response = await fetch(path); if (!response.ok) throw new Error("authenticated_versioned_read_required"); return response.json(); };
    return { accounts: await query("/api/v1/accounts?limit=200"), locations: await query("/api/v1/process-locations"), selectedId: id };
  }, accountId);
  const snapshot = await read();
  requireLive(snapshot.accounts.items.some(item => item.account_id === accountId && item.provider_key === "claude"), "real_registered_claude_account_required");
  const claudeLocations = snapshot.locations.items.filter(item => item.provider_key === "claude");
  requireResult(snapshot.locations.availability.state === "available" && claudeLocations.length > 0, "real_running_claude_processes_missing");
  stage = "installed_version_process_coverage";
  if (process.env.AGENTMONITOR_TEST_AGENT_PID) {
    requireResult(claudeLocations.some(item => item.pid === Number(process.env.AGENTMONITOR_TEST_AGENT_PID)), "owner_reported_running_terminal_missing");
  }
  stage = "process_account_contract";
  requireResult(claudeLocations.every(item => typeof item.association_key === "string" && Object.hasOwn(item, "account_association")), "process_account_association_contract_missing");
  let mutations = 0;
  page.on("request", request => { if (new URL(request.url()).origin === origin && request.url().includes("/api/v1/") && !["GET", "HEAD"].includes(request.method())) mutations += 1; });
  await page.goto(origin);
  const overviewRow = page.getByRole("table", { name: "Account quota overview", exact: true }).locator(`tbody tr[data-account-id="${accountId}"]`);
  await overviewRow.getByRole("button").first().click();
  stage = "account_agent_drill_down";
  await page.getByRole("heading", { name: "Agents using this account", exact: true }).waitFor({ timeout: 10_000 });
  const linked = claudeLocations.filter(item => item.account_association?.account_id === accountId);
  const table = page.getByRole("table", { name: "Agents using this account", exact: true });
  if (linked.length === 0) {
    await page.getByText("No agents linked to this account yet.", { exact: true }).waitFor({ timeout: 10_000 });
    requireResult(await table.count() === 0 && await page.getByText("No agents linked to this account yet.", { exact: true }).count() === 1, "unlinked_account_not_explicit");
  } else {
    await table.waitFor({ timeout: 10_000 });
    requireResult(await table.locator("tbody tr").count() === linked.length, "account_agent_rows_mismatch");
    for (const item of linked) {
      const row = table.locator(`tbody tr[data-association-key="${item.association_key}"]`);
      requireResult(await row.count() === 1 && (await row.textContent()).includes(String(item.pid)), "linked_real_process_missing");
      requireResult((await row.textContent()).includes("Owner confirmed"), "owner_confirmation_provenance_missing");
      if (item.working_directory !== null) requireResult((await row.textContent()).includes(item.working_directory), "actual_working_directory_missing");
      await row.locator("summary").click();
      requireResult((await row.textContent()).includes("Start identity"), "guarded_process_details_missing");
    }
  }
  stage = "unlinked_agent_controls";
  const unlinked = claudeLocations.filter(item => item.account_association === null);
  const section = page.locator("details[data-unlinked-agents]");
  if (unlinked.length > 0) {
    await section.locator("summary").first().click();
    const first = section.locator(`tr[data-association-key="${unlinked[0].association_key}"]`);
    await first.getByRole("button", { name: "Link account", exact: true }).click();
    const form = first.locator("form");
    const save = form.getByRole("button", { name: "Confirm account link", exact: true });
    requireResult(await save.isDisabled(), "account_link_does_not_require_owner_confirmation");
    requireResult(await form.getByRole("checkbox").count() === 1 && (await form.textContent()).includes("/status"), "official_status_confirmation_guidance_missing");
    await form.getByRole("button", { name: "Cancel", exact: true }).click();
  }
  stage = "responsive_and_read_only";
  const viewport = await page.evaluate(() => ({ width: innerWidth, height: innerHeight }));
  for (const [width, height] of [[1920, 1080], [1280, 900], [390, 844]]) {
    await page.setViewportSize({ width, height });
    await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
    requireResult(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), "account_agent_view_overflows");
  }
  await page.setViewportSize(viewport);
  requireResult(mutations === 0, "read_only_check_mutated_owner_state");
  if (process.env.AGENTMONITOR_TEST_REQUIRE_CONFIRMED_AGENT === "1") {
    requireResult(linked.length > 0, "owner_confirmed_real_agent_required");
    if (process.env.AGENTMONITOR_TEST_AGENT_PID) requireResult(linked.some(item => item.pid === Number(process.env.AGENTMONITOR_TEST_AGENT_PID)), "owner_selected_terminal_confirmation_required");
  }
  console.log(JSON.stringify({ status: "Passed", boundary: "real account agent read view and confirmation controls", liveProcesses: claudeLocations.length, linkedProcesses: linked.length, unlinkedProcesses: unlinked.length }));
  process.exit(0);
} catch (error) {
  const reason = error instanceof Error && /^[a-z0-9_]+$/.test(error.message) ? error.message : "real_dashboard_check_unavailable";
  const blocked = error instanceof VerificationError && error.blocked;
  console.error(`ACCOUNT AGENTS: ${blocked ? "BLOCKED" : "FAILED"} — ${stage}: ${reason}`);
  process.exit(blocked ? 3 : 1);
}
