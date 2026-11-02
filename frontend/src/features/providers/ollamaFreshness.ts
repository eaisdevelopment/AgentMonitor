/** A local observation becomes stale after three refresh periods. */
export function ollamaReadingFreshness(
  observedAt: string | null,
  nowMs: number,
): "current" | "stale" | "unknown" {
  if (observedAt === null || !Number.isFinite(nowMs)) return "unknown";
  const observedMs = Date.parse(observedAt);
  if (!Number.isFinite(observedMs) || observedMs > nowMs + 5_000) return "unknown";
  return nowMs - observedMs > 90_000 ? "stale" : "current";
}
