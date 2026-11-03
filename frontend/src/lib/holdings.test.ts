import { describe, expect, it } from "vitest";
import { filledHoldings, holdingsProblem, weightTotal } from "./holdings";

describe("holdingsProblem", () => {
  it("accepts weights from just above 0 up to 100", () => {
    expect(holdingsProblem([{ ticker: "BHP", weight: 0.1 }])).toBeNull();
    expect(holdingsProblem([{ ticker: "BHP", weight: 100 }])).toBeNull();
  });

  it("rejects a weight above 100% before the server does", () => {
    expect(holdingsProblem([{ ticker: "BHP", weight: 150 }])).toBe("Keep each weight at 100% or less.");
  });

  it("rejects missing, zero and duplicate entries", () => {
    expect(holdingsProblem([{ ticker: "", weight: 50 }])).toBe("Add at least one holding.");
    expect(holdingsProblem([{ ticker: "BHP", weight: 0 }])).toBe("Give every holding a weight above 0%.");
    expect(holdingsProblem([{ ticker: "BHP", weight: NaN }])).toBe("Give every holding a weight above 0%.");
    expect(
      holdingsProblem([
        { ticker: "BHP", weight: 50 },
        { ticker: " BHP", weight: 50 },
      ]),
    ).toBe("Each ASX code can only appear once.");
  });
});

describe("filledHoldings", () => {
  it("drops rows without an ASX code and trims the rest", () => {
    expect(
      filledHoldings([
        { ticker: " BHP ", weight: 40 },
        { ticker: "  ", weight: 30 },
        { ticker: "CBA", weight: 30 },
      ]),
    ).toEqual([
      { ticker: "BHP", weight: 40 },
      { ticker: "CBA", weight: 30 },
    ]);
  });
});

describe("weightTotal", () => {
  it("adds up only the rows that will be sent", () => {
    // The blank row is dropped before analysis, so it mustn't make the total look like 100%.
    const holdings = [
      { ticker: "BHP", weight: 40 },
      { ticker: "CBA", weight: 30 },
      { ticker: "", weight: 30 },
    ];
    expect(weightTotal(holdings)).toBe(70);
  });

  it("treats empty weights as 0", () => {
    expect(weightTotal([{ ticker: "BHP", weight: 60 }, { ticker: "CBA", weight: NaN }])).toBe(60);
  });

  it("ignores float noise, so a total of exactly 99.5 isn't scaled", () => {
    // Added one by one these come to 99.50000000000001.
    const holdings = [
      { ticker: "BHP", weight: 30.6 },
      { ticker: "CBA", weight: 34.45 },
      { ticker: "CSL", weight: 34.45 },
    ];
    expect(weightTotal(holdings)).toBe(99.5);
  });
});
