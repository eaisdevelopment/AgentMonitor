/** Read every page of one authenticated versioned Registry collection. */

const PAGE_LIMIT = 200;
const MAX_PAGE_COUNT = 10_000;

export async function readAllRegistryItemsV1(read, path) {
  if (typeof read !== "function"
    || typeof path !== "string"
    || !path.startsWith("/api/v1/")
    || path.includes("#")) {
    throw new Error("registry_page_selection_invalid");
  }
  const items = [];
  const seenCursors = new Set();
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
      throw new Error("registry_page_invalid");
    }
    items.push(...document.items);
    if (!document.page.has_more) return items;
    const nextCursor = document.page.next_cursor;
    if (typeof nextCursor !== "string"
      || nextCursor.length === 0
      || nextCursor === cursor
      || seenCursors.has(nextCursor)) {
      throw new Error("registry_page_incomplete");
    }
    seenCursors.add(nextCursor);
    cursor = nextCursor;
  }
  throw new Error("registry_page_incomplete");
}
