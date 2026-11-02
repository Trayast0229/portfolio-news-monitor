import importlib.util

import pytest

from app.asx import resolve
from app.engines.base import EngineError
from app.engines.finbert_engine import FinbertEngine, split_sentences
from app.models import HoldingIn


def fake_classifier(sentences):
    """Stands in for the FinBERT pipeline: 'fell' is negative, 'rose' positive."""
    out = []
    for s in sentences:
        if "fell" in s:
            scores = {"negative": 0.8, "neutral": 0.15, "positive": 0.05}
        elif "rose" in s:
            scores = {"negative": 0.1, "neutral": 0.2, "positive": 0.7}
        else:
            scores = {"negative": 0.1, "neutral": 0.8, "positive": 0.1}
        out.append([{"label": k, "score": v} for k, v in scores.items()])
    return out


def holdings(*tickers):
    return resolve([HoldingIn(ticker=t, weight=1) for t in tickers], [1 / len(tickers)] * len(tickers))


def test_split_sentences():
    text = "BHP fell 3%. Iron ore slumped!\nAnalysts were cautious? Yes."
    assert split_sentences(text) == ["BHP fell 3%.", "Iron ore slumped!", "Analysts were cautious?", "Yes."]


@pytest.mark.parametrize(
    "sentence",
    [
        "Wesfarmers Ltd. CEO Rob Scott said sales fell.",
        "Shares in BHP rose after U.S. President Trump eased tariffs.",
        "Analysts at J.P. Morgan cut BHP to underweight.",
        "Mr. Smith said BHP output fell.",
        "The St. George Bank unit of Westpac grew.",
    ],
)
def test_abbreviations_do_not_end_a_sentence(sentence):
    assert split_sentences(sentence) == [sentence]


def test_curly_quotes_around_a_sentence_end():
    assert split_sentences("BHP cut jobs. “We are disappointed,” the union said.") == [
        "BHP cut jobs.",
        "“We are disappointed,” the union said.",
    ]
    assert split_sentences("He said “profit fell.” BHP shares dropped.") == ["He said “profit fell.”", "BHP shares dropped."]


async def test_company_named_with_ltd_keeps_its_sentence():
    engine = FinbertEngine(classifier=fake_classifier)
    result = await engine.analyze("Wesfarmers Ltd. CEO Rob Scott said sales fell sharply.", holdings("WES"))
    assert result.per_holding[0].bearish == pytest.approx(0.8)


async def test_only_mentioned_holdings_are_relevant():
    engine = FinbertEngine(classifier=fake_classifier)
    result = await engine.analyze("BHP shares fell sharply on Monday. The weather was mild.", holdings("BHP", "CBA"))

    bhp, cba = result.per_holding
    assert bhp.relevant is True
    assert bhp.bearish == pytest.approx(0.8)
    assert bhp.bullish + bhp.neutral + bhp.bearish == pytest.approx(1.0)
    assert "BHP shares fell sharply" in bhp.reason
    assert cba.relevant is False


async def test_probabilities_are_averaged_across_mentioning_sentences():
    engine = FinbertEngine(classifier=fake_classifier)
    news = "Woolworths shares fell after the result. Later, Woolworths rose on buybacks."
    (wow,) = (await engine.analyze(news, holdings("WOW"))).per_holding

    assert wow.bearish == pytest.approx((0.8 + 0.1) / 2)
    assert wow.bullish == pytest.approx((0.05 + 0.7) / 2)


async def test_reason_quotes_at_most_two_sentences():
    engine = FinbertEngine(classifier=fake_classifier)
    news = "BHP rose. BHP rose again. BHP rose a third time."
    (bhp,) = (await engine.analyze(news, holdings("BHP"))).per_holding
    assert bhp.reason.count("BHP") == 2


async def test_each_sentence_is_classified_once():
    calls = []

    def counting(sentences):
        calls.append(list(sentences))
        return fake_classifier(sentences)

    engine = FinbertEngine(classifier=counting)
    await engine.analyze("BHP and Rio Tinto fell. Nothing else happened.", holdings("BHP", "RIO"))
    assert calls == [["BHP and Rio Tinto fell."]]


