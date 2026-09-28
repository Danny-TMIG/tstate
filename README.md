# tstate

**Reachability closure and structural analysis over state graphs.**

tstate is a pure-Python library that answers one question: given a set of
initial states and a successor function, which states can this system
actually reach? It computes the full closure, detects cycles, finds
attractors, and identifies symmetries. No I/O. No dependencies beyond the
standard library.

## The problem

You're implementing a protocol. Five states, a transition rule. You want to
know: can it ever reach two leaders at once? Reason by hand, or write a
simulator and hope you hit the case, or enumerate the reachable set.

tstate is the third option, done correctly.

## What it does

Given hashable `S`, initial `S0`, and `delta: S -> Set[S]`, tstate computes

    Reach(S0, delta) = union over n >= 0 of delta^n(S0)

by BFS with memoization. Cycles are explicit tuples. Attractors are closed
subsets. Symmetries are automorphisms commuting with `delta`.

## Install

    pip install tstate

## Usage

    from tstate import reachable, cycles, attractors

    def delta(s):
        return {(s + 1) % 3, s}

    assert reachable({0}, delta) == frozenset({0, 1, 2})
    assert (0, 1, 2, 0) in cycles({0}, delta)
    assert frozenset({0, 1, 2}) in attractors({0}, delta)

Realistic example — checking two-leader reachability:

    from tstate import reachable

    def delta(state):
        leader, voters = state
        out = {(leader, voters)}
        for v in voters:
            if v != leader:
                out.add((v, voters))
        return out

    R = reachable({("A", ("A", "B", "C"))}, delta)
    assert not [s for s in R if len({s[0]}) > 1]

## Known limitations

- States must be hashable.
- Memory grows with |Reach|.
- Single-threaded.
- Successor function must be pure.
- Deterministic transitions only.

## Where this fits

tstate is the mathematical foundation of the stack. Full model in
[docs/STACK.md](docs/STACK.md).

## License

See LICENSE.
