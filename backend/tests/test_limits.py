import asyncio

import pytest

from app.limits import AnalysisSlots, Busy, SlidingWindow, client_ip, proxy_hops


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def test_allows_up_to_the_limit_then_says_how_long_to_wait():
    clock = Clock()
    window = SlidingWindow([(3, 60)], clock)
    assert [window.hit("a") for _ in range(3)] == [None, None, None]
    clock.now += 20
    assert window.hit("a") == pytest.approx(40)


def test_a_request_counts_again_once_it_leaves_the_window():
    clock = Clock()
    window = SlidingWindow([(2, 60)], clock)
    window.hit("a")
    clock.now += 30
    window.hit("a")
    clock.now += 31  # the first request is now more than a minute old
    assert window.hit("a") is None
    assert window.hit("a") == pytest.approx(29)


def test_each_visitor_has_their_own_count():
    window = SlidingWindow([(1, 60)], Clock())
    assert window.hit("a") is None
    assert window.hit("b") is None
    assert window.hit("a") is not None


def test_the_longer_window_applies_once_the_short_one_resets():
    clock = Clock()
    window = SlidingWindow([(2, 60), (3, 3600)], clock)
    for _ in range(2):
        window.hit("a")
    clock.now += 61
    assert window.hit("a") is None  # third this hour
    clock.now += 61
    assert window.hit("a") == pytest.approx(3600 - 122)  # fourth this hour waits for the first to expire


def test_refused_requests_do_not_extend_the_wait():
    clock = Clock()
    window = SlidingWindow([(1, 60)], clock)
    window.hit("a")
    for _ in range(5):
        window.hit("a")
    clock.now += 61
    assert window.hit("a") is None


def test_forgets_visitors_who_went_quiet():
    clock = Clock()
    window = SlidingWindow([(5, 60)], clock)
    for i in range(1000):
        window.hit(f"visitor-{i}")
    clock.now += 61
    window.hit("new")
    assert window.tracked() == 1


def test_proxy_hops_setting():
    assert proxy_hops(None) == 0
    assert proxy_hops(" 1 ") == 1
    for bad in ("-1", "one", "1.5"):
        with pytest.raises(ValueError, match="TRUSTED_PROXY_HOPS"):
            proxy_hops(bad)


def test_without_a_trusted_proxy_the_forwarded_header_is_ignored():
    # A visitor can send X-Forwarded-For themselves to dodge the limit.
    assert client_ip("6.6.6.6", "203.0.113.5", hops=0) == "203.0.113.5"


def test_behind_one_proxy_the_address_it_added_is_used_not_the_ones_the_visitor_wrote():
    assert client_ip("6.6.6.6, 203.0.113.5", "10.0.0.2", hops=1) == "203.0.113.5"
    assert client_ip("203.0.113.5", "10.0.0.2", hops=1) == "203.0.113.5"


def test_a_request_that_skipped_the_proxies_falls_back_to_the_connection():
    assert client_ip(None, "10.0.0.2", hops=1) == "10.0.0.2"
    assert client_ip("203.0.113.5", "10.0.0.2", hops=2) == "10.0.0.2"


async def test_only_two_analyses_run_at_once_and_a_third_waits_its_turn():
    slots = AnalysisSlots(size=2, wait=1)
    running = 0
    peak = 0

    async def analysis():
        nonlocal running, peak
        async with slots.take():
            running += 1
            peak = max(peak, running)
            await asyncio.sleep(0.05)
            running -= 1

    await asyncio.gather(*(analysis() for _ in range(3)))
    assert peak == 2


async def test_a_waiting_analysis_gives_up_when_the_server_stays_busy():
    slots = AnalysisSlots(size=1, wait=0.05)
    release = asyncio.Event()

    async def hog():
        async with slots.take():
            await release.wait()

    task = asyncio.create_task(hog())
    await asyncio.sleep(0)
    with pytest.raises(Busy):
        async with slots.take():
            pass
    release.set()
    await task


def test_a_refunded_request_frees_its_place():
    clock = Clock()
    window = SlidingWindow([(2, 60)], clock)
    window.hit("a")
    window.hit("a")
    window.refund("a", clock.now)
    assert window.hit("a") is None
    assert window.hit("a") is not None
    window.refund("nobody", clock.now)  # a visitor the sweep already forgot


def test_refunding_a_request_that_already_left_the_window_changes_nothing():
    clock = Clock()
    window = SlidingWindow([(1, 60)], clock)
    old = clock.now
    window.hit("a")
    clock.now += 61
    window.hit("a")
    window.refund("a", old)
    assert window.hit("a") is not None
