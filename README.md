# tstate

tstate is a Python library that computes the set of states reachable from a
given set of initial states in a state machine. A state machine is described by
an initial set of states and a successor function that maps each state to a set
of successor states. The reachable set is the collection of every state that can
be reached from an initial state by applying the successor function zero or more
times. tstate returns the reachable set, the set of cycles in the state graph,
the set of attractors, and the set of symmetries of the successor function.
tstate uses only the Python standard library. tstate is the mathematical
foundation of the tmig stack.

tstate is a standalone library. The only runtime dependency is the Python standard library. No other program in the tmig stack is required to use tstate.

## What problem tstate solves

A protocol implementation, a state machine, or a simulation has states and
transitions between states. A common question is whether a specific state can
be reached. The question is decidable for finite state spaces, but existing
implementations disagree on conventions: whether a cycle is a path that returns
to its own start, whether attractors include states with no outgoing
transitions, and whether the closure includes the initial states. A program that
depends on reachability must adopt one set of conventions.

tstate provides one canonical implementation so that every program in the stack
that reasons about reachability uses the same definitions.

## What tstate provides

Four functions:

- `reachable(s0, delta)` returns the set of states reachable from `s0` by
  applying `delta` zero or more times.
- `cycles(s0, delta)` returns every simple cycle in the reachable set.
- `attractors(s0, delta)` returns every closed subset of the reachable set.
- `symmetries(s0, delta)` returns every automorphism of the state graph that
  commutes with `delta`.

## The mathematical model

Let `S` be a set of hashable values. Let `S0` be a finite subset of `S`. Let
`delta: S -> P(S)` be a function that maps each state to a set of states. The
reachable set is:

    Reach(S0, delta) = union over n >= 0 of delta^n(S0)

where `delta^0(S0) = S0` and `delta^(n+1)(S0) = union of delta(s) for s in delta^n(S0)`.

A cycle is a path `s_0 -> s_1 -> ... -> s_k -> s_0` where `k >= 1`.

An attractor is a subset `A` of `Reach` such that no successor of any element of
`A` lies outside `A`.

A symmetry is a bijection `sigma: S -> S` such that for every state `s`,
`delta(sigma(s)) = sigma(delta(s))`.

## Installation

    pip install tstate

## Usage

    from tstate import reachable, cycles, attractors

    def delta(s):
        return {(s + 1) % 3, s}

    R = reachable({0}, delta)
    assert R == frozenset({0, 1, 2})

    C = cycles({0}, delta)
    assert (0, 1, 2, 0) in C

    A = attractors({0}, delta)
    assert frozenset({0, 1, 2}) in A

A second example: verifying that a two-leader state is unreachable in a simple
leader-election protocol.

    from tstate import reachable

    def delta(state):
        leader, voters = state
        out = {(leader, voters)}
        for v in voters:
            if v != leader:
                out.add((v, voters))
        return out

    R = reachable({("A", ("A", "B", "C"))}, delta)
    two_leaders = [s for s in R if len({s[0]}) > 1]
    assert not two_leaders

## Known limitations

- States must be hashable. Unhashable states raise an error.
- Memory usage grows linearly with the size of the reachable set.
- Traversal is single-threaded.
- The successor function `delta` must be pure: it must not modify state outside
  the values passed to it.
- Only deterministic transitions are supported. Probabilistic transitions are
  not modeled.

## Relationship to the tmig stack

tstate is the mathematical foundation of the tmig stack. The abstractions in
the other programs reduce to reachability in the sense defined above. Formal
specification: [docs/SPEC.md](docs/SPEC.md). Relationship model:
[docs/STACK.md](docs/STACK.md).

## License

See [LICENSE](LICENSE).
