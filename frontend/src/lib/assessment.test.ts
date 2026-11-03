import { describe, expect, it } from "vitest";
import type { HoldingScore, PortfolioResult } from "./api";
import { languageNotice, notScoredLabel, skippedNotice } from "./assessment";

function holding(ticker: string, patch: Partial<HoldingScore> = {}): HoldingScore {
  return {
    ticker,
    name: null,
    weight: 0.5,
    relevant: false,
    assessed: true,
    effective_weight: 0,
    bullish: null,
    neutral: null,
    bearish: null,
    score: null,
    label: null,
    reason: "",
    confidence: null,
    ...patch,
  };
}

function result(holdings: HoldingScore[], engine: PortfolioResult["engine"] = "claude"): PortfolioResult {
  return {
    engine,
    status: "ok",
    score: 50,
    label: "Neutral",
    bullish: 0,
    neutral: 1,
    bearish: 0,
    exposure: 0.5,
    holdings,
    summary: null,
    key_points: [],
    time_horizon: [],
    risks: [],
    watch_items: [],
    error: null,
  };
}

describe("notScoredLabel", () => {
  it("tells a skipped holding apart from one the story doesn't touch", () => {
    expect(notScoredLabel(holding("CBA", { assessed: false }))).toBe("Not assessed");
    expect(notScoredLabel(holding("CBA"))).toBe("Not affected");
  });

  it("treats history saved before the field existed as assessed", () => {
    const { assessed: _, ...old } = holding("CBA");
    expect(notScoredLabel(old as HoldingScore)).toBe("Not affected");
  });
});

describe("skippedNotice", () => {
  it("is empty when every holding was assessed", () => {
    expect(skippedNotice(result([holding("BHP"), holding("CBA")]))).toBeNull();
  });

  it("names one skipped holding", () => {
    expect(skippedNotice(result([holding("BHP"), holding("CBA", { assessed: false })]))).toBe(
      "Claude skipped CBA, so it isn't part of this score. Try again to include it.",
    );
  });

  it("lists several skipped holdings", () => {
    const skipped = ["BHP", "CBA", "CSL"].map((t) => holding(t, { assessed: false }));
    expect(skippedNotice(result(skipped))).toBe(
      "Claude skipped BHP, CBA and CSL, so they aren't part of this score. Try again to include them.",
    );
  });
});

describe("languageNotice", () => {
  const chinese = "BHP 公布年度獲利創新高，股價週五大漲百分之五。分析師表示鐵礦砂需求強勁，BHP 前景看好。";
  const english = "BHP shares rose 5 per cent on Friday after the miner reported a record annual profit.";

  it("warns that FinBERT can't read a story that is mostly not English", () => {
    expect(languageNotice(result([], "finbert"), chinese)).toBe(
      "FinBERT reads English only, so it may have missed this story.",
    );
  });

  it("stays quiet for English stories, even ones that quote a few other characters", () => {
    expect(languageNotice(result([], "finbert"), english)).toBeNull();
    expect(languageNotice(result([], "finbert"), `${english} Its Chinese name is 必和必拓.`)).toBeNull();
  });

  it("stays quiet for Claude, which reads other languages", () => {
    expect(languageNotice(result([], "claude"), chinese)).toBeNull();
  });
});
