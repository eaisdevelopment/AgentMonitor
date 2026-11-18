import type { CapacityHistoryPageV2, CapacityHistoryPointV2 } from "../../shared/api/client";

/** Pure bounded history presentation; no provider reads or monetary inference. */
export type FundsHistoryContext = Readonly<{
  accountId: string; resourceId: string; windowId: string;
  sourceId: string; currency: string; asOf: string; periodStart: string; periodEnd: string;
}>;
export type FundsHistoryProgress = Readonly<{
  contextKey: string; items: readonly CapacityHistoryPointV2[];
  nextCursor: string | null; cursors: readonly string[];
}>;
export const FUNDS_HISTORY_PAGE_SIZE = 50;

function instant(value: string): string {
  const match = /^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.(\d{1,6}))?(?:Z|\+00:00)$/.exec(value);
  if (match === null) throw new Error("funds_history_time_invalid");
  const date = new Date(`${match[1]}Z`);
  if (!Number.isFinite(date.getTime()) || date.toISOString().slice(0, 19) !== match[1]) throw new Error("funds_history_time_invalid");
  return `${match[1]}.${(match[2] ?? "").padEnd(6, "0")}Z`;
}

export function fundsHistoryContextKey(context: FundsHistoryContext): string {
  const start = instant(context.periodStart), end = instant(context.periodEnd), cutoff = instant(context.asOf);
  if (start >= end || !/^[A-Z]{3}$/.test(context.currency) ||
      [context.accountId, context.resourceId, context.windowId, context.sourceId].some(value => value.length === 0)) throw new Error("funds_history_context_invalid");
  return JSON.stringify([context.accountId, context.resourceId, context.windowId,
    context.sourceId, context.currency, start, end, cutoff]);
}

function validatePoint(context: FundsHistoryContext, point: CapacityHistoryPointV2): void {
  if (point.observation_id.length === 0 || point.subject.account_id !== context.accountId ||
      point.subject.resource_id !== context.resourceId || point.window_id !== context.windowId ||
      point.window_key.length === 0 || point.provenance.source_id !== context.sourceId ||
      point.metric !== "remaining" || point.series_kind !== "poll_snapshot") throw new Error("funds_history_point_mismatch");
  const observed = instant(point.observed_at), cutoff = instant(context.asOf);
  if (observed < instant(context.periodStart) || observed >= instant(context.periodEnd) || observed > cutoff ||
      instant(point.collected_at) > cutoff || instant(point.stored_at) > cutoff) throw new Error("funds_history_point_cutoff_mismatch");
  const unit = context.currency.toLowerCase();
  const amount = point.value.value;
  if ((point.native_unit !== null && point.native_unit !== unit) ||
      (amount !== null && (amount.unit !== unit || point.native_unit !== unit))) throw new Error("funds_history_currency_mismatch");
  if (amount !== null && (!/^-?(?:0|[1-9][0-9]{0,77})$/.test(amount.coefficient) || amount.coefficient === "-0" ||
      !Number.isInteger(amount.scale) || amount.scale < 0 || amount.scale > 18 ||
      (amount.scale > 0 && amount.coefficient.endsWith("0")))) throw new Error("funds_history_amount_invalid");
}

export function appendFundsHistoryPage(
  previous: FundsHistoryProgress | null, context: FundsHistoryContext,
  page: CapacityHistoryPageV2, cursor: string | null,
): FundsHistoryProgress {
  const contextKey = fundsHistoryContextKey(context);
  if (previous !== null && previous.contextKey !== contextKey) throw new Error("funds_history_context_changed");
  if (cursor === null ? previous !== null : previous === null || previous.nextCursor !== cursor) throw new Error("funds_history_cursor_mismatch");
  const absent = page.availability.state === "unavailable" && page.availability.reason_code === "capacity_history_absent" &&
    page.items.length === 0 && !page.page.has_more && page.page.next_cursor === null;
  if (page.subject_id !== context.accountId || page.metric !== "remaining" || page.series_kind !== "poll_snapshot" ||
      instant(page.availability.as_of) !== instant(context.asOf) || (!absent && !["available", "partial"].includes(page.availability.state)) ||
      page.page.limit !== FUNDS_HISTORY_PAGE_SIZE || page.items.length > FUNDS_HISTORY_PAGE_SIZE) throw new Error("funds_history_page_mismatch");
  const next = page.page.next_cursor;
  if (page.page.has_more ? page.items.length === 0 || typeof next !== "string" || next.trim().length === 0 : next !== null) throw new Error("funds_history_page_invalid");
  const cursors = cursor === null ? [] : [...(previous?.cursors ?? []), cursor];
  if (next !== null && cursors.includes(next)) throw new Error("funds_history_cursor_repeated");
  const retained = previous?.items ?? [];
  const seen = new Set(retained.map(point => point.observation_id));
  const windowKey = retained[0]?.window_key ?? page.items[0]?.window_key;
  for (const point of page.items) {
    validatePoint(context, point);
    if (point.window_key !== windowKey) throw new Error("funds_history_window_changed");
    if (seen.has(point.observation_id)) throw new Error("funds_history_duplicate_observation");
    seen.add(point.observation_id);
  }
  return { contextKey, items: [...retained, ...page.items], nextCursor: next, cursors };
}

export function fundsHistoryGapReason(point: CapacityHistoryPointV2): string | null {
  if (point.value.value === null) return (point.value.reason_code ?? "Amount not reported").replaceAll("_", " ");
  if (!["available", "stale"].includes(point.value.availability)) {
    return (point.value.reason_code ?? point.value.availability).replaceAll("_", " ");
  }
  if (!["authoritative", "provider_reported"].includes(point.value.value_kind)) return "Source amount not established";
  if (!["exact", "rounded"].includes(point.value.precision)) return "Source precision not established";
  return null;
}

/** Only visual ratios use Number; source quantities and displayed amounts stay exact. */
export function fundsHistoryPlot(points: readonly CapacityHistoryPointV2[]) {
  const entries = points.map(point => {
    const gap = fundsHistoryGapReason(point);
    const amount = point.value.value;
    const scaled = gap !== null || amount === null ? null : BigInt(amount.coefficient) * 10n ** BigInt(18 - amount.scale);
    return { point, gap, scaled };
  });
  const maximum = entries.reduce((max, { scaled }) => {
    const magnitude = scaled === null ? 0n : scaled < 0n ? -scaled : scaled;
    return magnitude > max ? magnitude : max;
  }, 0n);
  return entries.map(({ point, gap, scaled }) => ({
    point, gap,
    direction: scaled === null ? null : scaled === 0n ? "zero" : scaled < 0n ? "negative" : "positive",
    magnitudeBasisPoints: scaled === null ? null : maximum === 0n ? 0 : Number((scaled < 0n ? -scaled : scaled) * 10000n / maximum),
  }));
}
