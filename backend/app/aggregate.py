"""Turn per-holding sentiment into one portfolio verdict.

The math is deliberately simple so it can be shown on screen:

1. Holdings the news doesn't touch are dropped.
2. The remaining weights are rescaled to sum to 1.
3. Portfolio probabilities are the weighted average of holding probabilities.
4. score = 50 + 50 * (bullish - bearish), on a 0-100 scale, halves rounding up.
"""

import math

from .models import EngineName, EngineResult, HoldingIn, HoldingScore, Label, PortfolioResult, ResolvedHolding

_WEIGHT_TOLERANCE = 0.5  # percentage points of drift we treat as "sums to 100"


def normalize_weights(holdings: list[HoldingIn]) -> tuple[list[float], bool]:
    """Return weights as fractions of 1, and whether they had to be rescaled."""
    total = sum(h.weight for h in holdings)
    adjusted = abs(round(total, 9) - 100) > _WEIGHT_TOLERANCE  # float noise can push 99.5 to 99.4999...
    return [h.weight / total for h in holdings], adjusted


def score_from_probs(bullish: float, bearish: float) -> int:
    # Halves round up (60.5 -> 61). Python's round() would send them to the even
    # neighbour, and float noise can turn 22.5 into 22.4999..., hence round(..., 9) first.
    return math.floor(round(50 + 50 * (bullish - bearish), 9) + 0.5)


def label_for(score: int) -> Label:
    if score < 20:
        return "Strongly bearish"
    if score < 40:
        return "Bearish"
    if score <= 60:
        return "Neutral"
    if score <= 80:
        return "Bullish"
    return "Strongly bullish"


def aggregate(engine: EngineName, holdings: list[ResolvedHolding], result: EngineResult) -> PortfolioResult:
    by_ticker = {s.ticker: s for s in result.per_holding}
    related_weight = sum(h.weight for h in holdings if (s := by_ticker.get(h.ticker)) and s.relevant)

    rows: list[HoldingScore] = []
    bull = neu = bear = 0.0
    for h in holdings:
        s = by_ticker.get(h.ticker)
        if s is None or not s.relevant or related_weight == 0:
            rows.append(
                HoldingScore(
                    ticker=h.ticker, name=h.name, weight=h.weight, relevant=False,
                    assessed=s.assessed if s else False, effective_weight=0.0,
                    bullish=None, neutral=None, bearish=None, score=None, label=None,
                    reason=s.reason if s else "", confidence=s.confidence if s else None,
                )
            )
            continue

        w = h.weight / related_weight
        bull += w * s.bullish
        neu += w * s.neutral
        bear += w * s.bearish
        score = score_from_probs(s.bullish, s.bearish)
        rows.append(
            HoldingScore(
                ticker=h.ticker, name=h.name, weight=h.weight, relevant=True, assessed=True, effective_weight=w,
                bullish=s.bullish, neutral=s.neutral, bearish=s.bearish, score=score, label=label_for(score),
                reason=s.reason, confidence=s.confidence,
            )
        )

    extras = result.model_dump(include={"summary", "key_points", "time_horizon", "risks", "watch_items"})
    if related_weight == 0:
        return PortfolioResult(engine=engine, status="unrelated", holdings=rows, **extras)

    score = score_from_probs(bull, bear)
    return PortfolioResult(
        engine=engine, status="ok", score=score, label=label_for(score),
        bullish=bull, neutral=neu, bearish=bear, exposure=related_weight, holdings=rows, **extras,
    )
