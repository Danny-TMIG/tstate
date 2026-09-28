# Specification: tstate

**Spec version:** 1.0
**Status:** Active
**Series:** tmig-stack/SPEC/tstate
**Last updated:** 2026-09-28

## 1. Identification

| Field | Value |
|---|---|
| Project | tstate |
| Repository | Danny-TMIG/tstate |
| Language | Python 3.12+ |
| Maintainer | Danny-TMIG |

## 2. Abstract

Computes the least fixpoint of a state graph and reports structural properties.

## 3. Scope

In scope: the functional surface described in section 5.

Out of scope: Termination for infinite Reach; delta models the intended system.

## 4. Conformance

RFC 6962 §2.1; RFC 8032; FIPS 180-4 where applicable.

## 5. Conceptual model

Reach(S0, delta) = union over n >= 0 of delta^n(S0). Cycle: s0 -> ... -> sk -> s0 with k >= 1. Attractor: closed subset of Reach. Symmetry: automorphism commuting with delta.

## 6. Interfaces

Public Python API and CLI as documented in README.md.

## 7. Functional requirements

Derived from the model above. Each requirement's verification is the
observable behaviour under test in the repo test suite.

## 8. Non-functional requirements

Determinism; purity where applicable; dependency minimality.

## 9. Invariants

As listed in OVERVIEW.md §5.

## 10. Dependencies

See pyproject.toml.

## 11. Limitations and non-goals

- Requires hashable states.
- Memory grows with |Reach|.
- Single-threaded.
- Assumes delta purity.
- No probabilistic transitions.

## 12. Versioning and compatibility

Semantic versioning. Public API stable within a major version.

## 13. Cross-references

- Stack index: tmig/docs/SPEC-STACK.md
- Relationship: docs/STACK.md
- Deep overview: docs/OVERVIEW.md
