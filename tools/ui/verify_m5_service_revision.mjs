/** Read-only proof for the M5 service activation revision and Registry state. */
import { chromium } from "../../frontend/node_modules/@playwright/test/index.mjs";

import {
  isExactServiceRevisionV1,
  publicRegistryDigestV1,
} from "./m5_codex_policy.mjs";
import { readAllRegistryItemsV1 } from "./m5_registry_pages.mjs";

const endpoint = process.env.AGENTMONITOR_TEST_DASHBOARD_CDP_ENDPOINT;
const origin = process.env.AGENTMONITOR_TEST_DASHBOARD_ORIGIN;
const revision = process.env.AGENTMONITOR_M5_IMPLEMENTATION_REVISION;
const mode = process.env.AGENTMONITOR_M5_SERVICE_REVISION_MODE;
let page;
let stage = "prerequisites";
let exitCode = 0;

const requireResult = (condition, reason) => {
  if (!condition) throw new Error(reason);
};

try {
  requireResult(endpoint && origin && revision && ["baseline", "candidate"].includes(mode),
    "explicit_service_revision_selection_required");
  const endpointUrl = new URL(endpoint);
  const originUrl = new URL(origin);
  requireResult(endpointUrl.protocol === "http:" && endpointUrl.hostname === "127.0.0.1"
    && originUrl.protocol === "http:" && originUrl.hostname === "127.0.0.1"
    && originUrl.pathname === "/" && !originUrl.search && !originUrl.hash
    && /^[0-9a-f]{40}$/u.test(revision),
  "service_revision_selection_invalid");

  const browser = await chromium.connectOverCDP(endpoint);
  const context = browser.contexts()[0];
  requireResult(context, "shared_owner_browser_required");
  page = await context.newPage();
  let mutations = 0;
  page.on("request", request => {
    const url = new URL(request.url());
    if (url.origin === origin && !["GET", "HEAD"].includes(request.method())) {
      mutations += 1;
    }
  });
  await page.goto(origin);
  requireResult(await page.evaluate(() => location.origin) === origin,
    "shared_authenticated_dashboard_required");
  const read = async path => page.evaluate(async selected => {
    const response = await fetch(selected, { credentials: "same-origin" });
    if (!response.ok) throw new Error("authenticated_versioned_read_required");
    return response.json();
  }, path);
  const registry = async () => publicRegistryDigestV1({
    accounts: await readAllRegistryItemsV1(read, "/api/v1/accounts"),
    organizations: await readAllRegistryItemsV1(read, "/api/v1/organizations"),
    installations: await readAllRegistryItemsV1(read, "/api/v1/provider-installations"),
  });

  stage = "registry_before";
  const registryBefore = await registry();
  stage = "service_revision";
  const [liveness, versions] = await Promise.all([
    read("/api/v1/operations/liveness"),
    read("/api/v1/operations/versions"),
  ]);
  requireResult(liveness?.state === "healthy", "service_liveness_invalid");
  if (mode === "candidate") {
    requireResult(isExactServiceRevisionV1(versions, revision),
      "service_source_revision_mismatch");
  }

  stage = "built_dashboard";
  await page.goto(origin);
  const overview = page.getByRole("button", { name: "Overview", exact: true });
  await overview.waitFor({ timeout: 15_000 });
  requireResult(await overview.count() === 1
    && await overview.getAttribute("aria-current") === "page"
    && await page.locator("main").count() === 1,
  "authenticated_built_overview_required");
  stage = "registry_after";
  const registryAfter = await registry();
  requireResult(registryAfter === registryBefore && mutations === 0,
    "service_revision_proof_mutated_registry");
  console.log(JSON.stringify({
    schema: "agentmonitor.m5-service-revision-proof.v1",
    mode,
    implementation_revision: revision,
    service_source_revision: mode === "candidate" ? versions.source_revision.value : null,
    registry_digest_before: registryBefore,
    registry_digest_after: registryAfter,
    mutations,
  }));
} catch (error) {
  const reason = error instanceof Error && /^[a-z0-9_]+$/u.test(error.message)
    ? error.message : "service_revision_browser_unavailable";
  console.error(`M5 SERVICE REVISION: BLOCKED — ${stage}: ${reason}`);
  exitCode = 3;
} finally {
  if (page) await page.close().catch(() => { exitCode = 3; });
}
process.exit(exitCode);
