// Pure helpers for the recent-analyses list, kept apart from storage so they
// can be tested without a browser.

import type { HoldingInput, PortfolioResult, TickerMatch } from "./api";
import { zoneFor } from "./gauge";
import type { HistoryEntry } from "./storage";

// Two entries are the same run when the story, holdings and engines match.
function runKey(entry: HistoryEntry): string {
  const engines = entry.response.results.map((r) => r.engine).sort();
  return JSON.stringify([entry.news.trim(), entry.holdings, engines]);
}

/** Adds an entry to the top, dropping any earlier copy of the same run. */
export function mergeHistory(history: HistoryEntry[], entry: HistoryEntry, limit: number): HistoryEntry[] {
  const key = runKey(entry);
  return [entry, ...history.filter((e) => runKey(e) !== key)].slice(0, limit);
}

export function historyScore(result: PortfolioResult): { text: string; className: string; title?: string } {
  if (result.status === "error") return { text: "Error", className: "history-error", title: result.error ?? undefined };
  if (result.score === null) return { text: "Unrelated", className: "muted" };
  return { text: String(result.score), className: `tone-text-${zoneFor(result.score).tone}` };
}

/** Tickers whose company name hasn't been requested yet, once each. */
export function tickersToLookUp(holdings: HoldingInput[], requested: Set<string>): string[] {
  const tickers = holdings.map((h) => h.ticker.trim()).filter((t) => t && !requested.has(t));
  return [...new Set(tickers)];
}

// Looks up one ticker's company name. A failed lookup, for example while the
// backend is still starting, is tried again every few seconds until it works.
export function lookUpName(
  ticker: string,
  search: (ticker: string) => Promise<TickerMatch[]>,
  found: (matches: TickerMatch[]) => void,
  retryMs = 3000,
): void {
  search(ticker)
    .then(found)
    .catch(() => setTimeout(() => lookUpName(ticker, search, found, retryMs), retryMs));
}
