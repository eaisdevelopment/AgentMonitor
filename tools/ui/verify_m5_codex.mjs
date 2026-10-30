/** V1-M5: four private Codex outcomes through real API, process and built UI. */
import { spawn } from "node:child_process";
import { constants } from "node:fs";
import {
  access,
  chmod,
  lstat,
  mkdir,
  mkdtemp,
  open,
  readFile,
  readdir,
  readlink,
  realpath,
  rm,
} from "node:fs/promises";
import { tmpdir } from "node:os";
import { basename, delimiter, isAbsolute, join } from "node:path";
import { chromium } from "../../frontend/node_modules/@playwright/test/index.mjs";

import {
  bindIndependentCodexExecutableProofsV1,
  buildCodexWitnessV1,
  codexAdmissionV1,
  codexExecutableIdentityDigestV1,
  isExactRenderedCodexProvenanceV1,
  isExactServiceRevisionV1,
  isFreshCodexLineageV1,
  liveIdentityDigestV1,
  normalizeCodexQuotaWindowsV1,
  parseLinuxProcStatV1,
  publicRegistryDigestV1,
  selectRepresentativeCodexProcessesV1,
  validateOwnerOutcomesV1,
} from "./m5_codex_policy.mjs";
import {
  readAllCapacityHistoryV1,
  readAllRegistryItemsV1,
} from "./m5_registry_pages.mjs";
import { selectServiceRevisionV1 } from "./m5_representative_policy.mjs";

const endpoint = process.env.AGENTMONITOR_TEST_DASHBOARD_CDP_ENDPOINT;
const origin = process.env.AGENTMONITOR_TEST_DASHBOARD_ORIGIN;
const outcomesPath = process.env.AGENTMONITOR_TEST_M5_OWNER_OUTCOMES;
const ownerRoot = process.env.AGENTMONITOR_TEST_OWNER_DATA_ROOT;
const ownerRevision = process.env.AGENTMONITOR_M5_OWNER_IMPLEMENTATION_REVISION;
const serviceRevision = selectServiceRevisionV1(ownerRevision, process.env.AGENTMONITOR_M5_SERVICE_IMPLEMENTATION_REVISION);
const ownerServicePid = Number(process.env.AGENTMONITOR_M5_OWNER_SERVICE_PID);
const ownerServiceStartTicks = Number(
  process.env.AGENTMONITOR_M5_OWNER_SERVICE_START_TIME_TICKS,
);
const preflightOnly = process.env.AGENTMONITOR_M5_PREFLIGHT_ONLY === "1";
const serviceStartedAt = process.env.AGENTMONITOR_M5_SERVICE_STARTED_AT;
let stage = "prerequisites";
let page;
let codexExecutableHandle;
let exitCode = 0;

class VerificationError extends Error {
  constructor(code, blocked = false) {
    super(code);
    this.blocked = blocked;
  }
}
const requireResult = (condition, reason) => {
  if (!condition) throw new VerificationError(reason);
};
const requireLive = (condition, reason) => {
  if (!condition) throw new VerificationError(reason, true);
};
const executableMetadata = info => ({
  device: String(info.dev),
  inode: String(info.ino),
  fileType: String(info.mode & 0o170000n),
  sizeBytes: String(info.size),
  modifiedNs: String(info.mtimeNs),
  changedNs: String(info.ctimeNs),
});
const fullExecutableMetadata = info => ({
  ...executableMetadata(info),
  uid: String(info.uid),
  gid: String(info.gid),
  mode: String(info.mode),
});
const sameExecutableMetadata = (left, right) =>
  JSON.stringify(fullExecutableMetadata(left))
    === JSON.stringify(fullExecutableMetadata(right));
const safeAdmittedExecutable = info => info.isFile()
  && (info.uid === 0n || info.uid === BigInt(process.getuid()))
  && (info.mode & 0o022n) === 0n
  && (info.mode & 0o111n) !== 0n
  && info.size > 0n;
