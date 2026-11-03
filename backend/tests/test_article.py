import asyncio
import socket
import time

import httpx
import pytest

from app import article
from app.article import ArticleError, fetch_article

ARTICLE_HTML = """<html><head><title>BHP cuts guidance | Example News</title></head>
<body><nav>Home Markets Sport</nav><article><h1>BHP cuts iron ore guidance</h1>
<p>BHP Group shares fell 4 per cent on Tuesday after the miner cut its iron ore production guidance for the year.</p>
<p>The company blamed wet weather in the Pilbara and maintenance delays at Port Hedland, analysts said.</p>
</article><footer>Copyright 2026. Subscribe now.</footer></body></html>"""

HOSTS = {
    "news.example": "93.184.216.34",
    "other.example": "93.184.216.35",
    "internal.example": "10.0.0.5",
    "metadata.example": "169.254.169.254",
    "localhost": "127.0.0.1",
}


def fake_resolve(host, port, *args, **kwargs):
    # Like socket.getaddrinfo: IP literals resolve to themselves.
    if host.replace(".", "").isdigit():
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (host, port))]
    if host not in HOSTS:
        raise socket.gaierror("unknown host")
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (HOSTS[host], port))]


def html(body=ARTICLE_HTML, status=200, **headers):
    return httpx.Response(status, content=body.encode(), headers={"content-type": "text/html; charset=utf-8", **headers})


async def fetch(url, handler):
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        return await fetch_article(url, client=client, resolve=fake_resolve)


async def fails_with(url, handler, words):
    with pytest.raises(ArticleError) as exc:
        await fetch(url, handler)
    assert words in str(exc.value)


# ---- Success -------------------------------------------------------------------


async def test_returns_title_and_article_text():
    result = await fetch("https://news.example/bhp", lambda req: html())
    assert result.title == "BHP cuts iron ore guidance"
    assert result.text.startswith("BHP cuts iron ore guidance\n")
    assert "wet weather in the Pilbara" in result.text
    assert "Subscribe now" not in result.text
    assert result.url == "https://news.example/bhp"
    assert result.truncated is False


async def test_does_not_repeat_the_title_when_the_text_starts_with_it():
    result = await fetch("https://news.example/bhp", lambda req: html())
    assert result.text.count("BHP cuts iron ore guidance") == 1


async def test_adds_the_title_when_the_text_lacks_it():
    page = ARTICLE_HTML.replace("<h1>BHP cuts iron ore guidance</h1>", "").replace(
        "<title>BHP cuts guidance | Example News</title>", '<meta property="og:title" content="Miner trims outlook">'
    )
    result = await fetch("https://news.example/bhp", lambda req: html(page))
    assert result.text.startswith("Miner trims outlook\n\nBHP Group shares fell")


async def test_cuts_long_articles_to_the_limit(monkeypatch):
    monkeypatch.setattr(article, "MAX_CHARS", 120)
    result = await fetch("https://news.example/bhp", lambda req: html())
    assert len(result.text) <= 120
    assert result.truncated is True


JAPANESE = "BHPの株価が上昇した。鉄鉱石の需要は強い。" * 3
FRENCH = "Nestlé café – crème brûlée BHP shares rose on Friday after the miner reported a record annual profit and lifted its dividend."
THAI = "BHP Group shares rose on Friday after the miner reported record annual profit and lifted its dividend. นักวิเคราะห์กล่าวว่าหุ้นขึ้น"
TURKISH = "BHP Group shares rose on Friday after the miner reported record annual profit. Analistler hisselerin yükseldiğini söyledi; şirket güçlü."
QUOTES = "The CEO called it “a great year” after BHP shares rose to a record on Friday, analysts said."


@pytest.mark.parametrize(
    ("text", "encoding", "content_type"),
    [
        (JAPANESE, "shift_jis", "text/html; charset=Shift_JIS"),
        (FRENCH, "windows-1252", "text/html; charset=windows-1252"),
        (THAI, "cp874", "text/html; charset=TIS-620"),
        (TURKISH, "cp1254", "text/html; charset=ISO-8859-9"),
        # Browsers read pages labelled ISO-8859-1 as windows-1252, which adds curly quotes.
        (QUOTES, "windows-1252", "text/html; charset=ISO-8859-1"),
    ],
)
async def test_reads_pages_in_the_encoding_the_site_declares(text, encoding, content_type):
    page = f"<html><head><title>Headline</title></head><body><article><p>{text}</p></article></body></html>"
    res = httpx.Response(200, content=page.encode(encoding), headers={"content-type": content_type})
    result = await fetch("https://news.example/bhp", lambda req: res)
    assert text.strip() in result.text


@pytest.mark.parametrize("charset", ["undefined", "unicode_escape"])
async def test_ignores_charsets_that_browsers_do_not_support(charset):
    page = f"<html><head><title>H</title></head><body><article><p>{QUOTES}</p></article></body></html>"
    res = httpx.Response(200, content=page.encode("windows-1252"), headers={"content-type": f"text/html; charset={charset}"})
    result = await fetch("https://news.example/bhp", lambda req: res)
    assert QUOTES in result.text


async def test_ignores_a_punycode_charset_without_stalling():
    # Python's punycode decoder slows down with length: a 1 MB page held the whole server for seconds.
    res = httpx.Response(200, content=b"a" * 1_000_000 + b"\xff", headers={"content-type": "text/html; charset=punycode"})
    start = time.perf_counter()
    with pytest.raises(ArticleError):
        await fetch("https://news.example/bhp", lambda req: res)
    assert time.perf_counter() - start < 2


