import asyncio
import importlib

import httpx
import pytest
from fastapi.testclient import TestClient

from app import main
from app.limits import AnalysisSlots, Busy, SlidingWindow
from app.models import EngineResult, HoldingSentiment

SITE = "https://portfolio-news.pages.dev"
NEWS = "BHP shares slumped 4% after the miner cut its iron ore production guidance for the year."
BODY = {"holdings": [{"ticker": "BHP", "weight": 100}], "news": NEWS, "engines": ["finbert"]}


class StubEngine:
    name = "finbert"

    def status(self):
        return "ready"

    async def analyze(self, news, holdings):
        return EngineResult(per_holding=[HoldingSentiment(ticker=h.ticker, relevant=False) for h in holdings])


@pytest.fixture
def client(monkeypatch):
    """The real app with CORS on for SITE and a stub engine, rebuilt so limits start from zero."""
    monkeypatch.setenv("ALLOWED_ORIGINS", SITE)
    app = importlib.reload(main).app
    app.state.engines = {"finbert": StubEngine()}
    with TestClient(app) as c:
        yield c
    monkeypatch.delenv("ALLOWED_ORIGINS")
    importlib.reload(main)


def test_the_eleventh_analysis_in_a_minute_is_refused_with_a_readable_reason(client):
    for _ in range(10):
        assert client.post("/api/analyze", json=BODY).status_code == 200
    res = client.post("/api/analyze", json=BODY, headers={"Origin": SITE})
    assert res.status_code == 429
    assert res.json() == {"detail": "Too many requests. Try again in a minute."}
    assert 1 <= int(res.headers["retry-after"]) <= 60
    # The frontend is on another site, so without this the browser would hide the reason.
    assert res.headers["access-control-allow-origin"] == SITE


def test_the_hourly_limit_says_how_many_minutes_to_wait(client):
    clock = [0.0]
    client.app.state.limits["/api/analyze"] = SlidingWindow([(10, 60), (60, 3600)], lambda: clock[0])
    for _ in range(60):
        assert client.post("/api/analyze", json=BODY).status_code == 200
        clock[0] += 7  # one every 7 seconds stays under 10 a minute
    res = client.post("/api/analyze", json=BODY)
    assert res.status_code == 429
    assert res.json() == {"detail": "Too many requests. Try again in 53 minutes."}


def test_article_fetches_are_limited_too(client, monkeypatch):
    async def fake_fetch(url):
        raise main.ArticleError("That address isn't allowed.")

    monkeypatch.setattr(main, "fetch_article", fake_fetch)
    codes = [client.post("/api/article", json={"url": "https://news.example/a"}).status_code for _ in range(11)]
    assert codes == [422] * 10 + [429]


def test_ticker_search_allows_fast_typing(client):
    codes = [client.get("/api/tickers?q=B").status_code for _ in range(121)]
    assert codes.count(200) == 120 and codes[-1] == 429


def test_the_health_check_is_never_limited(client):
    assert {client.get("/api/health").status_code for _ in range(300)} == {200}


def test_visitors_behind_the_hosts_proxy_are_counted_separately(client):
    client.app.state.proxy_hops = 1
    for _ in range(10):
        client.post("/api/analyze", json=BODY, headers={"X-Forwarded-For": "203.0.113.5"})
    assert client.post("/api/analyze", json=BODY, headers={"X-Forwarded-For": "203.0.113.5"}).status_code == 429
    assert client.post("/api/analyze", json=BODY, headers={"X-Forwarded-For": "198.51.100.7"}).status_code == 200


def test_a_busy_server_says_so(client):
    class Full(AnalysisSlots):
        def take(self):
            raise Busy

    client.app.state.analysis_slots = Full()
    res = client.post("/api/analyze", json=BODY, headers={"Origin": SITE})
    assert res.status_code == 503
    assert res.json() == {"detail": "The server is busy. Try again in a minute."}
    assert res.headers["retry-after"] == "60"
    assert res.headers["access-control-allow-origin"] == SITE


