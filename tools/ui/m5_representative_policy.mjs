/** Pure selection policy; live identity and lineage must be verified separately. */
export function selectServiceRevisionV1(ownerRevision, currentRevision) {
  const value = currentRevision ?? ownerRevision;
  return typeof value === "string" && /^[0-9a-f]{40}$/.test(value) ? value : null;
}

export function selectRepresentativeOutcomesV1(verified, accounts, ids) {
  if (!Array.isArray(verified) || !(accounts instanceof Map) || !Array.isArray(ids)
      || ids.length !== 2 || new Set(ids).size !== 2
      || ids.some(id => typeof id !== "string" || !/^[A-Za-z0-9_-]{1,128}$/.test(id))
      || !ids.some(id => verified.some(row => row.account_id === id && row.disposition === "verified"))) return null;
  const result = [];
  for (const id of ids) {
    const account = accounts.get(id);
    if (account?.provider_key !== "codex" || account.lifecycle !== "active"
        || account.is_effective_monitoring_enabled !== true
        || typeof account.friendly_name !== "string" || account.friendly_name.length === 0) return null;
    result.push({account_id: id, alias: account.friendly_name});
  }
  return result;
}
