"""Per-visitor request limits and a cap on analyses running at once.

Both live in memory, so they hold for one server process (the free hosts run one);
with several processes each would count on its own and a shared store would be needed.
"""

import asyncio
import time
from collections import deque
from contextlib import asynccontextmanager


class Busy(Exception):
    """Every analysis slot stayed taken for longer than a visitor should wait."""


class SlidingWindow:
    """Counts each visitor's requests over the last N seconds, for one or more (limit, seconds) rules."""

    def __init__(self, rules: list[tuple[int, float]], clock=time.monotonic):
        self.rules = rules
        self.clock = clock
        self._span = max(seconds for _, seconds in rules)
        self._hits: dict[str, deque[float]] = {}
        self._next_sweep = 0.0

    def hit(self, key: str, now: float | None = None) -> float | None:
        """Records a request at `now` (the clock by default) and returns None, or returns how many
        seconds to wait when over a limit.

        A refused request isn't recorded, so retrying early doesn't push the wait further out.
        """
        if now is None:
            now = self.clock()
        self._sweep(now)
        hits = self._hits.setdefault(key, deque())
        while hits and hits[0] <= now - self._span:
            hits.popleft()
        wait = 0.0
        for limit, seconds in self.rules:
            recent = [t for t in hits if t > now - seconds]
            if len(recent) >= limit:
                wait = max(wait, recent[-limit] + seconds - now)
        if wait:
            return wait
        hits.append(now)
        return None

    def refund(self, key: str, at: float) -> None:
        """Takes back the request recorded at `at`, for one the server turned away after all.

        Only that entry goes: a request that ends a minute after it arrived must not free a place
        taken by a newer one. If the entry has already left the window there is nothing to give back."""
        hits = self._hits.get(key)
        if hits and at in hits:
            hits.remove(at)

    def tracked(self) -> int:
        return len(self._hits)

    def _sweep(self, now: float) -> None:
        # Drops visitors with nothing left in the window, so memory doesn't grow with every new address.
        if now < self._next_sweep:
            return
        self._next_sweep = now + self._span
        for key in [k for k, hits in self._hits.items() if not hits or hits[-1] <= now - self._span]:
            del self._hits[key]


def proxy_hops(raw: str | None) -> int:
    """Parses TRUSTED_PROXY_HOPS: how many proxies of the host sit in front of the backend."""
    value = (raw or "0").strip()
    if not value.isdigit():
        raise ValueError(f"TRUSTED_PROXY_HOPS must be a whole number such as 0 or 1, not {raw!r}.")
    return int(value)


def client_ip(forwarded_for: str | None, peer: str | None, hops: int) -> str:
    """The visitor's address. Each trusted proxy appends the address it saw to X-Forwarded-For,
    so the visitor's is the one `hops` places from the right; anything further left the visitor
    could have written themselves."""
    if hops and forwarded_for:
        parts = [p.strip() for p in forwarded_for.split(",") if p.strip()]
        if len(parts) >= hops:
            return parts[-hops]
    return peer or "unknown"


class AnalysisSlots:
    """Lets a few analyses run at once; the rest wait their turn for up to `wait` seconds."""

    def __init__(self, size: int = 2, wait: float = 20.0):
        self.wait = wait
        self._slots = asyncio.Semaphore(size)

    @asynccontextmanager
    async def take(self):
        try:
            await asyncio.wait_for(self._slots.acquire(), self.wait)
        except TimeoutError:
            raise Busy from None
        try:
            yield
        finally:
            self._slots.release()
