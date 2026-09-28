# tstate — Reachable-State Closure and Structural Analysis

## Abstract

Computes the least fixpoint of a state graph and reports structural properties.

## 1. Problem

Reachability is decidable but implementations disagree on cycle conventions and attractor definitions.

## 2. Formal model

Reach(S0, delta) = union over n >= 0 of delta^n(S0). Cycle: s0 -> ... -> sk -> s0 with k >= 1. Attractor: closed subset of Reach. Symmetry: automorphism commuting with delta.

## 3. Design decisions

Hashability contract. BFS default. Cycle detection as explicit return value. No state-space compression.

## 4. Threat model

Not a security boundary. Limited to correctness of computation.

## 5. What it proves, and what it does not

Proves: For finite Reach and branching, returned set equals Reach(S0, delta); reported cycles are genuine; reported attractors are genuine closed subsets.

Does not prove: Termination for infinite Reach; delta models the intended system.

## 6. Related work

TLA+/TLC; SPIN; NetworkX; Hypothesis.

## 7. Known limitations

- Requires hashable states.
- Memory grows with |Reach|.
- Single-threaded.
- Assumes delta purity.
- No probabilistic transitions.

## 8. Extension points

1. Symmetry reduction.
2. BDD/SAT backend.
3. Distributed exploration.
4. Temporal queries.
