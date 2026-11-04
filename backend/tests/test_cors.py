import importlib

import pytest
from fastapi.testclient import TestClient

from app import main
from app.main import cors_origins

SITE = "https://portfolio-news.pages.dev"


def test_origins_are_read_as_a_comma_separated_list():
    assert cors_origins(f" {SITE}/ , http://localhost:4173 ") == [SITE, "http://localhost:4173"]


def test_no_origins_means_no_cross_site_access():
    assert cors_origins(None) == []
    assert cors_origins("  ") == []


@pytest.mark.parametrize("raw", ["*", "portfolio-news.pages.dev", f"{SITE}/app"])
def test_origins_that_would_never_match_or_match_everyone_stop_the_server(raw):
    with pytest.raises(ValueError, match="ALLOWED_ORIGINS"):
        cors_origins(raw)


@pytest.fixture
def app_with(monkeypatch):
    """Rebuilds the real app with ALLOWED_ORIGINS set, then restores the default app."""

    def build(origins, **client_options):
        if origins is None:
            monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)
        else:
            monkeypatch.setenv("ALLOWED_ORIGINS", origins)
        return TestClient(importlib.reload(main).app, **client_options)

    yield build
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)
    importlib.reload(main)


def preflight(client, origin, method="POST"):
    return client.options(
        "/api/analyze",
        headers={"Origin": origin, "Access-Control-Request-Method": method, "Access-Control-Request-Headers": "content-type"},
    )


def test_the_frontend_site_may_call_the_api(app_with):
    client = app_with(SITE)
    res = preflight(client, SITE)
    assert res.status_code == 200
    assert res.headers["access-control-allow-origin"] == SITE
    assert client.get("/api/tickers?q=BHP", headers={"Origin": SITE}).headers["access-control-allow-origin"] == SITE


def test_other_sites_are_not_allowed(app_with):
    client = app_with(SITE)
    assert "access-control-allow-origin" not in preflight(client, "https://evil.example").headers
    assert "access-control-allow-origin" not in client.get("/api/tickers?q=BHP", headers={"Origin": "https://evil.example"}).headers


def test_only_the_methods_the_app_uses_are_allowed(app_with):
    assert preflight(app_with(SITE), SITE, method="DELETE").status_code == 400


def test_without_the_setting_no_site_gets_cross_site_access(app_with):
    client = app_with(None)
    assert "access-control-allow-origin" not in client.get("/api/tickers?q=BHP", headers={"Origin": SITE}).headers


def test_a_crash_still_reaches_the_frontend_as_a_readable_error(app_with, monkeypatch):
    # Without the CORS header the browser hides the reply, and the visitor is told the server is unreachable.
    client = app_with(SITE, raise_server_exceptions=False)

    async def broken_fetch(url):
        raise RuntimeError("boom")

    monkeypatch.setattr(main, "fetch_article", broken_fetch)
    res = client.post("/api/article", json={"url": "https://example.com/a"}, headers={"Origin": SITE})
    assert res.status_code == 500
    assert res.headers.get("access-control-allow-origin") == SITE
    assert res.json() == {"detail": "Something went wrong on our side. Try again in a moment."}
