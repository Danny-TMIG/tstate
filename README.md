# tstate

Explicit-state reachability, closure, and attractor computation for finite
transition systems. Pure Python, no dependencies.

## Install

    pip install -e .

## API

    from tstate import TransitionSystem, make_quotient_system

    edges = {"s0": ["s1"], "s1": ["s2"], "s2": ["s2"]}
    ts = TransitionSystem(["s0"], lambda s: edges[s])

    ts.reachable()
    ts.is_closed(frozenset({"s2"}))
    ts.closure_theorem()
    ts.existential_attractor(frozenset({"s2"}))
    ts.universal_attractor(frozenset({"s2"}))

    ts = make_quotient_system(n=1000, k=3, local_succ=lambda v: {1} if v == 0 else {2})
    len(ts.reachable())     # 501501

## Scaling

| n    | full (3^n) | quotient    |
|------|------------|-------------|
| 9    | 19,683     | —           |
| 100  | 3^100      | 5,151       |
| 1000 | 3^1000     | 501,501     |
| 5000 | 3^5000     | 12,507,501  |

## Test

    pytest -q
