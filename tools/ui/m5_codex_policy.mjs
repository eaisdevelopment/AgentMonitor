import { createHash } from "node:crypto";
import { posix as path } from "node:path";

const sha256 = value => createHash("sha256")
  .update(JSON.stringify(value))
  .digest("hex");
const canonicalJson = value => {
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(",")}]`;
  if (value !== null && typeof value === "object") {
    return `{${Object.keys(value).sort().map(key =>
      `${JSON.stringify(key)}:${canonicalJson(value[key])}`).join(",")}}`;
  }
  return JSON.stringify(value);
};
const digest = value => typeof value === "string" && /^[0-9a-f]{64}$/.test(value);
const opaque = value => typeof value === "string" && /^[A-Za-z0-9_-]{1,64}$/.test(value);
const timestamp = value => typeof value === "string" && Number.isFinite(Date.parse(value));
const utcTimestamp = value => typeof value === "string"
  && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?Z$/.test(value)
  && Number.isFinite(Date.parse(value));
const safeReason = value => typeof value === "string" && /^[a-z][a-z0-9_]{0,95}$/.test(value);
const availableRatio = field => {
  const quantity = field?.value;
  if (field?.availability !== "available" || quantity?.unit !== "ratio"
      || typeof quantity.coefficient !== "string"
      || !/^(?:0|[1-9][0-9]*)$/.test(quantity.coefficient)
      || !Number.isInteger(quantity.scale) || quantity.scale < 0 || quantity.scale > 18
      || quantity.scale > 0 && quantity.coefficient.endsWith("0")) return null;
  const coefficient = BigInt(quantity.coefficient);
  if (coefficient > 10n ** BigInt(quantity.scale)) return null;
  return `${quantity.coefficient}:${quantity.scale}:ratio`;
};
const exactKeys = (value, expected) => value && typeof value === "object"
  && !Array.isArray(value)
  && JSON.stringify(Object.keys(value).sort()) === JSON.stringify([...expected].sort());
const normalizedAlias = value => {
  if (typeof value !== "string" || value !== value.trim() || value.length === 0
      || value.length > 128 || /[\u0000-\u001f\u007f]/u.test(value)) {
    throw new Error("owner_outcomes_invalid");
  }
  return value.normalize("NFKC").toLocaleLowerCase("en-US");
};
const safeToken = value => typeof value === "string"
  && /^[A-Za-z0-9_.:-]{1,128}$/.test(value);
const resetPrecisions = new Set(["exact", "rounded", "range", "estimated", "unknown"]);
const canonicalDecimal = (value, { positive = false } = {}) =>
  typeof value === "string" && /^(?:0|[1-9][0-9]{0,23})$/.test(value)
  && (!positive || value !== "0");
const canonicalLinuxPath = value => {
  if (typeof value !== "string" || value.length < 1 || value.length > 4096
      || !value.startsWith("/") || /[\u0000-\u001f\u007f]/u.test(value)
      || path.normalize(value) !== value) return null;
  return value;
};

export function codexExecutableIdentityDigestV1(identity) {
  if (!exactKeys(identity, [
    "device", "inode", "fileType", "sizeBytes", "modifiedNs", "changedNs",
  ])
      || !canonicalDecimal(identity.device)
      || !canonicalDecimal(identity.inode, { positive: true })
      || identity.fileType !== "32768"
      || !canonicalDecimal(identity.sizeBytes, { positive: true })
      || !canonicalDecimal(identity.modifiedNs, { positive: true })
      || !canonicalDecimal(identity.changedNs, { positive: true })) {
    throw new Error("codex_executable_identity_invalid");
  }
  return createHash("sha256").update([
    "linux.proc.executable-identity.v1",
    identity.device,
    identity.inode,
    identity.fileType,
    identity.sizeBytes,
    identity.modifiedNs,
    identity.changedNs,
  ].join("\x1f"), "ascii").digest("hex");
}

export function parseLinuxProcStatV1(raw, expectedPid) {
  if (typeof raw !== "string" || Buffer.byteLength(raw, "utf8") > 16_384
      || raw.includes("\0") || !Number.isSafeInteger(expectedPid) || expectedPid < 1) {
    throw new Error("codex_proc_stat_invalid");
  }
  const value = raw.endsWith("\n") ? raw.slice(0, -1) : raw;
  const open = value.indexOf(" (");
  const close = value.lastIndexOf(") ");
  const pidText = open < 1 ? "" : value.slice(0, open);
  const fields = close <= open + 2 ? [] : value.slice(close + 2).split(" ");
  const integer = selected => /^(?:0|[1-9][0-9]*)$/.test(selected ?? "")
    ? Number(selected) : Number.NaN;
  const pid = integer(pidText);
  const parentPid = integer(fields[1]);
  const startTimeTicks = integer(fields[19]);
  if (!/^[A-Za-z]$/.test(fields[0] ?? "") || !Number.isSafeInteger(pid)
      || pid !== expectedPid || !Number.isSafeInteger(parentPid) || parentPid < 1
      || !Number.isSafeInteger(startTimeTicks) || startTimeTicks < 1) {
    throw new Error("codex_proc_stat_invalid");
  }
  return { pid, parentPid, startTimeTicks };
}

export function publicRegistryDigestV1(registry) {
  const definitions = [
    ["accounts", "account_id"],
    ["organizations", "organization_id"],
    ["installations", "provider_installation_id"],
  ];
  if (!exactKeys(registry, definitions.map(([name]) => name))) {
    throw new Error("public_registry_invalid");
  }
  const normalized = {};
  for (const [name, key] of definitions) {
    const records = registry[name];
    if (!Array.isArray(records) || records.some(record =>
      record === null || typeof record !== "object" || Array.isArray(record)
        || typeof record[key] !== "string" || record[key].length < 1)
        || new Set(records.map(record => record[key])).size !== records.length) {
      throw new Error("public_registry_invalid");
    }
    normalized[name] = [...records].sort((left, right) =>
      left[key].localeCompare(right[key]));
  }
  return createHash("sha256").update(canonicalJson(normalized)).digest("hex");
}

export function normalizeCodexQuotaWindowsV1(windows) {
  if (!Array.isArray(windows) || windows.length < 1) {
    throw new Error("codex_quota_window_invalid");
  }
  const keys = new Set();
  return windows.map(window => {
    const field = window?.allowance?.remaining_percentage ?? window?.remaining_ratio;
    const value = field?.value;
    if (field?.availability !== "available" || value === null
        || !["ratio", "percent"].includes(value?.unit)
        || typeof value?.coefficient !== "string"
        || !/^(?:0|[1-9][0-9]*)$/.test(value.coefficient)
        || !Number.isInteger(value.scale) || value.scale < 0 || value.scale > 18
        || !safeToken(window?.window_key) || !safeToken(window?.semantic_role)
        || !safeToken(window?.current_observation_id)
        || !resetPrecisions.has(window?.reset_precision)
        || (window?.reset_at === null) !== (window?.reset_precision === "unknown")
        || keys.has(window.window_key)) {
      throw new Error("codex_quota_window_invalid");
    }
    const numerator = BigInt(value.coefficient)
      * (value.unit === "ratio" ? 100n : 1n);
    const denominator = 10n ** BigInt(value.scale);
    if (numerator % denominator !== 0n) {
      throw new Error("codex_quota_window_invalid");
    }
    const remainingPercent = Number(numerator / denominator);
    const selectedResetEpoch = window.reset_at === null
      ? null : Math.floor(Date.parse(window.reset_at) / 1000);
    if (!Number.isSafeInteger(remainingPercent)
        || remainingPercent < 0 || remainingPercent > 100
        || !(selectedResetEpoch === null
          || Number.isSafeInteger(selectedResetEpoch) && selectedResetEpoch > 0)) {
      throw new Error("codex_quota_window_invalid");
    }
    keys.add(window.window_key);
    return {
      windowKey: window.window_key,
      semanticRole: window.semantic_role,
      remainingPercent,
      resetEpoch: selectedResetEpoch,
      resetPrecision: window.reset_precision,
      currentObservationId: window.current_observation_id,
    };
  });
}

export function canonicalCodexHistoryMaterialV1(rows) {
  if (!Array.isArray(rows) || rows.some(row => !Array.isArray(row)
      || row.length !== 7 || !safeToken(row[0]) || !safeToken(row[1])
      || !safeToken(row[2]) || !Number.isSafeInteger(row[3])
      || row[3] < 0 || row[3] > 100
      || !(row[4] === null || Number.isSafeInteger(row[4]) && row[4] > 0)
      || !resetPrecisions.has(row[5]) || !safeToken(row[6]))) {
    throw new Error("codex_history_material_invalid");
  }
  return rows.map(row => [...row]).sort((left, right) => {
    const leftKey = JSON.stringify(left);
    const rightKey = JSON.stringify(right);
    return leftKey < rightKey ? -1 : leftKey > rightKey ? 1 : 0;
  });
}

export const codexAdmissionV1 = Object.freeze({
  provider_version: "0.160.0",
  adapter_id: "agentmonitor.codex",
  adapter_version: "1.0.1",
  parser_version: "1.0.0",
  rate_limits_source_id: "codex.app-server.account-rate-limits-read.v2",
  identity_source_id: "codex.app-server.account-read.v2",
  mapping_id: "M5-CDX-0-160-0-002",
  mapping_digest: "2ac086063dbfdae1c673f7cd899ac60d6d559bc72dbb598c6e5196c43567a204",
  schema_bundle_digest: "36bd8e1d76b12b89b06446a85c45e957945eb8cb63b05061264c3dec97f625da",
});

export function validateOwnerOutcomesV1(document, now = null, expectedContext = null) {
  if (!exactKeys(document, [
    "schema", "implementation_revision", "service_pid",
    "service_start_time_ticks", "owner_confirmed_at", "owner_confirmation",
    "outcomes",
  ])
      || document.schema !== "agentmonitor.m5-owner-outcomes.v2"
      || !/^[0-9a-f]{40}$/.test(document.implementation_revision)
      || !Number.isSafeInteger(document.service_pid) || document.service_pid < 1
      || !Number.isSafeInteger(document.service_start_time_ticks)
      || document.service_start_time_ticks < 1
      || document.owner_confirmation !== true
      || !utcTimestamp(document.owner_confirmed_at)
      || !Array.isArray(document.outcomes) || document.outcomes.length !== 4) {
    throw new Error("owner_outcomes_invalid");
  }
  if (now !== null) {
    const current = now instanceof Date ? now.getTime() : Number.NaN;
    const confirmed = Date.parse(document.owner_confirmed_at);
    if (!Number.isFinite(current) || confirmed > current + 5 * 60 * 1000
        || current - confirmed > 8 * 24 * 60 * 60 * 1000) {
      throw new Error("owner_outcomes_invalid");
    }
  }
  if (expectedContext !== null
      && (!exactKeys(expectedContext, [
        "implementationRevision", "servicePid", "serviceStartTimeTicks",
      ])
        || expectedContext.implementationRevision !== document.implementation_revision
        || expectedContext.servicePid !== document.service_pid
        || expectedContext.serviceStartTimeTicks !== document.service_start_time_ticks)) {
    throw new Error("owner_outcomes_invalid");
  }
  const aliases = [];
  const accountIds = [];
  const rows = document.outcomes.map(row => {
    const verified = row?.disposition === "verified";
    const unavailable = row?.disposition === "owner_unavailable";
    const keys = verified
      ? ["account_id", "alias", "disposition"]
      : unavailable
        ? ["account_id", "alias", "disposition", "reason"]
        : [];
    if (!exactKeys(row, keys) || !opaque(row.account_id)) {
      throw new Error("owner_outcomes_invalid");
    }
    accountIds.push(row.account_id);
    aliases.push(normalizedAlias(row.alias));
    if (unavailable && !safeReason(row.reason)) {
      throw new Error("owner_outcomes_invalid");
    }
    return Object.freeze({ ...row });
  });
  if (new Set(accountIds).size !== 4 || new Set(aliases).size !== 4) {
    throw new Error("owner_outcomes_invalid");
  }
  return Object.freeze(rows);
}

export function liveIdentityDigestV1(identity) {
  const email = identity?.email;
  const organization = identity?.provider_organization;
  if (identity?.state !== "verified" || identity?.provider_key !== "codex"
      || typeof email !== "string" || email !== email.trim()
      || email.length < 3 || email.length > 320
      || /[\u0000-\u001f\u007f]/u.test(email)
      || !(organization === null || typeof organization === "string"
        && organization === organization.trim() && organization.length > 0
        && organization.length <= 256
        && !/[\u0000-\u001f\u007f]/u.test(organization))) {
    throw new Error("codex_live_identity_invalid");
  }
  return sha256([
    identity.provider_key,
    email.normalize("NFKC").toLocaleLowerCase("en-US"),
    organization === null ? null : organization.normalize("NFKC"),
  ]);
}

export function isExactServiceRevisionV1(inventory, expectedRevision) {
  const revision = inventory?.source_revision;
  return typeof expectedRevision === "string"
    && /^[0-9a-f]{40}$/.test(expectedRevision)
    && revision?.value === expectedRevision
    && revision?.availability === "available"
    && revision?.source === "build_manifest";
}

export function isExactCodexProvenanceV1(value) {
  return value?.source_id === codexAdmissionV1.rate_limits_source_id
    && value?.adapter_id === codexAdmissionV1.adapter_id
    && value?.adapter_version === codexAdmissionV1.adapter_version
    && value?.parser_version === codexAdmissionV1.parser_version
    && value?.provider_version === codexAdmissionV1.provider_version
    && value?.decision_reference === codexAdmissionV1.mapping_id
    && value?.is_experimental === true;
}

export function isExactRenderedCodexProvenanceV1(fields) {
  return fields?.Source === codexAdmissionV1.rate_limits_source_id
    && fields?.Adapter === `${codexAdmissionV1.adapter_id} · ${codexAdmissionV1.adapter_version}`
    && fields?.["Provider version"] === codexAdmissionV1.provider_version;
}

export function isFreshCodexLineageV1(candidate, serviceStartedAt) {
  const lowerBound = Date.parse(serviceStartedAt);
  const requestedAt = Date.parse(candidate?.run?.requested_at);
  const completedAt = Date.parse(candidate?.run?.completed_at);
  const observationIds = candidate?.run?.observation_ids;
  const windows = candidate?.windows;
  const historyItems = candidate?.history?.items;
  if (!Number.isFinite(lowerBound) || !Number.isFinite(requestedAt)
      || !Number.isFinite(completedAt) || requestedAt < lowerBound
      || completedAt < requestedAt || !Array.isArray(observationIds)
      || observationIds.length === 0 || !Array.isArray(windows)
      || windows.length === 0 || !Array.isArray(historyItems)
      || candidate?.history?.availability?.state !== "available"
      || candidate?.identity?.account_id !== candidate?.accountId
      || candidate?.identity?.collection_run_id !== candidate?.run?.run_id
      || candidate?.identity?.state !== "verified"
      || candidate?.identity?.provider_version !== codexAdmissionV1.provider_version
      || candidate?.identity?.provider_key !== "codex"
      || candidate?.identity?.identity_source_id !== codexAdmissionV1.identity_source_id
      || candidate?.identity?.profile_protection !== "managed"
      || candidate?.run?.account_id !== candidate?.accountId
      || candidate?.run?.provider_key !== "codex"
      || candidate?.run?.capability_id !== "subscription.quota"
      || candidate?.run?.source_id !== codexAdmissionV1.rate_limits_source_id
      || candidate?.run?.adapter_version !== codexAdmissionV1.adapter_version
      || candidate?.run?.provider_version !== codexAdmissionV1.provider_version) {
    return false;
  }
  const windowKeys = new Set(windows.map(window => window?.window_key));
  const currentIds = new Set(windows.map(window => window?.current_observation_id));
  if (windowKeys.size !== windows.length || currentIds.size !== windows.length
      || !windows.every(window => typeof window?.window_key === "string"
        && window.window_key.includes(":")
        && window?.subject?.account_id === candidate.accountId
        && window?.subject?.provider_key === "codex"
        && window.freshness === "fresh"
        && window.collection_run_id === candidate.run.run_id
        && typeof window.current_observation_id === "string"
        && observationIds.includes(window.current_observation_id)
        && availableRatio(window.remaining_ratio) !== null
        && isExactCodexProvenanceV1(window.provenance))) {
    return false;
  }
  const currentHistory = historyItems.filter(point =>
    point?.subject?.account_id === candidate.accountId
      && point?.subject?.provider_key === "codex"
      && point.collection_run_id === candidate.run.run_id
      && currentIds.has(point.observation_id));
  const complete = candidate.run.state === "succeeded"
    && candidate.run.outcome_code === "succeeded" && candidate.run.error_code === null
    && currentHistory.every(point => point.completeness === "complete");
  const partial = candidate.run.state === "partial"
    && candidate.run.outcome_code === "partial" && candidate.run.error_code === null
    && currentHistory.every(point => point.completeness === "partial");
  return (complete || partial) && currentHistory.length === windows.length
    && windows.every(window => currentHistory.filter(point =>
      point.observation_id === window.current_observation_id
        && point.window_key === window.window_key
        && availableRatio(point.value) === availableRatio(window.remaining_ratio)
        && isExactCodexProvenanceV1(point.provenance)).length === 1);
}

export function selectRepresentativeCodexProcessesV1(processes, options = null) {
  const ownerRoot = exactKeys(options, ["ownerRoot"])
    ? canonicalLinuxPath(options.ownerRoot) : null;
  if (!Array.isArray(processes) || ownerRoot === null || ownerRoot === "/") {
    throw new Error("representative_codex_processes_required");
  }
  const managedProfilesRoot = `${ownerRoot}/profiles/codex`;
  const eligible = processes.filter(item => item?.provider_key === "codex"
    && item.provider_version === codexAdmissionV1.provider_version
    && item.state === "running" && item.account_correlation === "unresolved"
    && Number.isInteger(item.pid) && item.pid > 0
    && Number.isInteger(item.start_time_ticks) && item.start_time_ticks > 0
    && Number.isInteger(item.parent_pid) && item.parent_pid > 0
    && digest(item.platform_scope_id) && digest(item.association_key)
    && timestamp(item.observed_at)
    && canonicalLinuxPath(item.working_directory) !== null
    && item.working_directory !== ownerRoot
    && item.working_directory !== managedProfilesRoot
    && !item.working_directory.startsWith(`${managedProfilesRoot}/`)
    && (item.account_association === null
      || item.account_association?.state === "owner_confirmed"
        && opaque(item.account_association?.account_id)
        && opaque(item.account_association?.principal_id)
        && Number.isInteger(item.account_association?.record_version)
        && item.account_association.record_version >= 1
        && timestamp(item.account_association?.confirmed_at)
        && Date.parse(item.account_association.confirmed_at) <= Date.parse(item.observed_at)));
  const identities = eligible.map(item =>
    `${item.platform_scope_id}:${item.pid}:${item.start_time_ticks}`);
  const pidKeys = eligible.map(item => `${item.platform_scope_id}:${item.pid}`);
  if (new Set(identities).size !== eligible.length
      || new Set(pidKeys).size !== eligible.length
      || new Set(eligible.map(item => item.association_key)).size !== eligible.length
      || eligible.some(item => item.parent_pid === item.pid)) {
    throw new Error("representative_codex_processes_required");
  }
  const byPid = new Map(eligible.map(item => [
    `${item.platform_scope_id}:${item.pid}`,
    item,
  ]));
  for (const item of eligible) {
    const parent = byPid.get(`${item.platform_scope_id}:${item.parent_pid}`);
    if (parent && parent.start_time_ticks > item.start_time_ticks) {
      throw new Error("representative_codex_processes_required");
    }
    const visited = new Set();
    let current = item;
    while (current) {
      const key = `${current.platform_scope_id}:${current.pid}`;
      if (visited.has(key)) {
        throw new Error("representative_codex_processes_required");
      }
      visited.add(key);
      current = byPid.get(`${current.platform_scope_id}:${current.parent_pid}`);
    }
  }
  const ordered = [...eligible].sort((left, right) =>
    left.platform_scope_id.localeCompare(right.platform_scope_id)
      || left.start_time_ticks - right.start_time_ticks || left.pid - right.pid);
  if (ordered.length < 5) throw new Error("representative_codex_processes_required");
  return ordered.slice(0, 6);
}

export function bindIndependentCodexExecutableProofsV1(
  processes,
  proofs,
  admittedExecutableIdentity,
  options = null,
) {
  if (!digest(admittedExecutableIdentity) || !Array.isArray(proofs)) {
    throw new Error("independent_codex_process_proof_required");
  }
  let selected;
  try {
    selected = selectRepresentativeCodexProcessesV1(processes, options);
  } catch {
    throw new Error("independent_codex_process_proof_required");
  }
  if (proofs.length !== selected.length) {
    throw new Error("independent_codex_process_proof_required");
  }
  const byIdentity = new Map();
  for (const proof of proofs) {
    if (!exactKeys(proof, [
      "pid", "parentPid", "startTimeTicks", "workingDirectoryBefore",
      "workingDirectoryAfter", "executableIdentityBefore", "executableIdentityAfter",
    ])
        || !Number.isSafeInteger(proof.pid) || proof.pid < 1
        || !Number.isSafeInteger(proof.parentPid) || proof.parentPid < 1
        || !Number.isSafeInteger(proof.startTimeTicks) || proof.startTimeTicks < 1
        || canonicalLinuxPath(proof.workingDirectoryBefore) === null
        || proof.workingDirectoryAfter !== proof.workingDirectoryBefore
        || proof.executableIdentityBefore !== admittedExecutableIdentity
        || proof.executableIdentityAfter !== admittedExecutableIdentity) {
      throw new Error("independent_codex_process_proof_required");
    }
    const key = `${proof.pid}:${proof.startTimeTicks}`;
    if (byIdentity.has(key)) {
      throw new Error("independent_codex_process_proof_required");
    }
    byIdentity.set(key, proof);
  }
  return Object.freeze(selected.map(item => {
    const proof = byIdentity.get(`${item.pid}:${item.start_time_ticks}`);
    if (!proof || proof.parentPid !== item.parent_pid
        || proof.workingDirectoryBefore !== item.working_directory) {
      throw new Error("independent_codex_process_proof_required");
    }
    return Object.freeze({
      ...item,
      independent_executable_identity: admittedExecutableIdentity,
    });
  }));
}

export function buildCodexWitnessV1(
  ownerDocument,
  records,
  processes,
  {
    event,
    registryDigest,
    serviceRevision,
    providerHealth = "healthy",
    mutations = 0,
    processScanTruncated = false,
    ownerRoot,
  },
) {
  const outcomes = validateOwnerOutcomesV1(ownerDocument);
  const verifiedOutcomes = outcomes.filter(row => row.disposition === "verified");
  if (!["m5_codex_preflight", "m5_codex_witness"].includes(event)
      || verifiedOutcomes.length < 1 || !digest(registryDigest)
      || typeof serviceRevision !== "string"
      || !/^[0-9a-f]{40}$/.test(serviceRevision)
      || providerHealth !== "healthy" || mutations !== 0
      || typeof processScanTruncated !== "boolean"
      || !Array.isArray(records) || records.length !== verifiedOutcomes.length) {
    throw new Error("codex_witness_invalid");
  }
  const verifiedIds = new Set(verifiedOutcomes.map(row => row.account_id));
  const normalized = records.map(record => {
    if (!record || !verifiedIds.has(record.accountId)
        || !safeToken(record.collectionRunId)
        || record.currentHistoryMatched !== true
        || ![true, false].includes(record.freshAfterRestart)
        || record.providerKey !== "codex" || record.lifecycle !== "active"
        || record.monitoringPreference !== "enabled"
        || record.effectiveMonitoringEnabled !== true
        || !["matched", "owner_confirmed"].includes(record.identityState)
        || !digest(record.liveIdentityDigest)
        || !Array.isArray(record.quotaWindows) || record.quotaWindows.length < 1
        || !Number.isInteger(record.accountRecordVersion) || record.accountRecordVersion < 1
        || !Number.isInteger(record.accountRegistryRevision) || record.accountRegistryRevision < 1) {
      throw new Error("codex_witness_invalid");
    }
    const windowKeys = new Set();
    const quotaWindows = record.quotaWindows.map(window => {
      if (!exactKeys(window, [
        "windowKey", "semanticRole", "remainingPercent", "resetEpoch", "resetPrecision",
        "currentObservationId",
      ]) || !safeToken(window.windowKey) || !safeToken(window.semanticRole)
          || !safeToken(window.currentObservationId)
          || !Number.isSafeInteger(window.remainingPercent)
          || window.remainingPercent < 0 || window.remainingPercent > 100
          || !(window.resetEpoch === null
            || Number.isSafeInteger(window.resetEpoch) && window.resetEpoch > 0)
          || !resetPrecisions.has(window.resetPrecision)
          || (window.resetEpoch === null) !== (window.resetPrecision === "unknown")
          || windowKeys.has(window.windowKey)) {
        throw new Error("codex_witness_invalid");
      }
      windowKeys.add(window.windowKey);
      return window;
    });
    return { ...record, quotaWindows };
  });
  if (new Set(normalized.map(record => record.accountId)).size !== verifiedOutcomes.length) {
    throw new Error("codex_witness_invalid");
  }
  if (new Set(normalized.map(record => record.liveIdentityDigest)).size
      !== verifiedOutcomes.length) {
    throw new Error("codex_witness_invalid");
  }
  const selected = selectRepresentativeCodexProcessesV1(processes, { ownerRoot });
  if (selected.some(item => !digest(item.independent_executable_identity))
      || new Set(selected.map(item => item.independent_executable_identity)).size !== 1) {
    throw new Error("codex_witness_invalid");
  }
  const freshCount = normalized.filter(record => record.freshAfterRestart).length;
  if (event === "m5_codex_preflight" && freshCount !== 0
      || event === "m5_codex_witness" && freshCount !== verifiedOutcomes.length) {
    throw new Error("fresh_codex_lineage_required");
  }
  const orderedRecords = [...normalized].sort((left, right) =>
    left.accountId.localeCompare(right.accountId));
  return {
    event,
    service_revision: serviceRevision,
    account_count: 4,
    verified_count: verifiedOutcomes.length,
    owner_unavailable_count: 4 - verifiedOutcomes.length,
    current_history_count: normalized.filter(record => record.currentHistoryMatched).length,
    fresh_after_restart_count: freshCount,
    process_count: selected.length,
    process_scan_truncated: processScanTruncated,
    mutations,
    provider_version: codexAdmissionV1.provider_version,
    adapter_version: codexAdmissionV1.adapter_version,
    parser_version: codexAdmissionV1.parser_version,
    schema_bundle_digest: codexAdmissionV1.schema_bundle_digest,
    mapping_id: codexAdmissionV1.mapping_id,
    mapping_digest: codexAdmissionV1.mapping_digest,
    provider_health: providerHealth,
    fleet_metadata_digest: sha256([
      ...outcomes.map(row => [row.account_id, row.disposition]).sort(),
      ...orderedRecords.map(record => [
        record.accountId,
        record.providerKey,
        record.lifecycle,
        record.monitoringPreference,
        record.effectiveMonitoringEnabled,
        record.identityState,
        record.accountRecordVersion,
        record.accountRegistryRevision,
      ]),
    ]),
    identity_set_digest: sha256(
      orderedRecords.map(record => record.liveIdentityDigest).sort(),
    ),
    collection_run_set_digest: sha256(
      orderedRecords.map(record => [record.accountId, record.collectionRunId]).sort(),
    ),
    quota_value_set_digest: sha256(
      orderedRecords.flatMap(record => record.quotaWindows.map(window => [
        record.accountId,
        window.windowKey,
        window.semanticRole,
        window.remainingPercent,
        window.resetEpoch,
        window.resetPrecision,
      ])).sort(),
    ),
    history_value_set_digest: sha256(canonicalCodexHistoryMaterialV1(
      orderedRecords.flatMap(record => record.quotaWindows.map(window => [
        record.accountId,
        window.windowKey,
        window.semanticRole,
        window.remainingPercent,
        window.resetEpoch,
        window.resetPrecision,
        window.currentObservationId,
      ])),
    )),
    process_set_digest: sha256(selected.map(item => [
      item.platform_scope_id,
      item.pid,
      item.start_time_ticks,
      item.parent_pid,
      item.provider_version,
      item.independent_executable_identity,
      item.working_directory,
      item.account_association?.account_id ?? null,
      item.account_association?.record_version ?? null,
    ])),
    registry_digest: registryDigest,
  };
}