const resolveCodexLauncher = async () => {
  const searchPath = process.env.PATH;
  requireLive(typeof searchPath === "string"
    && Buffer.byteLength(searchPath, "utf8") <= 16_384,
  "admitted_codex_executable_unavailable");
  for (const entry of searchPath.split(delimiter)) {
    if (!isAbsolute(entry) || entry.length > 4096
        || /[\u0000-\u001f\u007f]/u.test(entry)) continue;
    const candidate = join(entry, "codex");
    try {
      await access(candidate, constants.X_OK);
      const resolved = await realpath(candidate);
      if (basename(resolved) === "codex") return { candidate, resolved };
    } catch {
      // Match command lookup without disclosing rejected private paths.
    }
  }
  throw new VerificationError("admitted_codex_executable_unavailable", true);
};
const isolatedCodexVersion = async (handle, root) => {
  const names = ["home", "codex-home", "cache", "config", "data", "state"];
  await Promise.all(names.map(name => mkdir(join(root, name), { mode: 0o700 })));
  const child = spawn("/proc/self/fd/3", ["--version"], {
    cwd: root,
    detached: false,
    env: {
      CODEX_HOME: join(root, "codex-home"),
      HOME: join(root, "home"),
      LANG: "C.UTF-8",
      LC_ALL: "C.UTF-8",
      NO_COLOR: "1",
      PATH: "/usr/bin:/bin",
      XDG_CACHE_HOME: join(root, "cache"),
      XDG_CONFIG_HOME: join(root, "config"),
      XDG_DATA_HOME: join(root, "data"),
      XDG_STATE_HOME: join(root, "state"),
    },
    shell: false,
    stdio: ["ignore", "pipe", "ignore", handle.fd],
  });
  let output = Buffer.alloc(0);
  let outputExceeded = false;
  child.stdout.on("data", chunk => {
    if (outputExceeded) return;
    if (output.length + chunk.length > 128) {
      outputExceeded = true;
      child.kill("SIGKILL");
      return;
    }
    output = Buffer.concat([output, chunk]);
  });
  let timedOut = false;
  const timeout = setTimeout(() => {
    timedOut = true;
    child.kill("SIGKILL");
  }, 3_000);
  const result = await new Promise(resolve => {
    child.once("error", () => resolve({ code: null, signal: "spawn_error" }));
    child.once("close", (code, signal) => resolve({ code, signal }));
  });
  clearTimeout(timeout);
  requireLive(!timedOut && !outputExceeded && result.code === 0
    && result.signal === null
    && /^codex-cli 0\.160\.0\r?\n?$/.test(output.toString("ascii")),
  "admitted_codex_executable_unavailable");
  const entries = await Promise.all(names.map(name => readdir(join(root, name))));
  requireLive(entries.every(items => items.length === 0),
    "admitted_codex_executable_side_effect");
};
const admitCodexExecutable = async () => {
  let handle;
  let root;
  try {
    const launcher = await resolveCodexLauncher();
    const pathInfo = await lstat(launcher.resolved, { bigint: true });
    await access(launcher.resolved, constants.X_OK);
    requireLive(safeAdmittedExecutable(pathInfo),
      "admitted_codex_executable_unavailable");
    handle = await open(launcher.resolved, "r");
    const descriptorInfo = await handle.stat({ bigint: true });
    requireLive(sameExecutableMetadata(pathInfo, descriptorInfo),
      "admitted_codex_executable_changed");
    const identity = codexExecutableIdentityDigestV1(
      executableMetadata(descriptorInfo),
    );
    root = await mkdtemp(join(tmpdir(), "agentmonitor-m5-codex-version-"));
    await chmod(root, 0o700);
    await isolatedCodexVersion(handle, root);
    const finalInfo = await handle.stat({ bigint: true });
    const finalTarget = await realpath(launcher.candidate);
    const finalHandle = await open(finalTarget, "r");
    try {
      const finalTargetInfo = await finalHandle.stat({ bigint: true });
      requireLive(sameExecutableMetadata(descriptorInfo, finalInfo)
        && sameExecutableMetadata(descriptorInfo, finalTargetInfo)
        && codexExecutableIdentityDigestV1(executableMetadata(finalInfo)) === identity,
      "admitted_codex_executable_changed");
    } finally {
      await finalHandle.close();
    }
    return { handle, identity, launcher: launcher.candidate };
  } catch (error) {
    if (handle) await handle.close().catch(() => {});
    if (error instanceof VerificationError) throw error;
    throw new VerificationError("admitted_codex_executable_unavailable", true);
  } finally {
    if (root) await rm(root, { recursive: true, force: true }).catch(() => {});
  }
};
const revalidateCodexExecutable = async admitted => {
  let currentHandle;
  try {
    const held = await admitted.handle.stat({ bigint: true });
    const currentTarget = await realpath(admitted.launcher);
    currentHandle = await open(currentTarget, "r");
    const current = await currentHandle.stat({ bigint: true });
    requireLive(safeAdmittedExecutable(held) && sameExecutableMetadata(held, current)
      && codexExecutableIdentityDigestV1(executableMetadata(held)) === admitted.identity,
    "admitted_codex_executable_changed");
  } catch (error) {
    if (error instanceof VerificationError) throw error;
    throw new VerificationError("admitted_codex_executable_changed", true);
  } finally {
    if (currentHandle) await currentHandle.close().catch(() => {});
  }
};
const readProcStat = async process => {
  let handle;
  try {
    handle = await open(`/proc/${process.pid}/stat`, "r");
    const buffer = Buffer.alloc(16_385);
    const { bytesRead } = await handle.read(buffer, 0, buffer.length, 0);
    requireLive(bytesRead > 0 && bytesRead <= 16_384,
      "representative_codex_process_changed");
    return parseLinuxProcStatV1(buffer.subarray(0, bytesRead).toString("utf8"), process.pid);
  } catch (error) {
    if (error instanceof VerificationError) throw error;
    throw new VerificationError("representative_codex_process_changed", true);
  } finally {
    if (handle) await handle.close();
  }
};
const readIndependentProcessProof = async selectedProcess => {
  const root = `/proc/${selectedProcess.pid}`;
  let firstExecutable;
  let secondExecutable;
  try {
    const before = await readProcStat(selectedProcess);
    const ownerBefore = await lstat(root, { bigint: true });
    const workingDirectoryBefore = await readlink(`${root}/cwd`);
    firstExecutable = await open(`${root}/exe`, "r");
    const firstInfo = await firstExecutable.stat({ bigint: true });
    const middle = await readProcStat(selectedProcess);
    secondExecutable = await open(`${root}/exe`, "r");
    const secondInfo = await secondExecutable.stat({ bigint: true });
    const workingDirectoryAfter = await readlink(`${root}/cwd`);
    const after = await readProcStat(selectedProcess);
    const ownerAfter = await lstat(root, { bigint: true });
    requireLive(ownerBefore.uid === BigInt(process.getuid())
      && ownerAfter.uid === ownerBefore.uid
      && before.pid === middle.pid && middle.pid === after.pid
      && before.parentPid === middle.parentPid
      && middle.parentPid === after.parentPid
      && before.startTimeTicks === middle.startTimeTicks
      && middle.startTimeTicks === after.startTimeTicks,
    "representative_codex_process_changed");
    return {
      pid: after.pid,
      parentPid: after.parentPid,
      startTimeTicks: after.startTimeTicks,
      workingDirectoryBefore,
      workingDirectoryAfter,
      executableIdentityBefore: codexExecutableIdentityDigestV1(
        executableMetadata(firstInfo),
      ),
      executableIdentityAfter: codexExecutableIdentityDigestV1(
        executableMetadata(secondInfo),
      ),
    };
  } catch (error) {
    if (error instanceof VerificationError) throw error;
    throw new VerificationError("representative_codex_process_changed", true);
  } finally {
    if (firstExecutable) await firstExecutable.close().catch(() => {});
    if (secondExecutable) await secondExecutable.close().catch(() => {});
  }
};

