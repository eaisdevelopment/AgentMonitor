import type { ExactMoneyWireV1 } from "../../shared/api/client";

function decimal(coefficient: bigint, scale: number): string {
  const negative = coefficient < 0n;
  const digits = (negative ? -coefficient : coefficient).toString().padStart(scale + 1, "0");
  return `${negative ? "-" : ""}${scale === 0 ? digits : `${digits.slice(0, -scale)}.${digits.slice(-scale)}`}`;
}

/** Formatting only; totals and financial availability come from the API. */
export function exactMoneyText(money: ExactMoneyWireV1): string {
  return `${decimal(BigInt(money.coefficient), money.scale)} ${money.currency}`;
}

export function displayMoney(money: ExactMoneyWireV1): string {
  if (money.currency !== "USD") return exactMoneyText(money);
  const coefficient = BigInt(money.coefficient);
  const negative = coefficient < 0n;
  const magnitude = negative ? -coefficient : coefficient;
  if (money.scale <= 2) return `${decimal(coefficient * 10n ** BigInt(2 - money.scale), 2)} USD`;
  const divisor = 10n ** BigInt(money.scale - 2);
  if (magnitude > 0n && magnitude < divisor) return `${negative ? "-" : ""}<0.01 USD`;
  let cents = magnitude / divisor;
  const remainder = magnitude % divisor;
  if (remainder * 2n > divisor || (remainder * 2n === divisor && cents % 2n === 1n)) cents += 1n;
  return `${decimal(negative ? -cents : cents, 2)} USD`;
}

export function completedPeriod(days: 7 | 30, now: Date) {
  const end = Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate());
  return {
    period_start: new Date(end - days * 86400000).toISOString(),
    period_end: new Date(end).toISOString(),
    as_of: now.toISOString(),
  };
}
