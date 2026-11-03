// Holdings an engine left out of its answer. They're not in the score, like
// holdings the story doesn't touch, but the user should be told they were skipped.

import { ENGINE_NAMES, type HoldingScore, type PortfolioResult } from "./api";

// History saved before `assessed` existed has no such field; treat it as assessed.
const wasSkipped = (h: HoldingScore) => h.assessed === false;

export const notScoredLabel = (h: HoldingScore) => (wasSkipped(h) ? "Not assessed" : "Not affected");

function joinList(items: string[]): string {
  return items.length < 2 ? items.join("") : `${items.slice(0, -1).join(", ")} and ${items[items.length - 1]}`;
}

export function skippedNotice(result: PortfolioResult): string | null {
  const skipped = result.holdings.filter(wasSkipped).map((h) => h.ticker);
  if (!skipped.length) return null;
  const one = skipped.length === 1;
  return (
    `${ENGINE_NAMES[result.engine]} skipped ${joinList(skipped)}, so ${one ? "it isn't" : "they aren't"} ` +
    `part of this score. Try again to include ${one ? "it" : "them"}.`
  );
}

// FinBERT was trained on English. Counting letters rather than words keeps a Chinese
// story with a few English tickers flagged, and an English story quoting a name not.
function mostlyNotEnglish(text: string): boolean {
  const letters = text.match(/\p{L}/gu) ?? [];
  const english = letters.filter((c) => /[a-z]/i.test(c)).length;
  return letters.length > 0 && english / letters.length < 0.7;
}

export function languageNotice(result: PortfolioResult, news: string): string | null {
  return result.engine === "finbert" && mostlyNotEnglish(news)
    ? "FinBERT reads English only, so it may have missed this story."
    : null;
}