try {
  requireLive(endpoint && origin && outcomesPath && ownerRoot && ownerRevision && serviceRevision,
    "explicit_m5_owner_selection_required");
  requireLive(preflightOnly || typeof serviceStartedAt === "string"
    && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/.test(serviceStartedAt),
  "service_restart_time_required");
  requireLive(new URL(endpoint).hostname === "127.0.0.1"
    && new URL(origin).hostname === "127.0.0.1"
    && new URL(origin).protocol === "http:", "loopback_dashboard_required");
  requireLive(outcomesPath === `${ownerRoot}/m5-owner-outcomes.json`,
    "fixed_owner_outcomes_path_required");
  let ownerDocument;
  let outcomes;
  try {
    const metadata = await lstat(outcomesPath);
    requireLive(metadata.isFile() && !metadata.isSymbolicLink()
      && metadata.uid === process.getuid() && (metadata.mode & 0o077) === 0
      && metadata.nlink === 1 && metadata.size >= 2 && metadata.size <= 16_384,
    "private_owner_outcomes_file_required");
    ownerDocument = JSON.parse(await readFile(outcomesPath, "utf8"));
    outcomes = validateOwnerOutcomesV1(ownerDocument, new Date(), {
      implementationRevision: ownerRevision,
      servicePid: ownerServicePid,
      serviceStartTimeTicks: ownerServiceStartTicks,
    });
  } catch {
    throw new VerificationError("owner_outcomes_changed", true);
  }
  const verifiedOutcomes = outcomes.filter(row => row.disposition === "verified");
  requireLive(verifiedOutcomes.length > 0, "verified_codex_account_required");

  const browser = await chromium.connectOverCDP(endpoint);
  const context = browser.contexts()[0];
  requireLive(context, "shared_owner_browser_required");
  page = await context.newPage();
  let mutations = 0;
  page.on("request", request => {
    const url = new URL(request.url());
    if (url.origin === origin && url.pathname.startsWith("/api/v1/")
        && !["GET", "HEAD"].includes(request.method())) mutations += 1;
  });
  await page.goto(origin);
  requireLive(await page.evaluate(() => location.origin) === origin,
    "shared_authenticated_dashboard_required");
  const read = async path => page.evaluate(async selected => {
    const response = await fetch(selected, { credentials: "same-origin" });
    if (!response.ok) throw new Error("authenticated_versioned_read_required");
    return response.json();
  }, path);
  const readAll = path => readAllRegistryItemsV1(read, path);

  stage = "exact_codex_admission";
  const [capabilities, initialAccountItems, initialOrganizationItems,
    initialInstallationItems,
    health, versions] = await Promise.all([
    read("/api/v1/providers/codex/capabilities"),
    readAll("/api/v1/accounts"),
    readAll("/api/v1/organizations"),
    readAll("/api/v1/provider-installations"),
    read("/api/v1/operations/health"),
    read("/api/v1/operations/versions"),
  ]);
  requireResult(isExactServiceRevisionV1(versions, serviceRevision),
    "running_service_revision_mismatch");
  requireResult(capabilities.provider_key === "codex"
    && capabilities.adapter_id === codexAdmissionV1.adapter_id
    && capabilities.adapter_version === codexAdmissionV1.adapter_version
    && capabilities.m0_mapping_id === codexAdmissionV1.mapping_id
    && capabilities.items.some(item => item.capability_id === "subscription.quota"
      && item.support_state === "experimental"
      && item.stability === "experimental"
      && item.sources.length === 1
      && item.sources[0].source_id === codexAdmissionV1.rate_limits_source_id
      && item.sources[0].is_experimental === true),
  "exact_codex_capability_missing");
  const codexInstallations = initialInstallationItems.filter(item =>
    item.provider_key === "codex");
  requireLive(codexInstallations.length === 1
    && codexInstallations[0].presence_state === "present"
    && codexInstallations[0].version?.masked_value === codexAdmissionV1.provider_version,
  "exact_codex_installation_missing");
  const codexHealth = health.components?.find(item =>
    item.component_key === "provider.codex");
  requireLive(codexHealth?.outcome === "available"
    && codexHealth.sample?.state === "healthy", "codex_provider_health_unavailable");

  const registryDigest = publicRegistryDigestV1({
    accounts: initialAccountItems,
    organizations: initialOrganizationItems,
    installations: initialInstallationItems,
  });
  const accountById = new Map(initialAccountItems.map(item =>
    [item.account_id, item]));
  const selectedAccounts = outcomes.map(outcome => {
    const account = accountById.get(outcome.account_id);
    requireLive(account?.provider_key === "codex" && account.lifecycle !== "archived",
      "codex_owner_outcome_registry_mismatch");
    if (outcome.disposition === "verified") {
      requireLive(account.lifecycle === "active"
        && account.is_effective_monitoring_enabled
        && ["matched", "owner_confirmed"].includes(account.identity_state),
      "verified_codex_account_not_monitoring");
    }
    return { outcome, account };
  });

  stage = "owner_unavailable_outcomes";
  for (const { outcome, account } of selectedAccounts
    .filter(item => item.outcome.disposition === "owner_unavailable")) {
    const identity = await read(`/api/v1/accounts/${encodeURIComponent(
      outcome.account_id,
    )}/provider-identity`);
    requireLive(!(account.lifecycle === "active"
      && account.is_effective_monitoring_enabled
      && ["matched", "owner_confirmed"].includes(account.identity_state)
      && identity.state === "verified"
      && identity.provider_key === "codex"
      && identity.provider_version === codexAdmissionV1.provider_version
      && identity.identity_source_id === codexAdmissionV1.identity_source_id
      && identity.profile_protection === "managed"),
    "owner_unavailable_account_is_current");
  }

  const inspectVerified = async ({ outcome, account }) => {
    const now = new Date();
    const from = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
    const id = encodeURIComponent(outcome.account_id);
    const [identity, capacity, history, runs] = await Promise.all([
      read(`/api/v1/accounts/${id}/provider-identity`),
      read(`/api/v1/accounts/${id}/capacity`),
      readAllCapacityHistoryV1(read, `/api/v1/capacity/history?${new URLSearchParams({
        subject_id: outcome.account_id,
        metric: "remaining_ratio",
        series_kind: "poll_snapshot",
        from: from.toISOString(),
        before: now.toISOString(),
      })}`),
      read(`/api/v1/collection-runs?${new URLSearchParams({
        provider_key: "codex", account_id: outcome.account_id, limit: "200",
      })}`),
    ]);
    const windows = capacity.items.flatMap(item => item.windows);
    let quotaWindows;
    try {
      quotaWindows = normalizeCodexQuotaWindowsV1(windows);
    } catch {
      throw new VerificationError("codex_quota_window_contract_invalid");
    }
    const run = runs.items.find(item => item.run_id === identity.collection_run_id);
    const currentLineage = capacity.availability.state === "available"
      && isFreshCodexLineageV1({
        accountId: outcome.account_id, identity, run, windows, history,
      }, "1970-01-01T00:00:00Z");
    const freshAfterRestart = !preflightOnly && currentLineage
      && isFreshCodexLineageV1({
        accountId: outcome.account_id, identity, run, windows, history,
      }, serviceStartedAt);
    return {
      outcome, account, identity, windows, quotaWindows, run, history,
      currentLineage, freshAfterRestart,
    };
  };

  stage = "genuine_codex_quota_lineage";
  let inspected;
  const deadline = Date.now() + (preflightOnly ? 360_000 : 420_000);
  while (true) {
    inspected = await Promise.all(selectedAccounts
      .filter(item => item.outcome.disposition === "verified")
      .map(inspectVerified));
    const ready = inspected.every(item => item.currentLineage
      && (preflightOnly || item.freshAfterRestart));
    if (ready) break;
    requireLive(Date.now() < deadline, preflightOnly
      ? "current_codex_quota_lineage_required"
      : "fresh_post_restart_codex_lineage_required");
    await new Promise(resolve => setTimeout(resolve, 10_000));
  }

  stage = "representative_codex_processes";
  const admittedCodexExecutable = await admitCodexExecutable();
  codexExecutableHandle = admittedCodexExecutable.handle;
  const currentLocations = await read("/api/v1/process-locations");
  requireLive(currentLocations.availability?.state === "available"
    && currentLocations.source_id === "linux.proc.cwd.v1",
  "live_codex_process_read_required");
  const selectedAccountIds = new Set(outcomes.map(row => row.account_id));
  const codexProcesses = currentLocations.availability?.state === "available"
    && Array.isArray(currentLocations.items)
    ? currentLocations.items.filter(item => item.provider_key === "codex"
      && (item.account_association === null
        || selectedAccountIds.has(item.account_association?.account_id)))
    : [];
  let representativeCandidates;
  try {
    representativeCandidates = selectRepresentativeCodexProcessesV1(
      codexProcesses,
      { ownerRoot },
    );
  } catch (error) {
    if (error instanceof Error
        && error.message === "representative_codex_processes_required") {
      throw new VerificationError(error.message, true);
    }
    throw error;
  }
  const independentProofs = [];
  for (const process of representativeCandidates) {
    independentProofs.push(await readIndependentProcessProof(process));
  }
  let representativeProcesses;
  try {
    representativeProcesses = bindIndependentCodexExecutableProofsV1(
      codexProcesses,
      independentProofs,
      admittedCodexExecutable.identity,
      { ownerRoot },
    );
  } catch (error) {
    if (error instanceof Error
        && error.message === "independent_codex_process_proof_required") {
      throw new VerificationError(error.message, true);
    }
    throw error;
  }
  await revalidateCodexExecutable(admittedCodexExecutable);
  const records = inspected.map(item => ({
    accountId: item.account.account_id,
    collectionRunId: item.identity.collection_run_id,
    currentHistoryMatched: item.currentLineage,
    freshAfterRestart: item.freshAfterRestart,
    providerKey: item.account.provider_key,
    lifecycle: item.account.lifecycle,
    monitoringPreference: item.account.monitoring_preference,
    effectiveMonitoringEnabled: item.account.is_effective_monitoring_enabled,
    identityState: item.account.identity_state,
    accountRecordVersion: item.account.record_version,
    accountRegistryRevision: item.account.registry_revision,
    liveIdentityDigest: liveIdentityDigestV1(item.identity),
    quotaWindows: item.quotaWindows,
  }));
  const event = preflightOnly ? "m5_codex_preflight" : "m5_codex_witness";
  let witness = buildCodexWitnessV1(ownerDocument, records, representativeProcesses, {
    event,
    registryDigest,
    serviceRevision,
    providerHealth: "healthy",
    mutations,
    processScanTruncated: currentLocations.truncated === true,
    ownerRoot,
  });

  if (!preflightOnly) {
    stage = "built_codex_overview";
    await page.goto(origin);
    const overview = page.getByRole("table", {
      name: "Account quota overview", exact: true,
    });
    await overview.waitFor({ timeout: 15_000 });
    for (const { account } of selectedAccounts) {
      const row = overview.locator(`tbody tr[data-account-id="${account.account_id}"]`);
      const review = overview.getByRole("button", {
        name: `Review ${account.friendly_name} connection`, exact: true,
      });
      requireResult(await row.count() === 1 || await review.count() === 1,
        "codex_account_hidden_from_overview");
    }

    stage = "built_codex_account_details";
    for (const item of inspected) {
      await page.goto(`${origin}/accounts/${encodeURIComponent(item.account.account_id)}`);
      const activity = page.getByRole("table", { name: "Account activity", exact: true });
      await activity.waitFor({ timeout: 15_000 });
      requireResult((await activity.locator('[data-label="State"]').textContent())
        .includes("Monitoring on"), "codex_monitoring_state_missing");
      try {
        await activity.locator(".workspace-reading").first().waitFor({ timeout: 15_000 });
      } catch {
        throw new VerificationError("codex_quota_missing");
      }
      const renderedWindows = activity.locator(".workspace-reading");
      requireResult(await renderedWindows.count() > 0
        && await renderedWindows.count() <= item.quotaWindows.length,
      "codex_quota_window_count_mismatch");
      for (const row of await renderedWindows.all()) {
        let exactMatch = false;
        for (const window of item.quotaWindows) {
          if (await row.getAttribute("data-window-key") === window.windowKey
              && await row.getAttribute("data-semantic-role") === window.semanticRole
              && (await row.locator("strong").textContent())?.trim() === `${window.remainingPercent}%`) {
            const reset = row.locator(".quota-reset");
            const time = reset.locator("time");
            const timestamp = await time.count() === 0 ? null
              : Math.floor(Date.parse(await time.getAttribute("datetime")) / 1000);
            exactMatch = timestamp === window.resetEpoch
              && await reset.getAttribute("data-reset-precision") === window.resetPrecision;
          }
        }
        requireResult(exactMatch, "codex_quota_value_not_rendered");
      }
      await page.locator("details.quota-technical > summary").click();
      const provenanceRows = page.locator("details.quota-technical .quota-provenance");
      await provenanceRows.first().waitFor({ timeout: 15_000 });
      requireResult(await provenanceRows.count() === item.windows.length,
        "codex_quota_provenance_rows_missing");
      for (let index = 0; index < item.windows.length; index += 1) {
        const fields = await provenanceRows.nth(index).locator("div")
          .evaluateAll(rows => Object.fromEntries(rows.map(row => [
            row.querySelector("dt")?.textContent?.trim() ?? "",
            row.querySelector("dd")?.textContent?.trim() ?? "",
          ])));
        requireResult(isExactRenderedCodexProvenanceV1(fields),
          "codex_quota_provenance_not_rendered");
      }
    }

    stage = "built_codex_process_details";
    const displayedProcesses = new Set();
    const representativeByKey = new Map(representativeProcesses.map(item =>
      [item.association_key, item]));
    for (const { account } of selectedAccounts) {
      const processResponse = page.waitForResponse(response =>
        new URL(response.url()).pathname === "/api/v1/process-locations"
          && response.request().method() === "GET", { timeout: 15_000 });
      await page.goto(`${origin}/accounts/${encodeURIComponent(account.account_id)}`);
      requireResult((await processResponse).status() === 200,
        "codex_process_api_not_rendered");
      await page.getByRole("heading", { name: "Agents using this account", exact: true })
        .waitFor({ timeout: 15_000 });
      await page.locator("section.live-processes [role=status]")
        .filter({ hasText: "Reading running" }).waitFor({ state: "hidden", timeout: 15_000 });
      const unlinked = page.locator("details[data-unlinked-agents]");
      if (await unlinked.count() > 0) await unlinked.locator(":scope > summary").click();
      for (const row of await page.locator("tr[data-association-key]").all()) {
        const key = await row.getAttribute("data-association-key");
        const process = representativeByKey.get(key);
        if (!process) continue;
        const stateCell = row.locator('[data-label="State"]');
        const runningState = stateCell.locator(".activity-running");
        requireResult(await runningState.count() === 1
          && (await runningState.textContent()).replace(/^[●\s]+/u, "") === "Running"
          && await stateCell.getByText("Activity unknown", {
            exact: true,
          }).count() === 1, "codex_process_state_not_rendered");
        const associationText = process.account_association === null
          ? "Account unknown" : "Owner confirmed";
        requireResult(await row.locator('[data-label="Agent"]').getByText(
          associationText, { exact: true },
        ).count() === 1, "codex_process_association_not_rendered");
        requireResult(await row.locator('[data-label="Path"] code').count() === 1,
          "codex_process_location_not_rendered");
        await row.locator("details.agent-details > summary").click();
        const fields = await row.locator("details.agent-details dl > div")
          .evaluateAll(items => Object.fromEntries(items.map(item => [
            item.querySelector("dt")?.textContent?.trim() ?? "",
            item.querySelector("dd")?.textContent?.trim() ?? "",
          ])));
        requireResult(fields.PID === String(process.pid)
          && fields["Parent PID"] === String(process.parent_pid)
          && fields["Start identity"] === `${process.start_time_ticks} ticks`
          && fields["Codex version"] === process.provider_version,
        "codex_process_details_not_exact");
        displayedProcesses.add(key);
      }
    }
    requireResult(representativeProcesses.every(item =>
      displayedProcesses.has(item.association_key)),
    "representative_codex_processes_not_rendered");

    stage = "built_codex_history";
    await page.goto(`${origin}/collectors`);
    await page.getByRole("heading", { name: "Collection runs", exact: true })
      .waitFor({ timeout: 15_000 });
    await page.locator("[data-collection-run=true]")
      .filter({ hasText: "codex · subscription.quota" }).first().waitFor({ timeout: 15_000 });
    requireResult(await page.locator("[data-collection-run=true]")
      .filter({ hasText: "codex · subscription.quota" }).count() > 0,
    "codex_collection_history_not_rendered");

    stage = "built_codex_provider_capabilities";
    await page.goto(`${origin}/providers`);
    await page.getByRole("heading", { name: "Providers", exact: true })
      .waitFor({ timeout: 15_000 });
    const codexCard = page.locator(".provider-card").filter({ hasText: "codex" });
    await codexCard.waitFor({ timeout: 15_000 });
    requireResult(await codexCard.count() === 1
      && await codexCard.getByText(codexAdmissionV1.provider_version, {
        exact: false,
      }).count() > 0
      && await codexCard.getByText("subscription.quota", { exact: true }).count() === 1,
    "codex_provider_capability_not_rendered");

  }
  stage = "post_browser_registry";
  const [finalAccounts, finalOrganizations, finalInstallations] = await Promise.all([
    readAll("/api/v1/accounts"),
    readAll("/api/v1/organizations"),
    readAll("/api/v1/provider-installations"),
  ]);
  const finalRegistryDigest = publicRegistryDigestV1({
    accounts: finalAccounts,
    organizations: finalOrganizations,
    installations: finalInstallations,
  });
  requireResult(finalRegistryDigest === registryDigest,
    "read_only_codex_verification_mutated_registry");
  requireResult(mutations === 0, "codex_browser_started_mutation");
  witness = { ...witness, mutations };
  console.log(JSON.stringify(witness));
  console.log(`M5 CODEX: PASSED — four explicit owner outcomes, ${witness.verified_count} current${preflightOnly ? "" : " post-restart"} quota lineages, ${witness.process_count} representative processes${preflightOnly ? "" : ", built provider-neutral UI"}`);
} catch (error) {
  const reason = error instanceof VerificationError
    && /^[a-z0-9_]+$/.test(error.message)
    ? error.message : "codex_verification_unavailable";
  const blocked = error instanceof VerificationError && error.blocked;
  console.error(`M5 CODEX: ${blocked ? "BLOCKED" : "FAILED"} — ${stage}: ${reason}`);
  exitCode = blocked ? 3 : 1;
} finally {
  if (codexExecutableHandle) await codexExecutableHandle.close().catch(() => {});
  if (page) await page.close();
}
process.exit(exitCode);
