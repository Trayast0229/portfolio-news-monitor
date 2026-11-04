import asyncio
import logging
import os
import threading
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .aggregate import aggregate, normalize_weights
from .article import ArticleError, fetch_article
from .asx import resolve, search
from .engines.base import Engine, EngineError
from .engines.claude_engine import ClaudeEngine
from .engines.finbert_engine import FinbertEngine
from .models import (
    AnalyzeRequest,
    AnalyzeResponse,
    Article,
    EngineName,
    FetchArticleRequest,
    PortfolioResult,
    ResolvedHolding,
)

load_dotenv()
log = logging.getLogger("portfolio-news-monitor")


def default_engines() -> dict[str, Engine]:
    return {"claude": ClaudeEngine(), "finbert": FinbertEngine()}


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not hasattr(app.state, "engines"):
        app.state.engines = default_engines()
    finbert = app.state.engines.get("finbert")
    # Load FinBERT in the background so the first analysis doesn't wait for it.
    if isinstance(finbert, FinbertEngine) and finbert.status() == "not_loaded" and os.getenv("FINBERT_PRELOAD", "1") == "1":
        threading.Thread(target=_preload, args=(finbert,), daemon=True).start()
    yield


def _preload(engine: FinbertEngine) -> None:
    try:
        engine._load()
        log.info("FinBERT loaded")
    except Exception:
        log.exception("FinBERT preload failed")


def cors_origins(raw: str | None) -> list[str]:
    """Parses ALLOWED_ORIGINS: the exact sites (scheme and host) allowed to call the API from a browser.

    A value the browser would never send, or "*", stops the server instead of silently
    blocking the frontend or opening the API to every site.
    """
    origins = []
    for item in (raw or "").split(","):
        origin = item.strip().rstrip("/")
        if not origin:
            continue
        scheme, sep, host = origin.partition("://")
        if scheme not in ("http", "https") or not sep or not host or "/" in host:
            raise ValueError(f"ALLOWED_ORIGINS needs full site addresses such as https://example.com, not {item.strip()!r}.")
        origins.append(origin)
    return origins


app = FastAPI(title="Portfolio News Monitor", lifespan=lifespan)


# Without this, a crash returns plain text and the frontend can't tell it apart
# from the dev proxy's "backend is off" reply. It is middleware rather than an
# exception handler so the reply passes back through CORS (added below, so it
# wraps this): Starlette sends a handled 500 from outside every middleware, and
# the browser would hide a reply that has no CORS header.
@app.middleware("http")
async def unexpected_error(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception:
        log.exception("Unexpected error on %s %s", request.method, request.url.path)
        return JSONResponse(status_code=500, content={"detail": "Something went wrong on our side. Try again in a moment."})


# FastAPI's own handler echoes each rejected value back, and JSON can't write 1e309 or NaN.
@app.exception_handler(RequestValidationError)
async def invalid_request(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = [{key: value for key, value in error.items() if key != "input"} for error in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": jsonable_encoder(errors)})


# Only needed when the frontend is served from another site; the dev proxy keeps it same-origin.
# Added last so it wraps the error middleware above.
if origins := cors_origins(os.getenv("ALLOWED_ORIGINS")):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )


@app.get("/api/health")
def health(request: Request):
    return {"engines": {name: e.status() for name, e in request.app.state.engines.items()}}


@app.get("/api/tickers")
def tickers(q: str = Query("", max_length=40)):
    return [{"ticker": c.ticker, "name": c.name} for c in search(q)]


@app.post("/api/article", response_model=Article)
async def article(body: FetchArticleRequest) -> Article:
    try:
        return await fetch_article(body.url)
    except ArticleError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze(body: AnalyzeRequest, request: Request) -> AnalyzeResponse:
    weights, adjusted = normalize_weights(body.holdings)
    holdings = resolve(body.holdings, weights)
    engines = request.app.state.engines
    results = await asyncio.gather(*(_run(name, engines[name], body.news, holdings) for name in body.engines))
    return AnalyzeResponse(weights_adjusted=adjusted, results=list(results))


async def _run(name: EngineName, engine: Engine, news: str, holdings: list[ResolvedHolding]) -> PortfolioResult:
    try:
        result = await engine.analyze(news, holdings)
    except EngineError as exc:
        return PortfolioResult(engine=name, status="error", error=str(exc))
    except Exception:
        log.exception("%s engine failed", name)
        return PortfolioResult(engine=name, status="error", error=f"The {name} engine hit an unexpected error.")
    return aggregate(name, holdings, result)
