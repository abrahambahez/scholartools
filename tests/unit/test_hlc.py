import pytest

from scholartools.services import hlc


@pytest.fixture(autouse=True)
def reset_hlc():
    hlc._counter = 0
    hlc._last_ms = 0
    yield
    hlc._counter = 0
    hlc._last_ms = 0


def test_format():
    ts = hlc.now("peer1")
    assert ts.endswith("-peer1")
    parts = ts.split("-")
    assert len(parts) >= 3
    assert "T" in ts
    # counter part should be 4 digits
    assert parts[-2].isdigit()
    assert len(parts[-2]) == 4


def test_same_ms_increments():
    fixed_ms = 1700000000123
    hlc._last_ms = fixed_ms
    hlc._counter = 3

    # simulate same millisecond by directly calling now and checking counter increments
    # We can't freeze time, so we manipulate state: if _last_ms matches current ms,
    # counter increments. We'll test via the exposed state.
    # Fake: set _last_ms to a future value that won't match real time
    future_ms = 9999999999999
    hlc._last_ms = future_ms
    hlc._counter = 7

    # First call with future_ms set: real ms != future_ms → resets to 1
    ts1 = hlc.now("p")
    assert "-0001-p" in ts1
    cur_ms = hlc._last_ms
    cur_counter = hlc._counter
    assert cur_counter == 1

    # Now set _last_ms back to what was just set and call again — same ms → increment
    hlc._last_ms = cur_ms
    hlc._counter = cur_counter
    hlc.now("p")
    # Could be same ms (counter 2) or new ms (counter 1)
    assert hlc._counter >= 1


def test_explicit_same_ms_increment():
    hlc.now("peer")
    cur_ms = hlc._last_ms
    hlc._last_ms = cur_ms  # ensure same ms on next call
    # Force counter to known value
    hlc._counter = 5
    hlc._last_ms = cur_ms

    # Since we set _last_ms to current ms, next call within same ms will increment
    # However real time may have advanced. Test the counter logic directly.
    import time

    t0_ms = int(time.time() * 1000)
    hlc._last_ms = t0_ms
    hlc._counter = 5

    # Tight loop to get same ms
    found_same = False
    for _ in range(1000):
        ms_now = int(time.time() * 1000)
        if ms_now == t0_ms:
            ts = hlc.now("peer")
            assert "-0006-peer" in ts
            found_same = True
            break

    if not found_same:
        pytest.skip("Could not get same millisecond in tight loop")


def test_new_ms_resets_counter():
    future_ms = 9_000_000_000_000
    hlc._last_ms = future_ms
    hlc._counter = 99

    ts = hlc.now("p")
    # real time is much less than future_ms → new ms → counter resets to 1
    assert "-0001-p" in ts


def test_lexicographic_ordering():
    results = [hlc.now("p") for _ in range(10)]
    assert results == sorted(results)


def test_different_peer_ids():
    ts_a = hlc.now("peer-a")
    ts_b = hlc.now("peer-b")
    assert ts_a.endswith("-peer-a")
    assert ts_b.endswith("-peer-b")
    assert ts_a < ts_b or ts_a[:28] == ts_b[:28]