async def test_trusts_the_page_over_the_header_when_they_disagree():
    # Old servers label every page ISO-8859-1; the page's own meta tag is the one written with the text.
    text = "必和必拓股價週五大漲，鐵礦砂需求強勁，公司前景看好。" * 2
    page = f'<html><head><meta charset="big5"><title>H</title></head><body><article><p>{text}</p></article></body></html>'
    res = httpx.Response(200, content=page.encode("big5"), headers={"content-type": "text/html; charset=ISO-8859-1"})
    result = await fetch("https://news.example/bhp", lambda req: res)
    assert text in result.text


async def test_reads_utf8_pages_as_utf8_even_when_labelled_otherwise():
    page = f"<html><body><article><p>{FRENCH}</p></article></body></html>"
    res = httpx.Response(200, content=page.encode(), headers={"content-type": "text/html; charset=ISO-8859-1"})
    result = await fetch("https://news.example/bhp", lambda req: res)
    assert FRENCH in result.text


async def test_follows_a_redirect_and_reports_the_final_address():
    def handler(req):
        if req.url.path == "/short":
            return httpx.Response(301, headers={"location": "https://other.example/full"})
        return html()

    result = await fetch("https://news.example/short", handler)
    assert result.url == "https://other.example/full"


async def test_sends_an_honest_user_agent():
    seen = {}

    def handler(req):
        seen["ua"] = req.headers["user-agent"]
        return html()

    await fetch("https://news.example/bhp", handler)
    assert "PortfolioNewsMonitor" in seen["ua"]


# ---- Addresses we refuse -----------------------------------------------------------


@pytest.mark.parametrize("url", ["ftp://news.example/a", "news.example/bhp", "javascript:alert(1)", "https://"])
async def test_rejects_addresses_that_are_not_web_links(url):
    await fails_with(url, lambda req: html(), "starting with http:// or https://")


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost:8000/api/health",
        "http://internal.example/",
        "http://metadata.example/latest/meta-data",
        "http://127.0.0.1/",
        "https://news.example:8443/bhp",
    ],
)
async def test_rejects_private_addresses_and_unusual_ports(url):
    await fails_with(url, lambda req: html(), "isn't allowed")


async def test_rejects_a_redirect_to_a_private_address():
    def handler(req):
        if req.url.host == "news.example":
            return httpx.Response(302, headers={"location": "http://internal.example/admin"})
        return html()

    await fails_with("https://news.example/bhp", handler, "isn't allowed")


async def test_gives_up_after_too_many_redirects():
    def handler(req):
        n = int(req.url.path.strip("/") or 0)
        return httpx.Response(302, headers={"location": f"/{n + 1}"})

    await fails_with("https://news.example/0", handler, "redirects too many times")


@pytest.mark.parametrize("location", ["ftp://files.example/story.html", "mailto:news@example.com"])
async def test_explains_a_redirect_to_an_address_we_cannot_open(location):
    redirect = lambda req: httpx.Response(302, headers={"location": location})
    await fails_with("https://news.example/bhp", redirect, "redirects to an address we can't open")


async def test_reports_an_unknown_host():
    await fails_with("https://nowhere.example/", lambda req: html(), "couldn't find that site")


# ---- Pages we can't read ------------------------------------------------------------


@pytest.mark.parametrize("status", [401, 402, 403, 429])
async def test_explains_paywalls_and_blocked_access(status):
    await fails_with("https://news.example/bhp", lambda req: html(status=status), "needs a subscription")


@pytest.mark.parametrize("status", [404, 410])
async def test_explains_missing_pages(status):
    await fails_with("https://news.example/bhp", lambda req: html(status=status), "couldn't find that page")


async def test_explains_other_server_errors():
    await fails_with("https://news.example/bhp", lambda req: html(status=503), "(503)")


@pytest.mark.parametrize("error", [httpx.ConnectTimeout("slow"), httpx.ReadTimeout("slow"), httpx.ConnectError("down")])
async def test_explains_sites_that_do_not_respond(error):
    def handler(req):
        raise error

    await fails_with("https://news.example/bhp", handler, "didn't respond")


async def test_rejects_pages_that_are_not_html():
    pdf = lambda req: httpx.Response(200, content=b"%PDF-1.7", headers={"content-type": "application/pdf"})
    await fails_with("https://news.example/report.pdf", pdf, "isn't a news page")


async def test_rejects_pages_that_are_too_big(monkeypatch):
    monkeypatch.setattr(article, "MAX_BYTES", 200)
    await fails_with("https://news.example/bhp", lambda req: html(), "isn't a news page")


async def test_gives_up_on_a_site_that_sends_a_little_at_a_time(monkeypatch):
    monkeypatch.setattr(article, "TOTAL_SECONDS", 0.2)

    async def trickle():
        while True:
            yield b"<p>"
            await asyncio.sleep(0.05)

    slow = lambda req: httpx.Response(200, headers={"content-type": "text/html"}, content=trickle())
    with pytest.raises(ArticleError) as exc:
        await asyncio.wait_for(fetch("https://news.example/bhp", slow), 2)
    assert "took too long" in str(exc.value)


async def test_explains_pages_without_article_text():
    teaser = "<html><body><p>Subscribe to read.</p></body></html>"
    await fails_with("https://news.example/bhp", lambda req: html(teaser), "couldn't find the article text")