@pytest.mark.parametrize(
    "news",
    [
        "BHP shares rose to a record, while CBA shares fell after a warning.",
        "BHP shares rose to a record but CBA shares fell after a warning.",
        "BHP shares rose to a record; CBA shares fell after a warning.",
    ],
)
async def test_each_company_is_scored_on_its_own_clause(news):
    engine = FinbertEngine(classifier=fake_classifier)
    bhp, cba = (await engine.analyze(news, holdings("BHP", "CBA"))).per_holding

    assert bhp.bullish == pytest.approx(0.7)
    assert cba.bearish == pytest.approx(0.8)
    assert "CBA" not in bhp.reason


async def test_companies_in_the_same_clause_share_it():
    engine = FinbertEngine(classifier=fake_classifier)
    bhp, rio = (await engine.analyze("BHP and Rio Tinto fell, while gold rose.", holdings("BHP", "RIO"))).per_holding
    assert bhp.bearish == pytest.approx(0.8)
    assert rio.bearish == pytest.approx(0.8)


async def test_reason_warns_when_a_sentence_could_not_be_split():
    engine = FinbertEngine(classifier=fake_classifier)
    bhp, cba, csl = (await engine.analyze("BHP rose and CBA fell. CSL was flat.", holdings("BHP", "CBA", "CSL"))).per_holding

    assert "also names CBA" in bhp.reason
    assert "also names BHP" in cba.reason
    assert "also names" not in csl.reason


@pytest.mark.parametrize(
    "news",
    ["BHP shares rose, while CBA shares fell.", "BHP shares rose. CBA shares fell."],
)
async def test_no_warning_when_each_company_has_its_own_text(news):
    engine = FinbertEngine(classifier=fake_classifier)
    bhp, cba = (await engine.analyze(news, holdings("BHP", "CBA"))).per_holding
    assert "also names" not in bhp.reason
    assert "also names" not in cba.reason


async def test_sentence_naming_one_company_is_not_split():
    calls = []

    def counting(sentences):
        calls.append(list(sentences))
        return fake_classifier(sentences)

    engine = FinbertEngine(classifier=counting)
    await engine.analyze("BHP fell, while the broader market rose.", holdings("BHP", "CBA"))
    assert calls == [["BHP fell, while the broader market rose."]]


async def test_long_sentence_is_cut_down_around_the_mention():
    # FinBERT reads only the first 512 tokens, so a mention near the end of a
    # long run-on sentence would be cut off before the model saw it.
    calls = []

    def counting(sentences):
        calls.append(list(sentences))
        return fake_classifier(sentences)

    filler = " ".join(["the group discussed operations in several regions"] * 60)
    engine = FinbertEngine(classifier=counting)
    (bhp,) = (await engine.analyze(f"{filler} and BHP shares fell sharply", holdings("BHP"))).per_holding

    (scored,) = calls[0]
    assert len(scored.split()) <= 200
    assert scored.endswith("BHP shares fell sharply")
    assert bhp.bearish == pytest.approx(0.8)


async def test_no_mentions_skips_the_model():
    def boom(_):
        raise AssertionError("classifier should not run")

    engine = FinbertEngine(classifier=boom)
    result = await engine.analyze("Markets were quiet across Asia today.", holdings("BHP"))
    assert result.per_holding[0].relevant is False


def test_status_reports_loaded_classifier():
    assert FinbertEngine(classifier=fake_classifier).status() == "ready"


async def test_missing_finbert_is_an_error_even_when_no_company_is_named(monkeypatch):
    # Otherwise the app shows "Not related", as if FinBERT had read the story.
    real = importlib.util.find_spec
    monkeypatch.setattr(importlib.util, "find_spec", lambda name, *a: None if name == "torch" else real(name, *a))
    engine = FinbertEngine()
    assert engine.status() == "unavailable"
    with pytest.raises(EngineError, match="isn't installed"):
        await engine.analyze("Iron ore prices fell sharply overnight on weaker Chinese demand.", holdings("BHP", "CBA"))
