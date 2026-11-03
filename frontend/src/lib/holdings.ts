// Which holding rows count. The editor's total and the request must agree,
// or the editor can say 100% while the server scales the weights.

import type { HoldingInput } from "./api";

/** Rows with an ASX code, trimmed. Blank rows are never sent. */
export function filledHoldings(holdings: HoldingInput[]): HoldingInput[] {
  return holdings.filter((h) => h.ticker.trim()).map((h) => ({ ticker: h.ticker.trim(), weight: h.weight }));
}

/** The first thing to fix before the holdings can be sent, mirroring the server's rules. */
export function holdingsProblem(holdings: HoldingInput[]): string | null {
  const filled = filledHoldings(holdings);
  if (!filled.length) return "Add at least one holding.";
  if (filled.some((h) => !Number.isFinite(h.weight) || h.weight <= 0)) return "Give every holding a weight above 0%.";
  if (filled.some((h) => h.weight > 100)) return "Keep each weight at 100% or less.";
  const tickers = filled.map((h) => h.ticker);
  if (new Set(tickers).size !== tickers.length) return "Each ASX code can only appear once.";
  return null;
}

export function weightTotal(holdings: HoldingInput[]): number {
  const total = filledHoldings(holdings).reduce((sum, h) => sum + (Number.isFinite(h.weight) ? h.weight : 0), 0);
  return Math.round(total * 1e9) / 1e9; // float noise can push 99.5 to 99.50000000000001, like the server's round(total, 9)
}
