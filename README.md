# tstate


<!-- tmig-stack-intro -->

## What this is

**tstate** is a small pure-Python library that answers the question *which states can this system actually reach*: given a set of initial states and a successor function, it computes the full reachable closure, detects cycles, and finds attractors and symmetries — the mathematical primitives that the larger packages in the stack are built on. It's not a framework or a server or a service; it's about fifteen tests' worth of functions that do one thing and do it exactly, so that a distributed system, a state machine, or a protocol implementation can ask "what can happen from here" and get a definitive answer instead of a guess. Its purpose is to make reachability a fact you can compute rather than a property you hope for, and to give the rest of the stack a single shared definition of what "this state leads to that state" means.

*Part of the [tmig stack](https://github.com/Danny-TMIG/tmig).*
---

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