def test_warns_once_when_a_proxy_is_in_front_but_hops_is_not_set(client, caplog):
    # Every visitor then shares the proxy's address and one quota, so the log has to say why.
    for ip in ("203.0.113.5", "198.51.100.7"):
        client.post("/api/analyze", json=BODY, headers={"X-Forwarded-For": ip})
    warnings = [r for r in caplog.records if "TRUSTED_PROXY_HOPS" in r.getMessage()]
    assert [r.levelname for r in warnings] == ["WARNING"]


def test_no_proxy_warning_without_the_header_or_once_hops_is_set(client, caplog):
    client.post("/api/analyze", json=BODY)
    client.app.state.proxy_hops = 1
    client.post("/api/analyze", json=BODY, headers={"X-Forwarded-For": "203.0.113.5"})
    assert not [r for r in caplog.records if "TRUSTED_PROXY_HOPS" in r.getMessage()]


def test_a_busy_reply_does_not_use_up_the_visitors_quota(client):
    real = client.app.state.analysis_slots

    class Full(AnalysisSlots):
        def take(self):
            raise Busy

    client.app.state.analysis_slots = Full()
    assert {client.post("/api/analyze", json=BODY).status_code for _ in range(10)} == {503}
    client.app.state.analysis_slots = real
    assert client.post("/api/analyze", json=BODY).status_code == 200


def test_invalid_requests_do_not_use_up_the_visitors_quota(client):
    assert {client.post("/api/analyze", json={**BODY, "engines": []}).status_code for _ in range(10)} == {422}
    assert client.post("/api/analyze", json=BODY).status_code == 200


def test_requests_that_crash_do_not_use_up_the_visitors_quota(client, monkeypatch):
    calls = []

    async def fetch(url):
        calls.append(url)
        if len(calls) <= 10:
            raise RuntimeError("boom")
        raise main.ArticleError("That address isn't allowed.")

    monkeypatch.setattr(main, "fetch_article", fetch)
    crashing = TestClient(client.app, raise_server_exceptions=False)
    assert {crashing.post("/api/article", json={"url": "https://news.example/a"}).status_code for _ in range(10)} == {500}
    assert crashing.post("/api/article", json={"url": "https://news.example/a"}).status_code == 422


def test_a_proxy_that_adds_its_own_forwarded_for_line_still_identifies_the_visitor(client):
    # Some proxies keep the visitor's X-Forwarded-For line and add another; the address the
    # proxy saw is in the last line, and the visitor can write anything in the first.
    client.app.state.proxy_hops = 1
    codes = [
        client.post(
            "/api/analyze",
            json=BODY,
            headers=[("X-Forwarded-For", f"198.51.100.{i}"), ("X-Forwarded-For", "203.0.113.5")],
        ).status_code
        for i in range(11)
    ]
    assert codes == [200] * 10 + [429]


def test_turning_away_an_old_request_does_not_free_a_newer_ones_place(client, monkeypatch):
    # A request is counted when it arrives. One whose body only finishes a minute later and
    # turns out invalid must give back its own place, not one from the newer minute.
    async def refuse(url):
        raise main.ArticleError("That address isn't allowed.")  # a real fetch attempt, so it counts

    monkeypatch.setattr(main, "fetch_article", refuse)
    clock = [0.0]
    client.app.state.limits["/api/article"] = SlidingWindow([(10, 60), (60, 3600)], lambda: clock[0])

    async def scenario():
        reading, finish = asyncio.Event(), asyncio.Event()

        async def slow_invalid_body():
            yield b'{"url": '
            reading.set()  # the app is reading the body, so the request has been counted
            await finish.wait()
            yield b'""}'

        transport = httpx.ASGITransport(app=client.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            old = asyncio.create_task(
                c.post("/api/article", content=slow_invalid_body(), headers={"Content-Type": "application/json"})
            )
            await reading.wait()
            clock[0] = 61
            fetch = {"url": "https://news.example/a"}
            codes = [(await c.post("/api/article", json=fetch)).status_code for _ in range(10)]
            finish.set()
            old_code = (await old).status_code
            next_code = (await c.post("/api/article", json=fetch)).status_code
            return codes, old_code, next_code

    assert asyncio.run(scenario()) == ([422] * 10, 422, 429)
