import pytest
from fastapi.testclient import TestClient

from app import main
from app.article import ArticleError
from app.engines.base import EngineError
from app.main import app
from app.models import Article, EngineResult, HoldingSentiment

NEWS = "BHP shares slumped 4% after the miner cut its iron ore production guidance for the year."


class StubEngine:
    def __init__(self, name, per_holding=None, error=None):
        self.name = name
        self.per_holding = per_holding or {}
        self.error = error
        self.seen = None

    def status(self):
        return "ready"

    async def analyze(self, news, holdings):
        self.seen = holdings
        if self.error:
            raise self.error
        return EngineResult(
            per_holding=[
                self.per_holding.get(h.ticker, HoldingSentiment(ticker=h.ticker, relevant=False)) for h in holdings
            ]
        )


@pytest.fixture
def client():
    bearish_bhp = {"BHP": HoldingSentiment(ticker="BHP", relevant=True, bullish=0.1, neutral=0.2, bearish=0.7)}
    app.state.engines = {
        "finbert": StubEngine("finbert", bearish_bhp),
        "claude": StubEngine("claude", error=EngineError("Claude isn't set up.")),
    }
    with TestClient(app) as c:
        yield c
    del app.state.engines


def body(**overrides):
    b = {
        "holdings": [{"ticker": "BHP", "weight": 40}, {"ticker": "CBA", "weight": 30}, {"ticker": "CSL", "weight": 30}],
        "news": NEWS,
        "engines": ["finbert"],
    }
    b.update(overrides)
    return b


def test_health_lists_engines(client):
    assert client.get("/api/health").json() == {"engines": {"finbert": "ready", "claude": "ready"}}


def test_ticker_search(client):
    results = client.get("/api/tickers", params={"q": "CBA"}).json()
    assert results[0] == {"ticker": "CBA", "name": "Commonwealth Bank of Australia"}


def test_analyze_returns_portfolio_verdict(client):
    res = client.post("/api/analyze", json=body())
    assert res.status_code == 200
    data = res.json()
    assert data["weights_adjusted"] is False
    (r,) = data["results"]
    assert r["engine"] == "finbert"
    assert r["status"] == "ok"
    assert r["score"] == 20
    assert r["label"] == "Bearish"
    assert r["exposure"] == pytest.approx(0.4)
    assert [h["relevant"] for h in r["holdings"]] == [True, False, False]
    assert r["holdings"][0]["name"] == "BHP Group Limited"


def test_weights_are_normalized_and_flagged(client):
    res = client.post("/api/analyze", json=body(holdings=[{"ticker": "BHP", "weight": 45}, {"ticker": "CBA", "weight": 45}]))
    data = res.json()
    assert data["weights_adjusted"] is True
    assert data["results"][0]["exposure"] == pytest.approx(0.5)


def test_one_engine_failing_does_not_break_the_other(client):
    data = client.post("/api/analyze", json=body(engines=["finbert", "claude"])).json()
    finbert, claude = data["results"]
    assert finbert["status"] == "ok"
    assert claude == {**claude, "status": "error", "error": "Claude isn't set up."}


def test_tickers_are_cleaned(client):
    data = client.post("/api/analyze", json=body(holdings=[{"ticker": " bhp.ax ", "weight": 100}])).json()
    assert data["results"][0]["holdings"][0]["ticker"] == "BHP"


@pytest.mark.parametrize(
    "overrides",
    [
        {"news": "too short"},
        {"holdings": []},
        {"engines": []},
        {"engines": ["gpt"]},
        {"holdings": [{"ticker": "BHP", "weight": 50}, {"ticker": "BHP", "weight": 50}]},
        {"holdings": [{"ticker": "BHP", "weight": 0}]},
        {"holdings": [{"ticker": "BH P", "weight": 10}]},
    ],
)
def test_invalid_requests_are_rejected(client, overrides):
    assert client.post("/api/analyze", json=body(**overrides)).status_code == 422


def test_article_returns_the_fetched_text(client, monkeypatch):
    async def fake_fetch(url):
        return Article(url=url, title="BHP cuts guidance", text="BHP cuts guidance\n\n" + NEWS, truncated=False)

    monkeypatch.setattr(main, "fetch_article", fake_fetch)
    res = client.post("/api/article", json={"url": "https://news.example/bhp"})
    assert res.status_code == 200
    assert res.json() == {
        "url": "https://news.example/bhp",
        "title": "BHP cuts guidance",
        "text": "BHP cuts guidance\n\n" + NEWS,
        "truncated": False,
    }


def test_article_errors_come_back_as_readable_messages(client, monkeypatch):
    async def fake_fetch(url):
        raise ArticleError("This site needs a subscription.")

    monkeypatch.setattr(main, "fetch_article", fake_fetch)
    res = client.post("/api/article", json={"url": "https://news.example/bhp"})
    assert res.status_code == 422
    assert res.json() == {"detail": "This site needs a subscription."}


def test_unexpected_errors_say_the_server_failed_not_that_it_is_off(monkeypatch):
    async def broken_fetch(url):
        raise ValueError("bug")

    monkeypatch.setattr(main, "fetch_article", broken_fetch)
    res = TestClient(app, raise_server_exceptions=False).post("/api/article", json={"url": "https://news.example/bhp"})
    assert res.status_code == 500
    assert res.json() == {"detail": "Something went wrong on our side. Try again in a moment."}


@pytest.mark.parametrize("url", ["", "https://news.example/" + "a" * 2000])
def test_article_rejects_empty_or_huge_links(client, url):
    assert client.post("/api/article", json={"url": url}).status_code == 422
