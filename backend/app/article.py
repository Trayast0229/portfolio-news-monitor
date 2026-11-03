"""Fetch a news page and pull out its headline and article text.

The server fetches on the user's behalf, so it only follows public web
addresses on the usual ports and re-checks every redirect. (A host could
still change its DNS answer between our check and the connection; that's an
acceptable risk for this app.)
"""

import asyncio
import codecs
import ipaddress
import re
import socket
import zlib

import httpx
import trafilatura

from .models import Article

MAX_CHARS = 20_000  # same limit as AnalyzeRequest.news
MAX_BYTES = 3_000_000
MAX_REDIRECTS = 5
TIMEOUT = httpx.Timeout(10.0)  # per step, so a site that trickles data never hits it
TOTAL_SECONDS = 20  # the whole fetch, including DNS lookups and redirects
USER_AGENT = "Mozilla/5.0 (compatible; PortfolioNewsMonitor/0.1)"
HEADERS = {"user-agent": USER_AGENT, "accept-encoding": "gzip, deflate"}  # the encodings _read_limited unpacks
MIN_TEXT = 50  # AnalyzeRequest.news needs at least this many characters
# The encodings browsers support (WHATWG Encoding Standard), keyed by Python's name for a
# label and mapped to the codec browsers really use for it. Any other label is ignored: the
# site picks it, and some Python codecs (punycode) take a minute on a large page.
WEB_ENCODINGS = {
    **{
        name: name
        for name in ["cp866", "koi8-r", "koi8-u", "mac-roman", "euc_jp", "iso2022_jp", "gb18030", "cp932", "cp949"]
        + ["big5hkscs", "utf-16", "utf-16-be", "utf-16-le"]
    },
    **{f"iso8859-{n}": f"iso8859-{n}" for n in (2, 3, 4, 5, 6, 7, 8, 10, 13, 14, 15, 16)},
    **{f"cp125{n}": f"cp125{n}" for n in range(9)},
    "iso8859-1": "cp1252",
    "iso8859-9": "cp1254",
    "ascii": "cp1252",
    "shift_jis": "cp932",
    "gb2312": "gb18030",
    "gbk": "gb18030",
    "big5": "big5hkscs",
    "euc_kr": "cp949",
    "tis-620": "cp874",  # Thai; Python doesn't know the "windows-874" label itself
    "iso8859-11": "cp874",
    "cp874": "cp874",
}
# trafilatura already honours a meta tag in the part of the page it scans for one.
META_CHARSET = re.compile(rb"<meta[^>]+charset\s*=", re.IGNORECASE)
META_SCAN_BYTES = 5000
# A comment runs to the next "-->", or to the end when it isn't closed; "<!-->" and "<!--->" are empty ones.
HTML_COMMENT = re.compile(rb"<!--(?:-?>|.*?(?:-->|\Z))", re.DOTALL)


class ArticleError(Exception):
    """A failure whose message can be shown to the user as is."""


NOT_A_LINK = "Enter a full web address starting with http:// or https://."
BAD_REDIRECT = "That link redirects to an address we can't open. Paste the text instead."
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
            async with client.stream("GET", current, headers=HEADERS, timeout=TIMEOUT) as res:
                if res.is_redirect and "location" in res.headers:
                    current = _redirect_target(current, res.headers["location"])
                    continue
                _check_response(res)
                body = await _read_limited(res)
                charset = res.charset_encoding
        except httpx.InvalidURL as exc:  # httpx reads the Location itself, e.g. mailto: with no host
            raise ArticleError(BAD_REDIRECT) from exc
        except httpx.TransportError as exc:
            raise ArticleError(NO_RESPONSE) from exc
        return _extract(_decode(body, charset), str(current))
    raise ArticleError("That link redirects too many times. Try the article's own address.")


def _parse(url: str) -> httpx.URL:
    try:
        parsed = httpx.URL(url.strip())
    except httpx.InvalidURL as exc:
        raise ArticleError(NOT_A_LINK) from exc
    if parsed.scheme not in ("http", "https") or not parsed.host:
        raise ArticleError(NOT_A_LINK)
    return parsed


def _redirect_target(current: httpx.URL, location: str) -> httpx.URL:
    try:
        return _parse(str(current.join(location)))
    except ArticleError as exc:  # the user's link was fine; the site sent us somewhere else
        raise ArticleError(BAD_REDIRECT) from exc


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
    """Unpack the page ourselves, stopping at MAX_BYTES. httpx unpacks each chunk whole,
    and a few hundred compressed bytes can unpack to gigabytes."""
    encoding = res.headers.get("content-encoding", "").strip().lower()
    if encoding in ("", "identity"):
        unpack = None
    elif encoding in ("gzip", "x-gzip", "deflate"):
        unpack = zlib.decompressobj(wbits=47)  # gzip or zlib framing
    else:
        raise ArticleError(NOT_HTML)
    body = bytearray()
    async for chunk in res.aiter_raw():
        if unpack:
            try:
                chunk = unpack.decompress(chunk, MAX_BYTES + 1 - len(body))
            except zlib.error as exc:
                raise ArticleError(NOT_HTML) from exc
        body += chunk
        if len(body) > MAX_BYTES:
            raise ArticleError(NOT_HTML)
        if unpack and unpack.eof:
            break  # anything after the end of the compressed page is junk zlib would keep in memory
    return bytes(body)


def _decode(body: bytes, charset: str | None) -> str | bytes:
    """Read the page in the encoding the header declares. trafilatura ignores the header and
    guesses wrong for pages such as Shift_JIS that say their encoding nowhere else."""
    try:
        return body.decode("utf-8")  # a page that decodes as UTF-8 is UTF-8, whatever its label says
    except UnicodeDecodeError:
        pass
    if META_CHARSET.search(HTML_COMMENT.sub(b"", body[:META_SCAN_BYTES])):
        return body  # the page's own label wins: old servers send ISO-8859-1 for everything
    try:
        return body.decode(WEB_ENCODINGS[codecs.lookup(charset or "").name])
    except (LookupError, KeyError, UnicodeError):
        return body  # no label, a wrong one or one browsers don't support: let trafilatura guess


def _extract(body: str | bytes, url: str) -> Article:
    doc = trafilatura.bare_extraction(body, url=url, with_metadata=True, include_comments=False)
    text = (doc.text or "").strip() if doc else ""
    if len(text) < MIN_TEXT:
        raise ArticleError(NO_TEXT)
    title = (doc.title or "").strip() or None
    if title and not text.startswith(title):
        text = f"{title}\n\n{text}"
    truncated = len(text) > MAX_CHARS
    return Article(url=url, title=title, text=text[:MAX_CHARS].rstrip(), truncated=truncated)
