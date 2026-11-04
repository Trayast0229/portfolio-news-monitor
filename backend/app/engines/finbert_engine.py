"""FinBERT engine: free, local, and literal.

FinBERT only reads tone, so it can't tell which company a sentence is good or
bad for. We narrow it down by scoring only the sentences that name a holding.
Holdings the article never names are marked not relevant, which is exactly
where this engine and the Claude engine part ways.
"""

import asyncio
import importlib.util
import re
import threading
from collections.abc import Callable

from ..asx import find_mention, mentions
from ..models import EngineResult, HoldingSentiment, ResolvedHolding
from .base import EngineError, EngineStatus

MODEL_ID = "ProsusAI/finbert"
_NOT_INSTALLED = "FinBERT isn't installed on the analysis server, so it can't read stories right now."  # setup steps are in the README
_MAX_QUOTED = 2
_MAX_QUOTE_CHARS = 220
# FinBERT reads at most 512 tokens. 200 words leaves room for numbers and rare
# words that split into several tokens each.
_MAX_WORDS = 200

# A classifier takes sentences and returns, per sentence, every label with its score.
Classifier = Callable[[list[str]], list[list[dict]]]

_SENTENCE_END = re.compile(r"(?:(?<=[.!?])|(?<=[.!?][\"'”’]))\s+(?=[\"'“‘(A-Z0-9])")
_ABBREVIATIONS = {"co", "corp", "dr", "inc", "jr", "ltd", "mr", "mrs", "ms", "mt", "no", "prof", "sr", "st", "vs"}
_INITIALS = re.compile(r"(?:[A-Za-z]\.)+")  # U.S., J.P.


# Where a sentence turns from one company to another. The conjunction stays
# with the clause that follows it.
_CLAUSE_BREAK = re.compile(r"\s*;\s*|,?\s+(?=(?:while|but|whereas|although)\b)", re.IGNORECASE)


def _passage(sentence: str, holding: ResolvedHolding, holdings: list[ResolvedHolding]) -> str:
    """The part of a sentence to score for one holding.

    "BHP surged, while CBA plunged" would otherwise give both the same score.
    """
    if not any(o is not holding and mentions(sentence, o) for o in holdings):
        return sentence
    mine = [c.strip() for c in _CLAUSE_BREAK.split(sentence) if mentions(c, holding)]
    return " ".join(mine) if mine else sentence


def _focus(passage: str, holding: ResolvedHolding) -> str:
    """Keep a long passage to the words around the mention, so truncation can't drop it."""
    if len(passage.split()) <= _MAX_WORDS:
        return passage
    start = find_mention(passage, holding)
    if start is None:
        return passage
    before = passage[:start].split()[-(_MAX_WORDS // 2) :]
    after = passage[start:].split()[: _MAX_WORDS // 2]
    return " ".join(before + after)


def _ends_with_abbreviation(fragment: str) -> bool:
    last = fragment.split()[-1].lstrip("\"'“‘(")
    return last.rstrip(".").lower() in _ABBREVIATIONS or bool(_INITIALS.fullmatch(last))


def split_sentences(text: str) -> list[str]:
    # A period after "Ltd." or "U.S." usually isn't the end of the sentence, and
    # splitting there would part a company's name from what's said about it.
    # Line breaks always split.
    sentences = []
    for line in text.splitlines():
        pieces = [p.strip() for p in _SENTENCE_END.split(line) if p.strip()]
        for i, piece in enumerate(pieces):
            if i and _ends_with_abbreviation(pieces[i - 1]):
                sentences[-1] += " " + piece
            else:
                sentences.append(piece)
    return sentences


class FinbertEngine:
    name = "finbert"

    def __init__(self, classifier: Classifier | None = None):
        self._classifier = classifier
        self._lock = threading.Lock()  # loading the model
        # Two threads in the transformers pipeline at once crash the process (a segfault on
        # PyTorch, seen with two visitors analyzing together), so analyses take turns.
        self._run_lock = threading.Lock()

    def status(self) -> EngineStatus:
        if self._classifier is not None:
            return "ready"
        if importlib.util.find_spec("transformers") is None or importlib.util.find_spec("torch") is None:
            return "unavailable"
        return "not_loaded"

    def _load(self) -> Classifier:
        with self._lock:
            if self._classifier is None:
                if self.status() == "unavailable":
                    raise EngineError(_NOT_INSTALLED)
                from transformers import pipeline

                pipe = pipeline("text-classification", model=MODEL_ID, top_k=None, truncation=True)
                self._classifier = lambda sentences: pipe(sentences, batch_size=16)
            return self._classifier

    async def analyze(self, news: str, holdings: list[ResolvedHolding]) -> EngineResult:
        return await asyncio.to_thread(self._analyze_sync, news, holdings)

    def _analyze_sync(self, news: str, holdings: list[ResolvedHolding]) -> EngineResult:
        # Check before matching: a story that names no holding never loads the model,
        # and would otherwise come back "Not related" without FinBERT reading it.
        if self.status() == "unavailable":
            raise EngineError(_NOT_INSTALLED)
        sentences = split_sentences(news)
        hits = {h.ticker: [_focus(_passage(s, h, holdings), h) for s in sentences if mentions(s, h)] for h in holdings}
        to_score = list(dict.fromkeys(s for found in hits.values() for s in found))

        scores: dict[str, dict[str, float]] = {}
        if to_score:
            classify = self._load()
            with self._run_lock:
                raw = classify(to_score)
            scores = {s: {d["label"].lower(): float(d["score"]) for d in row} for s, row in zip(to_score, raw)}

        per_holding = []
        for h in holdings:
            found = hits[h.ticker]
            if not found:
                per_holding.append(HoldingSentiment(ticker=h.ticker, relevant=False, reason="Not mentioned in the article."))
                continue
            n = len(found)
            bull = sum(scores[s].get("positive", 0) for s in found) / n
            neu = sum(scores[s].get("neutral", 0) for s in found) / n
            bear = sum(scores[s].get("negative", 0) for s in found) / n
            total = bull + neu + bear or 1.0
            bull, neu, bear = bull / total, neu / total, bear / total
            reason = " ".join(f"“{_clip(s)}”" for s in found[:_MAX_QUOTED])
            # Text that still names another holding couldn't be split, so its tone may belong to either.
            if others := [o.ticker for o in holdings if o is not h and any(mentions(s, o) for s in found)]:
                reason += f" A sentence used here also names {', '.join(others)}, so FinBERT may have mixed up their news."
            per_holding.append(
                HoldingSentiment(
                    ticker=h.ticker,
                    relevant=True,
                    bullish=bull,
                    neutral=neu,
                    bearish=bear,
                    reason=reason,
                    confidence=round(max(bull, neu, bear) * 100),
                )
            )
        return EngineResult(per_holding=per_holding)


def _clip(sentence: str) -> str:
    return sentence if len(sentence) <= _MAX_QUOTE_CHARS else sentence[: _MAX_QUOTE_CHARS - 1].rstrip() + "…"
