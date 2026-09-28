# tstate — Reachable-State Closure and Structural Analysis

## Abstract

tstate is a pure-Python library that computes the reachable closure of a
finite or finitely-describable state space given an initial set and a
successor function. It reports the closure, cycle structure, and attractors,
and exposes symmetry detection as a first-class operation. It has no I/O, no
dependencies beyond the standard library, and no configuration. It exists so
that every other package in the stack has one shared, unambiguous definition
of *what can happen from here*.

## 1. Problem

Distributed systems, protocol implementations, and state-machine models all
ask the same question: given a set of initial states and a transition
relation, what is the set of states reachable by any finite sequence of
transitions? This question is decidable in principle for finite state spaces
and in practice for finitely-describable ones with memoization, but the
implementations scattered across frameworks disagree on cycle detection
conventions, initial-state semantics, and what counts as an "attractor".
Without a canonical implementation, every system that reasons about
reachability introduces its own conventions, and the conventions are not
composable.

## 2. Formal model

Let `S` be the state type (assumed hashable), `S₀ ⊆ S` a finite initial set,
and `δ: S → 𝒫(S)` a successor function. Define the *reachable set*

    Reach(S₀, δ) = ⋃ₙ₌₀^∞ δⁿ(S₀)

where `δ⁰(S₀) = S₀` and `δⁿ⁺¹(S₀) = ⋃_{s ∈ δⁿ(S₀)} δ(s)`.

tstate computes `Reach` by breadth-first traversal with a visited set,
guaranteeing termination iff `Reach` is finite and each `δ(s)` is finite.

A *cycle* is a path `s₀ → s₁ → … → sₖ → s₀` with `k ≥ 1`. An *attractor* is a
closed subset `A ⊆ Reach` such that no path from any `s ∈ A` leaves `A`. A
*symmetry* is an automorphism `σ: S → S` with `δ ∘ σ = σ ∘ δ`.

## 3. Design decisions

**Hashable state contract.** States must be hashable; the library does not
attempt to canonicalize unhashable representations. This is deliberate — a
library that silently serializes arbitrary objects to strings to make them
hashable creates a class of bugs (state A and state B hashing to the same
string) that is extremely hard to find and trivially avoided by requiring
hashability up front.

**Breadth-first by default.** Depth-first would yield the same reachable set
but would not terminate on infinite-depth finite-width spaces and would
produce cycles in a less useful order. BFS gives shortest-path lengths as a
byproduct, which are the natural diagnostic.

**Cycle detection as an explicit return value.** Cycles are returned, not
raised. The caller decides whether a cycle is an error, a fixpoint, or a
desirable attractor. Libraries that raise on cycles force the caller to
distinguish by exception-type inspection, which does not compose.

**No state-space compression.** tstate does not attempt to canonicalize
states, merge isomorphic subgraphs, or bound memory. Those are legitimate
optimizations for specific problems and are not attempted here because they
require problem-specific knowledge (a canonical form for one domain is
wrong for another).

## 4. Threat model

tstate is not a security boundary. Its threat model is limited to *correctness
of computation*: given valid inputs, it must return a set that equals the
mathematical `Reach`. It makes no claims about adversarial states, side
channels, or resource exhaustion beyond the termination condition above.

## 5. What it proves, and what it doesn't

Proves: for finite `Reach` and finite branching, that the returned set equals
`Reach(S₀, δ)` under the given `δ`; that any reported cycle is a genuine
cycle; that any reported attractor is a genuine closed subset.

Does not prove: termination for infinite `Reach`; that `δ` is a correct model
of the system it is meant to describe; anything about states not in `Reach`.

## 6. Related work

- *TLA⁺ / TLC.* Model checker with explicit-state enumeration; tstate is a
  library, not a checker, and provides no temporal logic.
- *SPIN.* Explicit-state model checker with a C-like language; tstate has no
  input language.
- *NetworkX.* General graph library; tstate specializes to state graphs with
  a successor function and exposes reachability/attractor/cycle primitives
  directly, not via graph construction.
- *Hypothesis.* Property-based testing; orthogonal — tstate is often used by
  property tests to bound the search space.

## 7. Known limitations

1. **Hashability requirement.** States must be hashable.
2. **No canonical form.** Memory grows linearly with `|Reach|`.
3. **No parallelism.** Traversal is single-threaded.
4. **Successor function purity assumed.** If `δ` has side effects, behavior
   is undefined.
5. **No probabilistic transitions.** Deterministic `δ` only.

## 8. Extension points

- **Symmetry reduction** via user-supplied automorphism group.
- **BDD or SAT backend** for large state spaces with structured transitions.
- **Distributed exploration** with a sharded visited set.
- **Temporal queries** (CTL/CTL*) as a separate layer over the reachability
  primitive.
