import pytest

from app.aggregate import aggregate, label_for, normalize_weights, score_from_probs
from app.models import EngineResult, HoldingIn, HoldingSentiment, ResolvedHolding


def resolved(*pairs):
    return [ResolvedHolding(ticker=t, weight=w, name=None) for t, w in pairs]


def sentiment(ticker, relevant=True, bull=0.0, neu=1.0, bear=0.0, reason=""):
    return HoldingSentiment(
        ticker=ticker, relevant=relevant, bullish=bull, neutral=neu, bearish=bear, reason=reason
    )


class TestNormalizeWeights:
    def test_weights_summing_to_100_are_unchanged(self):
        weights, adjusted = normalize_weights([HoldingIn(ticker="BHP", weight=40), HoldingIn(ticker="CBA", weight=60)])
        assert weights == pytest.approx([0.4, 0.6])
        assert adjusted is False

    def test_weights_not_summing_to_100_are_scaled(self):
        weights, adjusted = normalize_weights([HoldingIn(ticker="BHP", weight=30), HoldingIn(ticker="CBA", weight=60)])
        assert weights == pytest.approx([1 / 3, 2 / 3])
        assert adjusted is True

    def test_tiny_rounding_drift_is_not_flagged(self):
        _, adjusted = normalize_weights([HoldingIn(ticker=t, weight=33.33) for t in ("A", "B", "C")])
        assert adjusted is False

    @pytest.mark.parametrize("weights", [[0.35, 19.58, 79.57], [0.01, 8.56, 91.93]])
    def test_totals_of_exactly_99_5_or_100_5_are_not_flagged(self, weights):
        # Summed as floats these come to 99.49999999999999 and 100.50000000000001.
        _, adjusted = normalize_weights([HoldingIn(ticker=t, weight=w) for t, w in zip("ABC", weights)])
        assert adjusted is False


class TestScore:
    @pytest.mark.parametrize(
        "bull,bear,expected",
        [(0, 0, 50), (1, 0, 100), (0, 1, 0), (0.09, 0.71, 19), (0.5, 0.25, 63)],
    )
    def test_score_from_probs(self, bull, bear, expected):
        assert score_from_probs(bull, bear) == expected

    @pytest.mark.parametrize(
        "bull,bear,expected,label",
        [
            (0.21, 0, 61, "Bullish"),  # 60.5
            (0.61, 0, 81, "Strongly bullish"),  # 80.5
            (0.03, 0.42, 31, "Bearish"),  # 30.5
            (0, 0.21, 40, "Neutral"),  # 39.5
            (0, 0.61, 20, "Bearish"),  # 19.5
            (0, 0.55, 23, "Bearish"),  # 22.5, which floats compute as 22.4999...
        ],
    )
    def test_halves_round_up(self, bull, bear, expected, label):
        assert score_from_probs(bull, bear) == expected
        assert label_for(score_from_probs(bull, bear)) == label

    @pytest.mark.parametrize(
        "score,label",
        [
            (0, "Strongly bearish"),
            (19, "Strongly bearish"),
            (20, "Bearish"),
            (39, "Bearish"),
            (40, "Neutral"),
            (60, "Neutral"),
            (61, "Bullish"),
            (80, "Bullish"),
            (81, "Strongly bullish"),
            (100, "Strongly bullish"),
        ],
    )
    def test_label_boundaries(self, score, label):
        assert label_for(score) == label


class TestAggregate:
    def test_unrelated_holdings_are_excluded_and_weights_redistributed(self):
        holdings = resolved(("BHP", 0.4), ("CBA", 0.3), ("CSL", 0.3))
        result = EngineResult(
            per_holding=[
                sentiment("BHP", bull=0.09, neu=0.20, bear=0.71, reason="Iron ore slump"),
                sentiment("CBA", relevant=False),
                sentiment("CSL", relevant=False),
            ]
        )
        out = aggregate("finbert", holdings, result)

        assert out.status == "ok"
        assert out.score == 19
        assert out.label == "Strongly bearish"
        assert out.bearish == pytest.approx(0.71)
        assert out.exposure == pytest.approx(0.4)
        bhp, cba, _ = out.holdings
        assert bhp.effective_weight == pytest.approx(1.0)
        assert bhp.score == 19
        assert cba.relevant is False and cba.effective_weight == 0 and cba.score is None

    def test_weighted_average_of_two_related_holdings(self):
        holdings = resolved(("BHP", 0.5), ("RIO", 0.25), ("CBA", 0.25))
        result = EngineResult(
            per_holding=[
                sentiment("BHP", bull=0.0, neu=0.0, bear=1.0),
                sentiment("RIO", bull=1.0, neu=0.0, bear=0.0),
                sentiment("CBA", relevant=False),
            ]
        )
        out = aggregate("claude", holdings, result)

        # BHP gets 2/3 of the related weight, RIO 1/3.
        assert out.bearish == pytest.approx(2 / 3)
        assert out.bullish == pytest.approx(1 / 3)
        assert out.bullish + out.neutral + out.bearish == pytest.approx(1.0)
        assert out.score == 33
        assert out.exposure == pytest.approx(0.75)

    def test_no_related_holdings_returns_unrelated(self):
        holdings = resolved(("BHP", 0.5), ("CBA", 0.5))
        result = EngineResult(per_holding=[sentiment("BHP", relevant=False), sentiment("CBA", relevant=False)])
        out = aggregate("finbert", holdings, result)

        assert out.status == "unrelated"
        assert out.score is None and out.label is None
        assert out.exposure == 0

    def test_holding_missing_from_engine_output_counts_as_unrelated(self):
        holdings = resolved(("BHP", 0.5), ("CBA", 0.5))
        result = EngineResult(per_holding=[sentiment("BHP", bull=1.0, neu=0.0)])
        out = aggregate("claude", holdings, result)

        assert out.score == 100
        assert out.holdings[1].relevant is False
        assert out.holdings[1].assessed is False

    def test_skipped_holding_is_marked_and_left_out_of_the_score(self):
        holdings = resolved(("BHP", 0.5), ("CBA", 0.5))
        skipped = HoldingSentiment(ticker="CBA", relevant=False, assessed=False)
        out = aggregate("claude", holdings, EngineResult(per_holding=[sentiment("BHP", bull=1.0, neu=0.0), skipped]))

        bhp, cba = out.holdings
        assert bhp.assessed is True
        assert cba.assessed is False and cba.effective_weight == 0
        assert out.score == 100
        assert out.exposure == pytest.approx(0.5)

    def test_engine_extras_are_passed_through(self):
        holdings = resolved(("BHP", 1.0))
        result = EngineResult(
            per_holding=[sentiment("BHP", bull=1.0, neu=0.0)],
            summary="Good for miners.",
            key_points=["Prices up"],
            time_horizon=["short"],
            risks=["Demand may fade"],
            watch_items=["China PMI"],
        )
        out = aggregate("claude", holdings, result)

        assert out.summary == "Good for miners."
        assert out.key_points == ["Prices up"]
        assert out.time_horizon == ["short"]
        assert out.risks == ["Demand may fade"]
        assert out.watch_items == ["China PMI"]
