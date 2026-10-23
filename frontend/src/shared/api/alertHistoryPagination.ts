import type {
  AlertHistoryPageV1,
  AlertHistoryWireV1,
} from "../../generated/api";

export const ALERT_HISTORY_PAGE_LIMIT = 200 as const;
export const ALERT_HISTORY_MAX_PAGES = 200 as const;
export const ALERT_HISTORY_MAX_ENTRIES = 40_000 as const;

export type AlertHistoryPaginationStateV1 = Readonly<{
  alertId: string;
  entries: readonly AlertHistoryWireV1[];
  nextCursor: string | null;
  pageCount: number;
  seenCursors: readonly string[];
  terminal: boolean;
}>;

export type AlertHistoryPaginationResultV1 =
  | Readonly<{ ok: true; state: AlertHistoryPaginationStateV1 }>
  | Readonly<{
      ok: false;
      reason:
        | "alert_history_selection_invalid"
        | "alert_history_page_invalid"
        | "alert_history_page_incomplete";
    }>;

type AlertHistoryPageSelectionV1 = Readonly<{
  alertId: string;
  cursor: string | null;
}>;

const controls = /[\u0000-\u001f\u007f-\u009f]/u;

function boundedToken(value: unknown, maximum: number): value is string {
  return typeof value === "string"
    && value.length > 0
    && [...value].length <= maximum
    && !controls.test(value);
}

function validEntry(
  value: AlertHistoryWireV1,
  alertId: string,
): boolean {
  return boundedToken(value?.event_id, 128)
    && value.alert_id === alertId
    && Number.isSafeInteger(value.aggregate_sequence)
    && value.aggregate_sequence > 0;
}

function validRetainedState(state: AlertHistoryPaginationStateV1): boolean {
  if (!boundedToken(state.alertId, 128)
      || !Number.isSafeInteger(state.pageCount)
      || state.pageCount < 1
      || state.pageCount > ALERT_HISTORY_MAX_PAGES
      || state.entries.length < 1
      || state.entries.length > ALERT_HISTORY_MAX_ENTRIES
      || !Array.isArray(state.seenCursors)
      || state.seenCursors.length > ALERT_HISTORY_MAX_PAGES - 1
      || new Set(state.seenCursors).size !== state.seenCursors.length
      || state.seenCursors.some((cursor) => !boundedToken(cursor, 1024))
      || state.terminal !== (state.nextCursor === null)
      || (!state.terminal && state.seenCursors.at(-1) !== state.nextCursor)) {
    return false;
  }
  const eventIds = new Set<string>();
  const sequences = new Set<number>();
  let previousSequence = 0;
  for (const entry of state.entries) {
    if (!validEntry(entry, state.alertId)
        || eventIds.has(entry.event_id)
        || sequences.has(entry.aggregate_sequence)
        || entry.aggregate_sequence <= previousSequence) {
      return false;
    }
    eventIds.add(entry.event_id);
    sequences.add(entry.aggregate_sequence);
    previousSequence = entry.aggregate_sequence;
  }
  return true;
}

/**
 * Validate and append one V1 alert-history page without guessing completion.
 * The retained state is immutable so a later failed page cannot discard rows
 * that were already shown to the operator.
 */
export function appendAlertHistoryPageV1(
  current: AlertHistoryPaginationStateV1 | null,
  document: AlertHistoryPageV1,
  selection: AlertHistoryPageSelectionV1,
): AlertHistoryPaginationResultV1 {
  if (!boundedToken(selection?.alertId, 128)
      || !(selection.cursor === null || boundedToken(selection.cursor, 1024))
      || (current === null && selection.cursor !== null)
      || (current !== null
        && (!validRetainedState(current)
          || current.alertId !== selection.alertId
          || current.terminal
          || selection.cursor !== current.nextCursor))) {
    return { ok: false, reason: "alert_history_selection_invalid" };
  }
  if (document === null
      || typeof document !== "object"
      || Array.isArray(document)
      || document.availability?.state !== "available"
      || !Array.isArray(document.items)
      || document.items.length < 1
      || document.items.length > ALERT_HISTORY_PAGE_LIMIT
      || document.page === null
      || typeof document.page !== "object"
      || Array.isArray(document.page)
      || document.page.limit !== ALERT_HISTORY_PAGE_LIMIT
      || typeof document.page.has_more !== "boolean") {
    return { ok: false, reason: "alert_history_page_invalid" };
  }

  const retained = current?.entries ?? [];
  const eventIds = new Set(retained.map((entry) => entry.event_id));
  const sequences = new Set(retained.map((entry) => entry.aggregate_sequence));
  let previousSequence = retained.at(-1)?.aggregate_sequence ?? 0;
  for (const entry of document.items) {
    if (!validEntry(entry, selection.alertId)
        || eventIds.has(entry.event_id)
        || sequences.has(entry.aggregate_sequence)
        || entry.aggregate_sequence <= previousSequence) {
      return { ok: false, reason: "alert_history_page_incomplete" };
    }
    eventIds.add(entry.event_id);
    sequences.add(entry.aggregate_sequence);
    previousSequence = entry.aggregate_sequence;
  }

  const pageCount = (current?.pageCount ?? 0) + 1;
  const entryCount = retained.length + document.items.length;
  if (pageCount > ALERT_HISTORY_MAX_PAGES
      || entryCount > ALERT_HISTORY_MAX_ENTRIES) {
    return { ok: false, reason: "alert_history_page_incomplete" };
  }

  const nextCursor = document.page.next_cursor;
  const seenCursors = current?.seenCursors ?? [];
  if (!document.page.has_more) {
    if (nextCursor !== null) {
      return { ok: false, reason: "alert_history_page_invalid" };
    }
    return {
      ok: true,
      state: Object.freeze({
        alertId: selection.alertId,
        entries: Object.freeze([...retained, ...document.items]),
        nextCursor: null,
        pageCount,
        seenCursors: Object.freeze([...seenCursors]),
        terminal: true,
      }),
    };
  }

  if (pageCount >= ALERT_HISTORY_MAX_PAGES
      || !boundedToken(nextCursor, 1024)
      || nextCursor === selection.cursor
      || seenCursors.includes(nextCursor)) {
    return { ok: false, reason: "alert_history_page_incomplete" };
  }
  return {
    ok: true,
    state: Object.freeze({
      alertId: selection.alertId,
      entries: Object.freeze([...retained, ...document.items]),
      nextCursor,
      pageCount,
      seenCursors: Object.freeze([...seenCursors, nextCursor]),
      terminal: false,
    }),
  };
}
