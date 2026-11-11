import { registry, type AccountPageV1, type OrganizationPageV1, type ClientResult } from "../../shared/api/client";

/** Complete bounded registry traversal; a failed later page never means all. */
async function pages<T extends AccountPageV1 | OrganizationPageV1>(
  read: (signal?: AbortSignal, cursor?: string) => Promise<ClientResult<T>>,
  identity: (item: T["items"][number]) => string,
  signal: AbortSignal,
): Promise<ClientResult<T>> {
  let result = await read(signal);
  if (!result.ok) return result;
  const items = [...result.data.items];
  const seen = new Set(items.map(identity));
  const cursors = new Set<string>();
  while (result.data.page.has_more) {
    const cursor = result.data.page.next_cursor;
    if (cursor === null || cursors.has(cursor) || cursors.size >= 100) throw new Error("overview_inventory_pagination_invalid");
    cursors.add(cursor);
    const next = await read(signal, cursor);
    if (!next.ok) return next;
    for (const item of next.data.items) {
      const id = identity(item);
      if (seen.has(id)) throw new Error("overview_inventory_changed");
      seen.add(id);
      items.push(item);
    }
    result = next;
  }
  return { ...result, data: { ...result.data, items } };
}

export const allOverviewAccounts = (signal: AbortSignal) => pages(registry.accounts, item => "account_id" in item ? item.account_id : "", signal);
export const allOverviewOrganizations = (signal: AbortSignal) => pages(registry.organizations, item => "organization_id" in item ? item.organization_id : "", signal);
