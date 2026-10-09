import type { AlertWireV1 } from "../../shared/api/client";

type AlertPresentationInput = Pick<AlertWireV1,
  "condition_type" | "critical_remaining_basis_points" |
  "decision_reason_code" | "lifecycle" | "remaining_basis_points" | "severity" |
  "warning_remaining_basis_points">;

export type AlertPresentation = Readonly<{
  title: string;
  remaining: string | null;
  explanation: string;
}>;

const conditionNames: Readonly<Record<AlertWireV1["condition_type"], string>> = {
  capacity_remaining: "Capacity threshold reached",
  capacity_exhausted: "Capacity exhausted",
  capacity_unavailable: "Capacity unavailable",
  forecasted_exhaustion: "Capacity may run out",
  authentication_attention: "Sign-in needs attention",
  data_stale: "Reading is stale",
  collector_failure: "Collector failed",
  possible_stall: "Agent may be stalled",
};

function percentFromBasisPoints(value: string | number | null): string | null {
  if (value === null) return null;
  const percent = Number(value) / 100;
  if (!Number.isFinite(percent) || percent < 0 || percent > 100) return null;
  return String(Number(percent.toFixed(2)));
}

export function alertPresentation(alert: AlertPresentationInput): AlertPresentation {
  const remainingPercent = percentFromBasisPoints(alert.remaining_basis_points);
  const remaining = remainingPercent === null ? null : `${remainingPercent}% remaining`;
  if (alert.condition_type !== "capacity_remaining") {
    return {
      title: conditionNames[alert.condition_type],
      remaining,
      explanation: alert.decision_reason_code.replaceAll("_", " "),
    };
  }

  if (alert.lifecycle === "closed_by_configuration") {
    return {
      title: "Capacity alert closed",
      remaining,
      explanation: "Configured capacity rule is inactive",
    };
  }

  if (alert.lifecycle === "recovered") {
    const warningPercent = percentFromBasisPoints(alert.warning_remaining_basis_points);
    return {
      title: "Capacity threshold cleared",
      remaining,
      explanation: warningPercent === null
        ? "Configured capacity threshold cleared"
        : `Warning threshold: ${warningPercent}% or less`,
    };
  }

  const thresholdBasisPoints = alert.severity === "critical"
    ? alert.critical_remaining_basis_points
    : alert.severity === "warning" ? alert.warning_remaining_basis_points : null;
  const thresholdPercent = percentFromBasisPoints(thresholdBasisPoints);
  const thresholdName = alert.severity === "critical" ? "Critical" : "Warning";
  return {
    title: conditionNames.capacity_remaining,
    remaining,
    explanation: thresholdPercent === null
      ? "Configured capacity threshold reached"
      : `${thresholdName} threshold: ${thresholdPercent}% or less`,
  };
}
