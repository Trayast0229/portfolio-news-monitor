import { describe, expect, it } from "vitest";
import { isUsable, usableEngines } from "./engines";

describe("isUsable", () => {
  it("turns off an engine the server can't run", () => {
    expect(isUsable("claude", { claude: "unavailable", finbert: "ready" })).toBe(false);
  });

  it("keeps an engine that is ready or still loading", () => {
    expect(isUsable("finbert", { finbert: "ready" })).toBe(true);
    expect(isUsable("finbert", { finbert: "not_loaded" })).toBe(true);
  });

  it("keeps every engine until the server has answered", () => {
    expect(isUsable("claude", {})).toBe(true);
  });
});

describe("usableEngines", () => {
  it("drops chosen engines the server can't run and keeps the order", () => {
    expect(usableEngines(["claude", "finbert"], { claude: "unavailable", finbert: "ready" })).toEqual(["finbert"]);
    expect(usableEngines(["finbert", "claude"], { claude: "ready", finbert: "not_loaded" })).toEqual(["finbert", "claude"]);
  });

  it("leaves nothing when only an unusable engine was chosen", () => {
    expect(usableEngines(["claude"], { claude: "unavailable" })).toEqual([]);
  });
});
