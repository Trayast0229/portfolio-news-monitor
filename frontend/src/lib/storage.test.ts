import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { PortfolioResult } from "./api";
import { DEFAULT_HOLDINGS, loadEngines, loadHistory, loadHoldings, type HistoryEntry } from "./storage";

// Vitest runs in Node, which has no localStorage, so each test gets a fresh in-memory one.
let store: Map<string, string>;
beforeEach(() => {
  store = new Map();
  vi.stubGlobal("localStorage", {
    getItem: (k: string) => store.get(k) ?? null,
    setItem: (k: string, v: string) => store.set(k, v),
  });
});
afterEach(() => vi.unstubAllGlobals());

const result: PortfolioResult = {
  engine: "finbert",
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
};
const entry: HistoryEntry = {
  id: "1",
  at: "2026-11-03T00:00:00.000Z",
  news: "BHP lifts its dividend.",
  holdings: [{ ticker: "BHP", weight: 100 }],
  response: { weights_adjusted: false, results: [result] },
};

describe("loading saved data", () => {
  it("falls back to the defaults when saved data has the wrong shape", () => {
    for (const bad of ["null", "{}", '"BHP"', "42", '[{"ticker":1}]']) {
      store.set("pnm.holdings", bad);
      store.set("pnm.engines", bad);
      store.set("pnm.history", bad);
      expect(loadHoldings(), bad).toEqual(DEFAULT_HOLDINGS);
      expect(loadEngines(), bad).toEqual(["finbert"]);
      expect(loadHistory(), bad).toEqual([]);
    }
  });

  it("drops engines it doesn't know", () => {
    store.set("pnm.engines", '["gpt","claude"]');
    expect(loadEngines()).toEqual(["claude"]);
    // Built-in object names aren't engines either.
    store.set("pnm.engines", '["toString","constructor"]');
    expect(loadEngines()).toEqual(["finbert"]);
  });

  it("drops history entries it can't show and keeps the rest", () => {
    store.set("pnm.history", JSON.stringify([entry, { id: "2" }, null, { ...entry, response: {} }]));
    expect(loadHistory()).toEqual([entry]);
  });

  it("keeps what the app itself saves, including blank rows and no engines", () => {
    // A cleared weight is NaN in the app, which JSON saves as null.
    store.set("pnm.holdings", JSON.stringify([{ ticker: "BHP", weight: 60 }, { ticker: "", weight: NaN }]));
    store.set("pnm.engines", "[]");
    store.set("pnm.history", JSON.stringify([entry]));
    expect(loadHoldings()).toEqual([
      { ticker: "BHP", weight: 60 },
      { ticker: "", weight: NaN },
    ]);
    expect(loadEngines()).toEqual([]);
    expect(loadHistory()).toEqual([entry]);
  });
});
