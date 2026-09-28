import type { ExactMetricFieldWireV1 } from "../../shared/api/client";

export function remainingPercentage(field: ExactMetricFieldWireV1): Readonly<{ label: string; value: number }> | null {
  if (!["available", "stale"].includes(field.availability) || field.value === null || !["ratio", "percent"].includes(field.value.unit)) return null;
  const value = Number(field.value.coefficient) * (10 ** ((field.value.unit === "ratio" ? 2 : 0) - field.value.scale));
  if (!Number.isFinite(value) || value < 0 || value > 100) return null;
  return { label: `${Number(value.toFixed(2))}%`, value };
}

export function metricAvailability(field: ExactMetricFieldWireV1): string {
  if (field.availability === "available") return "Unavailable";
  return field.availability.replaceAll("_", " ").replace(/^./, (letter) => letter.toUpperCase());
}
