"""Fetch a news page and pull out its headline and article text.

The server fetches on the user's behalf, so it only follows public web
addresses on the usual ports and re-checks every redirect. (A host could
still change its DNS answer between our check and the connection; that's an
acceptable risk for this app.)
"""

import asyncio
import ipaddress
import socket

import httpx
import trafilatura

from .models import Article

MAX_CHARS = 20_000  # same limit as AnalyzeRequest.news
MAX_BYTES = 3_000_000
MAX_REDIRECTS = 5
TIMEOUT = httpx.Timeout(10.0)  # per step, so a site that trickles data never hits it
TOTAL_SECONDS = 20  # the whole fetch, including DNS lookups and redirects
USER_AGENT = "Mozilla/5.0 (compatible; PortfolioNewsMonitor/0.1)"
MIN_TEXT = 50  # AnalyzeRequest.news needs at least this many characters


class ArticleError(Exception):
    """A failure whose message can be shown to the user as is."""


NOT_A_LINK = "Enter a full web address starting with http:// or https://."
NOT_ALLOWED = "That address isn't allowed. Use a link to a public news site."
BLOCKED = "This site needs a subscription or blocks automatic access. Copy the article text and paste it instead."
NOT_FOUND = "We couldn't find that page. Check the link."
NO_RESPONSE = "The site didn't respond. Try again, or paste the text instead."
TOO_SLOW = "The site took too long to load. Try again, or paste the text instead."
NOT_HTML = "That link isn't a news page we can read. Paste the text instead."
NO_TEXT = (
    "We couldn't find the article text. It may be behind a paywall or loaded by JavaScript. Paste the text instead."
)


async def fetch_article(url: str, *, client: httpx.AsyncClient | None = None, resolve=socket.getaddrinfo) -> Article:
    try:
        async with asyncio.timeout(TOTAL_SECONDS):
            if client is None:
                async with httpx.AsyncClient(timeout=TIMEOUT, headers={"user-agent": USER_AGENT}) as own:
                    return await _follow(url, own, resolve)
            return await _follow(url, client, resolve)
    except TimeoutError as exc:
        raise ArticleError(TOO_SLOW) from exc


async def _follow(url: str, client: httpx.AsyncClient, resolve) -> Article:
    current = _parse(url)
    for _ in range(MAX_REDIRECTS + 1):
        await _check_public(current, resolve)
        try:
            async with client.stream("GET", current, headers={"user-agent": USER_AGENT}, timeout=TIMEOUT) as res:
                if res.is_redirect and "location" in res.headers:
                    current = _parse(str(current.join(res.headers["location"])))
                    continue
                _check_response(res)
                body = await _read_limited(res)
        except httpx.TransportError as exc:
            raise ArticleError(NO_RESPONSE) from exc
        return _extract(body, str(current))
    raise ArticleError("That link redirects too many times. Try the article's own address.")


def _parse(url: str) -> httpx.URL:
    try:
        parsed = httpx.URL(url.strip())
    except httpx.InvalidURL as exc:
        raise ArticleError(NOT_A_LINK) from exc
    if parsed.scheme not in ("http", "https") or not parsed.host:
        raise ArticleError(NOT_A_LINK)
    return parsed


async def _check_public(url: httpx.URL, resolve) -> None:
    if url.port not in (None, 80, 443):
        raise ArticleError(NOT_ALLOWED)
    try:
        infos = await asyncio.to_thread(resolve, url.host, url.port or 443, type=socket.SOCK_STREAM)
    except (socket.gaierror, UnicodeError) as exc:
        raise ArticleError("We couldn't find that site. Check the link.") from exc
    for info in infos:
        if not ipaddress.ip_address(info[4][0]).is_global:
            raise ArticleError(NOT_ALLOWED)


def _check_response(res: httpx.Response) -> None:
    if res.status_code in (401, 402, 403, 429):
        raise ArticleError(BLOCKED)
    if res.status_code in (404, 410):
        raise ArticleError(NOT_FOUND)
    if res.status_code >= 400:
        raise ArticleError(f"The site returned an error ({res.status_code}). Try again, or paste the text instead.")
    if "html" not in res.headers.get("content-type", ""):
        raise ArticleError(NOT_HTML)
    if int(res.headers.get("content-length") or 0) > MAX_BYTES:
        raise ArticleError(NOT_HTML)


async def _read_limited(res: httpx.Response) -> bytes:
    body = bytearray()
    async for chunk in res.aiter_bytes():
        body += chunk
        if len(body) > MAX_BYTES:
            raise ArticleError(NOT_HTML)
    return bytes(body)


def _extract(body: bytes, url: str) -> Article:
    doc = trafilatura.bare_extraction(body, url=url, with_metadata=True, include_comments=False)
    text = (doc.text or "").strip() if doc else ""
    if len(text) < MIN_TEXT:
        raise ArticleError(NO_TEXT)
    title = (doc.title or "").strip() or None
    if title and not text.startswith(title):
        text = f"{title}\n\n{text}"
    truncated = len(text) > MAX_CHARS
    return Article(url=url, title=title, text=text[:MAX_CHARS].rstrip(), truncated=truncated)
