/** Read every page of one authenticated versioned API collection. */

const PAGE_LIMIT = 200;
const MAX_PAGE_COUNT = 10_000;

async function readAllAvailablePagesV1(read, path, errorScope) {
  if (typeof read !== "function"
    || typeof path !== "string"
    || !path.startsWith("/api/v1/")
    || path.includes("#")
    || /(?:[?&])(?:limit|cursor)=/u.test(path)) {
    throw new Error(`${errorScope}_page_selection_invalid`);
  }
  const items = [];
  const seenCursors = new Set();
  let availability = null;
  let cursor = null;
  for (let pageCount = 0; pageCount < MAX_PAGE_COUNT; pageCount += 1) {
    const separator = path.includes("?") ? "&" : "?";
    const cursorParameter = cursor === null
      ? ""
      : `&cursor=${encodeURIComponent(cursor)}`;
    const document = await read(
      `${path}${separator}limit=${PAGE_LIMIT}${cursorParameter}`,
    );
    if (document === null
      || typeof document !== "object"
      || Array.isArray(document)
      || document.availability?.state !== "available"
      || !Array.isArray(document.items)
      || document.items.length > PAGE_LIMIT
      || document.page === null
      || typeof document.page !== "object"
      || Array.isArray(document.page)
      || typeof document.page.has_more !== "boolean") {
      throw new Error(`${errorScope}_page_invalid`);
    }
    availability ??= document.availability;
    items.push(...document.items);
    if (!document.page.has_more) {
      return Object.freeze({
        items: Object.freeze(items),
        availability: Object.freeze({ ...availability }),
      });
    }
    const nextCursor = document.page.next_cursor;
    if (typeof nextCursor !== "string"
      || nextCursor.length === 0
      || nextCursor === cursor
      || seenCursors.has(nextCursor)) {
      throw new Error(`${errorScope}_page_incomplete`);
    }
    seenCursors.add(nextCursor);
    cursor = nextCursor;
  }
  throw new Error(`${errorScope}_page_incomplete`);
}

export async function readAllRegistryItemsV1(read, path) {
  const document = await readAllAvailablePagesV1(read, path, "registry");
  return document.items;
}

export function advanceCapacityHistoryPageV1(document, selection, state) {
  const seenCursors = new Set(state?.seenCursors);
  const seenObservationIds = new Set(state?.seenObservationIds);
  const cursor = state?.cursor;
  if (!selection
    || typeof selection.subject_id !== "string"
    || typeof selection.metric !== "string"
    || typeof selection.series_kind !== "string"
    || !state
    || !(cursor === null || typeof cursor === "string")
    || !Array.isArray(state.seenCursors)
    || seenCursors.size !== state.seenCursors.length
    || !Array.isArray(state.seenObservationIds)
    || seenObservationIds.size !== state.seenObservationIds.length
    || document === null
    || typeof document !== "object"
    || Array.isArray(document)
    || document.subject_id !== selection.subject_id
    || document.metric !== selection.metric
    || document.series_kind !== selection.series_kind
    || document.availability?.state !== "available"
    || !Array.isArray(document.items)
    || document.items.length > PAGE_LIMIT
    || document.page === null
    || typeof document.page !== "object"
    || Array.isArray(document.page)
    || document.page.limit !== PAGE_LIMIT
    || typeof document.page.has_more !== "boolean") {
    throw new Error("capacity_history_page_invalid");
  }
  const observationIds = [];
  for (const item of document.items) {
    const observationId = item?.observation_id;
    if (typeof observationId !== "string"
      || observationId.length === 0
      || observationId.length > 256
      || /[\u0000-\u001f\u007f]/u.test(observationId)
      || seenObservationIds.has(observationId)
      || observationIds.includes(observationId)) {
      throw new Error("capacity_history_page_incomplete");
    }
    observationIds.push(observationId);
  }
  const nextCursor = document.page.next_cursor;
  if (!document.page.has_more) {
    if (nextCursor !== null) throw new Error("capacity_history_page_invalid");
    return Object.freeze({
      items: Object.freeze([...document.items]),
      observationIds: Object.freeze(observationIds),
      nextCursor: null,
      terminal: true,
    });
  }
  if (typeof nextCursor !== "string"
    || nextCursor.length === 0
    || nextCursor.length > 1024
    || /[\u0000-\u001f\u007f]/u.test(nextCursor)
    || nextCursor === cursor
    || seenCursors.has(nextCursor)) {
    throw new Error("capacity_history_page_incomplete");
  }
  return Object.freeze({
    items: Object.freeze([...document.items]),
    observationIds: Object.freeze(observationIds),
    nextCursor,
    terminal: false,
  });
}

export async function readAllCapacityHistoryV1(read, path) {
  let selection;
  try {
    const url = new URL(path, "http://agentmonitor.invalid");
    const exact = name => {
      const values = url.searchParams.getAll(name);
      if (values.length !== 1 || values[0].length === 0) throw new Error();
      return values[0];
    };
    if (typeof read !== "function"
      || typeof path !== "string"
      || path.length > 8192
      || url.origin !== "http://agentmonitor.invalid"
      || url.pathname !== "/api/v1/capacity/history"
      || url.hash
      || url.searchParams.has("limit")
      || url.searchParams.has("cursor")) {
      throw new Error();
    }
    selection = Object.freeze({
      subject_id: exact("subject_id"),
      metric: exact("metric"),
      series_kind: exact("series_kind"),
    });
  } catch {
    throw new Error("capacity_history_page_selection_invalid");
  }
  const items = [];
  const seenCursors = new Set();
  const seenObservationIds = new Set();
  let availability = null;
  let cursor = null;
  for (let pageCount = 0; pageCount < MAX_PAGE_COUNT; pageCount += 1) {
    const cursorParameter = cursor === null
      ? ""
      : `&cursor=${encodeURIComponent(cursor)}`;
    const document = await read(
      `${path}&limit=${PAGE_LIMIT}${cursorParameter}`,
    );
    const decision = advanceCapacityHistoryPageV1(document, selection, {
      cursor,
      seenCursors: [...seenCursors],
      seenObservationIds: [...seenObservationIds],
    });
    availability ??= document.availability;
    items.push(...decision.items);
    for (const observationId of decision.observationIds) {
      seenObservationIds.add(observationId);
    }
    if (decision.terminal) {
      return Object.freeze({
        ...selection,
        items: Object.freeze(items),
        availability: Object.freeze({ ...availability }),
      });
    }
    seenCursors.add(decision.nextCursor);
    cursor = decision.nextCursor;
  }
  throw new Error("capacity_history_page_incomplete");
}
