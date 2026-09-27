"""Tests for reference/closure_reference.py."""

from __future__ import annotations

import pytest

from tstate.core import (
    TransitionSystem,
    from_count_vector,
    make_quotient_system,
    make_system,
    to_count_vector,
)


def _simple_chain() -> TransitionSystem[str]:
    edges = {"s0": ["s1"], "s1": ["s2"], "s2": ["s2"]}
    return TransitionSystem(["s0"], lambda s: edges[s])


def test_reachable_chain() -> None:
    assert _simple_chain().reachable() == frozenset({"s0", "s1", "s2"})


def test_reachable_lfp_matches_bfs() -> None:
    ts = _simple_chain()
    assert ts.reachable_lfp() == ts.reachable()


def test_is_closed() -> None:
    ts = _simple_chain()
    assert ts.is_closed(frozenset({"s0", "s1", "s2"}))
    assert ts.is_closed(frozenset({"s2"}))
    assert not ts.is_closed(frozenset({"s0", "s1"}))
    assert not ts.is_closed(frozenset({"s0"}))


def test_closure_theorem_chain() -> None:
    r = _simple_chain().closure_theorem()
    assert r["theorem_holds"]
    assert r["reachable_size"] == 3


def _branching() -> TransitionSystem[str]:
    edges = {"s0": ["s0", "s1"], "s1": ["s2"], "s2": ["s2"]}
    return TransitionSystem(["s0"], lambda s: edges[s])


def test_existential_attractor_branching() -> None:
    ts = _branching()
    assert ts.existential_attractor(frozenset({"s2"})) == frozenset({"s0", "s1", "s2"})


def test_universal_attractor_branching() -> None:
    ts = _branching()
    assert ts.universal_attractor(frozenset({"s2"})) == frozenset({"s1", "s2"})


def test_universal_attractor_self() -> None:
    ts = _branching()
    assert ts.universal_attractor(frozenset({"s0"})) == frozenset({"s0"})


def _k2(v: int) -> set[int]:
    return {0, 1}


def _k3_progress(v: int) -> set[int]:
    return {1} if v == 0 else {2}


def test_agents_3_reachable() -> None:
    assert len(make_system(3, 2, _k2).reachable()) == 8


def test_agents_3_closure_theorem() -> None:
    assert make_system(3, 2, _k2).closure_theorem()["theorem_holds"]


def test_agents_10_quotient() -> None:
    ts = make_quotient_system(10, 3, _k3_progress)
    R = ts.reachable()
    assert ts.closure_theorem()["theorem_holds"]
    assert len(R) == (10 + 1) * (10 + 2) // 2


def test_agents_100_quotient() -> None:
    ts = make_quotient_system(100, 3, _k3_progress)
    assert ts.closure_theorem()["theorem_holds"]
    assert len(ts.reachable()) == (100 + 1) * (100 + 2) // 2


def test_agents_1000_quotient() -> None:
    ts = make_quotient_system(1000, 3, _k3_progress)
    assert len(ts.reachable()) == (1000 + 1) * (1000 + 2) // 2


def test_quotient_matches_full_modulo_symmetry() -> None:
    n, k = 4, 3
    full = make_system(n, k, _k3_progress).reachable()
    quot = make_quotient_system(n, k, _k3_progress).reachable()
    full_cvs = {to_count_vector(s, k) for s in full}
    assert full_cvs == quot


def test_count_vector_roundtrip() -> None:
    for state in [(0, 1, 2), (1, 1, 1), (2, 2, 0)]:
        assert from_count_vector(to_count_vector(state, 3)) == tuple(sorted(state))


def test_unknown_state_raises() -> None:
    with pytest.raises(KeyError):
        _simple_chain().succ("nonexistent")
