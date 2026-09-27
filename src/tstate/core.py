"""Reference implementation of transition-system closure concepts."""

from __future__ import annotations

from collections import deque
from collections.abc import Callable, Hashable, Iterable
from itertools import product
from typing import Generic, TypeVar

S = TypeVar("S", bound=Hashable)


class TransitionSystem(Generic[S]):
    """A finite transition system (S, ->)."""

    def __init__(
        self,
        init_states: Iterable[S],
        succ: Callable[[S], Iterable[S]],
    ) -> None:
        self.init_states: frozenset[S] = frozenset(init_states)
        self._succ = succ

    def succ(self, s: S) -> frozenset[S]:
        return frozenset(self._succ(s))

    def post(self, X: frozenset[S]) -> frozenset[S]:
        return frozenset(s2 for s in X for s2 in self.succ(s))

    def pre(self, X: frozenset[S], universe: frozenset[S]) -> frozenset[S]:
        return frozenset(s for s in universe if self.succ(s) & X)

    def reachable(self) -> frozenset[S]:
        visited: set[S] = set(self.init_states)
        queue: deque[S] = deque(self.init_states)
        while queue:
            s = queue.popleft()
            for s2 in self.succ(s):
                if s2 not in visited:
                    visited.add(s2)
                    queue.append(s2)
        return frozenset(visited)

    def reachable_lfp(self) -> frozenset[S]:
        X: frozenset[S] = frozenset()
        while True:
            nxt = self.init_states | self.post(X)
            if nxt == X:
                return X
            X = nxt

    def is_closed(self, X: frozenset[S]) -> bool:
        return self.post(X) <= X

    def closure_theorem(self) -> dict:
        R = self.reachable()
        contains_init = self.init_states <= R
        closed = self.is_closed(R)
        minimal = True
        for s in R:
            if s in self.init_states:
                continue
            candidate = R - {s}
            if self.init_states <= candidate and self.is_closed(candidate):
                minimal = False
                break
        return {
            "reachable_size": len(R),
            "contains_init": contains_init,
            "closed": closed,
            "minimal": minimal,
            "theorem_holds": contains_init and closed and minimal,
        }

    def existential_attractor(self, A: frozenset[S]) -> frozenset[S]:
        universe = self.reachable()
        X: frozenset[S] = frozenset()
        while True:
            nxt = A | self.pre(X, universe)
            if nxt == X:
                return X
            X = nxt

    def universal_attractor(self, A: frozenset[S]) -> frozenset[S]:
        universe = self.reachable()
        X: frozenset[S] = frozenset()
        while True:
            nxt = A
            for s in universe:
                post_s = self.succ(s)
                if post_s and post_s <= X:
                    nxt = nxt | {s}
            if nxt == X:
                return X
            X = nxt


def make_system(
    n: int,
    k: int,
    local_succ: Callable[[int], set[int]],
    *,
    async_update: bool = True,
) -> TransitionSystem[tuple[int, ...]]:
    init = (0,) * n

    if async_update:

        def succ(state: tuple[int, ...]) -> set[tuple[int, ...]]:
            if len(state) != n or not all(0 <= v < k for v in state):
                return set()
            out: set[tuple[int, ...]] = set()
            for i in range(n):
                for new_v in local_succ(state[i]):
                    if new_v == state[i]:
                        continue
                    s = list(state)
                    s[i] = new_v
                    out.add(tuple(s))
            return out

    else:

        def succ(state: tuple[int, ...]) -> set[tuple[int, ...]]:
            if len(state) != n or not all(0 <= v < k for v in state):
                return set()
            options = [sorted(local_succ(v)) for v in state]
            return {tuple(p) for p in product(*options)}

    return TransitionSystem([init], succ)


def to_count_vector(state: tuple[int, ...], k: int) -> tuple[int, ...]:
    counts = [0] * k
    for v in state:
        counts[v] += 1
    return tuple(counts)


def from_count_vector(cv: tuple[int, ...]) -> tuple[int, ...]:
    out: list[int] = []
    for v, c in enumerate(cv):
        out.extend([v] * c)
    return tuple(out)


def make_quotient_system(
    n: int,
    k: int,
    local_succ: Callable[[int], set[int]],
) -> TransitionSystem[tuple[int, ...]]:
    init_cv = (n,) + (0,) * (k - 1)

    def cv_succ(cv: tuple[int, ...]) -> set[tuple[int, ...]]:
        out: set[tuple[int, ...]] = set()
        for v in range(k):
            if cv[v] == 0:
                continue
            for new_v in local_succ(v):
                if new_v == v:
                    continue
                nxt = list(cv)
                nxt[v] -= 1
                nxt[new_v] += 1
                out.add(tuple(nxt))
        return out

    return TransitionSystem([init_cv], cv_succ)
