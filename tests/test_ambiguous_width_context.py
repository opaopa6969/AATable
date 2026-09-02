"""Regression tests for per-context ambiguous-width settings."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import _aawidth


def test_ambiguous_width_is_isolated_between_threads():
    barrier = Barrier(2)

    def measure(width):
        _aawidth.set_ambiguous_width(width)
        barrier.wait()
        return _aawidth.display_width("①②③")

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(measure, (2, 1)))

    assert results == [6, 3]
