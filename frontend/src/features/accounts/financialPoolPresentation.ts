import type { FinancialPoolViewV1, OrganizationViewV1 } from "../../shared/api/client";

export type PoolSelector = "billing" | "self" | "team";
export type PoolContext = Readonly<{ accountId: string; resourceId: string; selector: PoolSelector }>;
type IntentBase = PoolContext & Readonly<{ revision: number; idempotencyKey: string; organizationId: string | null }>;
export type PoolIntent = IntentBase & (
  Readonly<{ kind: "assign"; action: "create" | "join" | "unlink"; poolId: string | null }>
  | Readonly<{ kind: "edit"; poolId: string; recordVersion: number }>
);

const identifier = (value: unknown): value is string => typeof value === "string" && /^[A-Za-z0-9_-]{1,64}$/.test(value);
const positive = (value: unknown): value is number => typeof value === "number" && Number.isSafeInteger(value) && value > 0;

/** Restore only a nonsecret, exact request; never replay it automatically. */
export function restorePoolIntent(raw: string | null, context: PoolContext): PoolIntent | null {
  if (raw === null || raw.length > 2048) return null;
  try {
    const value: unknown = JSON.parse(raw);
    if (typeof value !== "object" || value === null || Array.isArray(value)) return null;
    const item = value as Record<string, unknown>;
    const keys = ["accountId", "resourceId", "selector", "revision", "idempotencyKey", "organizationId", "kind", "poolId", item.kind === "edit" ? "recordVersion" : "action"];
    if (Object.keys(item).length !== keys.length || Object.keys(item).some((key) => !keys.includes(key)) ||
        item.accountId !== context.accountId || item.resourceId !== context.resourceId || item.selector !== context.selector ||
        !identifier(item.accountId) || !identifier(item.resourceId) || !positive(item.revision) || !identifier(item.idempotencyKey) ||
        (item.organizationId !== null && !identifier(item.organizationId))) return null;
    if (item.kind === "assign") {
      if (!["create", "join", "unlink"].includes(String(item.action)) ||
          (item.action === "join" ? !identifier(item.poolId) : item.poolId !== null) ||
          (item.action !== "create" && item.organizationId !== null)) return null;
    } else if (item.kind !== "edit" || !identifier(item.poolId) || !positive(item.recordVersion)) return null;
    return item as PoolIntent;
  } catch { return null; }
}

export function organizationLabel(id: string | null, organizations: readonly Pick<OrganizationViewV1, "organization_id" | "name" | "lifecycle">[]): string {
  if (id === null) return "Ungrouped";
  const organization = organizations.find((value) => value.organization_id === id);
  return organization ? `${organization.name}${organization.lifecycle === "archived" ? " (archived)" : ""}` : "Organization unavailable";
}

export function compatiblePoolChoices<T extends Pick<FinancialPoolViewV1, "provider_key" | "selector">>(pools: readonly T[], provider: string, selector: PoolSelector): readonly T[] {
  return pools.filter((pool) => pool.provider_key === provider && pool.selector === selector);
}

export function poolReason(code: string): string {
  switch (code) {
    case "financial_pool_associated": return "This association is owner metadata. It does not verify provider access or widen the report's scope.";
    case "financial_pool_unassociated": return "Associate only scopes you know belong to the same financial pool. Matching names or balances do not establish shared ownership.";
    case "financial_pool_binding_unavailable": return "A current credential binding is required to associate this unresolved scope. Complete the existing connection setup first.";
    case "financial_pool_incompatible": return "This pool has a different provider or billing scope. Choose a compatible pool or create a distinct one.";
    case "financial_pool_organization_unavailable": return "The selected dashboard organization is unavailable. Refresh the choices before saving.";
    case "registry_revision_conflict":
    case "registry_version_conflict":
    case "financial_pool_scope_changed":
    case "registry_replay_stale": return "The account, scope or registry changed. Review its current pool status before making another change.";
    case "financial_pool_resource_unavailable": return "This resource is unavailable. Restore or enable its account before changing its billing pool.";
    default: return "The pool change could not be confirmed. Refresh its status and resolve the previous change before submitting another.";
  }
}
