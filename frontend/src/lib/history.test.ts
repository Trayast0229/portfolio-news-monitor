import { afterEach, describe, expect, it, vi } from "vitest";
import type { EngineName, HoldingInput, PortfolioResult } from "./api";
import { historyScore, lookUpName, mergeHistory, tickersToLookUp } from "./history";
import type { HistoryEntry } from "./storage";

function result(engine: EngineName, patch: Partial<PortfolioResult> = {}): PortfolioResult {
  return {
    engine,
    status: "ok",
    score: 70,
    label: "Bullish",
    bullish: 0.6,
    neutral: 0.3,
    bearish: 0.1,
    exposure: 1,
    holdings: [],
    summary: null,
    key_points: [],
    time_horizon: [],
    risks: [],
    watch_items: [],
    error: null,
    ...patch,
  };
}

const HOLDINGS: HoldingInput[] = [
  { ticker: "BHP", weight: 60 },
  { ticker: "CBA", weight: 40 },
];

function entry(id: string, news: string, engines: EngineName[] = ["finbert"], holdings = HOLDINGS): HistoryEntry {
  return {
    id,
    at: "2026-10-21T00:00:00.000Z",
    news,
    holdings,
    response: { weights_adjusted: false, results: engines.map((e) => result(e)) },
  };
}

describe("mergeHistory", () => {
  it("puts the new entry first", () => {
    const next = mergeHistory([entry("a", "Old story")], entry("b", "New story"), 20);
    expect(next.map((e) => e.id)).toEqual(["b", "a"]);
  });

  it("replaces an earlier run of the same story, holdings and engines", () => {
    const old = [entry("a", "Same story"), entry("b", "Other story")];
    const next = mergeHistory(old, entry("c", "Same story"), 20);
    expect(next.map((e) => e.id)).toEqual(["c", "b"]);
  });

  it("keeps both runs when the engines differ", () => {
    const next = mergeHistory([entry("a", "Same story", ["finbert"])], entry("b", "Same story", ["claude"]), 20);
    expect(next.map((e) => e.id)).toEqual(["b", "a"]);
  });

  it("keeps both runs when the holdings differ", () => {
    const other = [{ ticker: "CSL", weight: 100 }];
    const next = mergeHistory([entry("a", "Same story")], entry("b", "Same story", ["finbert"], other), 20);
    expect(next.map((e) => e.id)).toEqual(["b", "a"]);
  });

  it("treats engine order as the same run", () => {
    const next = mergeHistory(
      [entry("a", "Same story", ["claude", "finbert"])],
      entry("b", "Same story", ["finbert", "claude"]),
      20,
    );
    expect(next.map((e) => e.id)).toEqual(["b"]);
  });

  it("caps the list at the limit", () => {
    const old = [entry("a", "One"), entry("b", "Two")];
    expect(mergeHistory(old, entry("c", "Three"), 2).map((e) => e.id)).toEqual(["c", "a"]);
  });
});

describe("historyScore", () => {
  it("shows the score with its zone tone", () => {
    expect(historyScore(result("claude", { score: 16 }))).toEqual({ text: "16", className: "tone-text-bear-strong" });
  });

  it("says Unrelated when no holding is affected", () => {
    const r = result("finbert", { status: "unrelated", score: null, label: null });
    expect(historyScore(r)).toEqual({ text: "Unrelated", className: "muted" });
  });

  it("says Error and keeps the message when the engine failed", () => {
    const r = result("claude", { status: "error", score: null, label: null, error: "Claude is busy." });
    expect(historyScore(r)).toEqual({ text: "Error", className: "history-error", title: "Claude is busy." });
  });
});

describe("tickersToLookUp", () => {
  it("returns tickers not looked up yet, once each", () => {
    const holdings = [
      { ticker: "BHP", weight: 40 },
      { ticker: "WDS", weight: 30 },
      { ticker: "WDS", weight: 30 },
    ];
    expect(tickersToLookUp(holdings, new Set(["BHP"]))).toEqual(["WDS"]);
  });

  it("skips blank rows", () => {
    expect(tickersToLookUp([{ ticker: " ", weight: 10 }], new Set())).toEqual([]);
  });
});

describe("lookUpName", () => {
  afterEach(() => vi.useRealTimers());

  it("tries again when the backend is not ready yet", async () => {
    vi.useFakeTimers();
    const bhp = [{ ticker: "BHP", name: "BHP Group" }];
    const search = vi.fn().mockRejectedValueOnce(new Error("Backend not running")).mockResolvedValue(bhp);
    const found = vi.fn();

    lookUpName("BHP", search, found);
    await vi.advanceTimersByTimeAsync(10_000);

    expect(found).toHaveBeenCalledWith(bhp);
  });
});
