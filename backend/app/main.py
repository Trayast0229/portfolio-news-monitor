import asyncio
import logging
import os
import threading
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Request
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


app = FastAPI(title="Portfolio News Monitor", lifespan=lifespan)


# Without this, a crash returns plain text and the frontend can't tell it apart
# from the dev proxy's "backend is off" reply. The traceback is still logged.
@app.exception_handler(Exception)
async def unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    detail = "Something went wrong on the analysis server. Try again, and if it keeps happening, check the backend terminal."
    return JSONResponse(status_code=500, content={"detail": detail})


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
