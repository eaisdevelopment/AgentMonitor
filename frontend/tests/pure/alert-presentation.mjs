"use strict";

import assert from "node:assert/strict";

import { alertPresentation } from "../../src/features/alerts/alertPresentation.ts";

const presentation = alertPresentation({
  condition_type: "capacity_remaining",
  lifecycle: "open",
  severity: "critical",
  remaining_basis_points: "9400",
  warning_remaining_basis_points: 10000,
  critical_remaining_basis_points: 10000,
  decision_reason_code: "quota_remaining",
});

assert.deepEqual(presentation, {
  title: "Capacity threshold reached",
  remaining: "94% remaining",
  explanation: "Critical threshold: 100% or less",
});
assert.doesNotMatch(JSON.stringify(presentation), /\blow\b/i);

assert.deepEqual(alertPresentation({
  condition_type: "capacity_remaining",
  lifecycle: "open",
  severity: "warning",
  remaining_basis_points: "1850",
  warning_remaining_basis_points: 3000,
  critical_remaining_basis_points: 1500,
  decision_reason_code: "quota_remaining",
}), {
  title: "Capacity threshold reached",
  remaining: "18.5% remaining",
  explanation: "Warning threshold: 30% or less",
});

assert.deepEqual(alertPresentation({
  condition_type: "capacity_remaining",
  lifecycle: "recovered",
  severity: "information",
  remaining_basis_points: "9400",
  warning_remaining_basis_points: 0,
  critical_remaining_basis_points: 0,
  decision_reason_code: "quota_remaining",
}), {
  title: "Capacity threshold cleared",
  remaining: "94% remaining",
  explanation: "Warning threshold: 0% or less",
});

assert.deepEqual(alertPresentation({
  condition_type: "capacity_remaining",
  lifecycle: "closed_by_configuration",
  severity: "information",
  remaining_basis_points: "9400",
  warning_remaining_basis_points: 0,
  critical_remaining_basis_points: 0,
  decision_reason_code: "quota_remaining",
}), {
  title: "Capacity alert closed",
  remaining: "94% remaining",
  explanation: "Configured capacity rule is inactive",
});

assert.deepEqual(alertPresentation({
  condition_type: "capacity_unavailable",
  lifecycle: "open",
  severity: "warning",
  remaining_basis_points: null,
  warning_remaining_basis_points: null,
  critical_remaining_basis_points: null,
  decision_reason_code: "quota_unavailable",
}), {
  title: "Capacity unavailable",
  remaining: null,
  explanation: "quota unavailable",
});

console.log("ALERT PRESENTATION PURE: PASSED");
