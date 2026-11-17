# Equilibrium Verification Guide

## Purpose

This document defines the preferred verification approach for Equilibrium changes.

Goals:
- prove behavior with the smallest useful check first
- keep validation proportional to the risk of the change
- make it clear what was actually verified
- avoid claiming confidence that was not earned

General rule:
- narrow change -> narrow verification
- core strategy change -> direct strategy and EV validation
- cross-platform change -> validate each affected surface

---

## Verification principles

1. Start small
2. Validate the layer you changed
3. Validate downstream consumers if contracts changed
4. Be explicit when something could not be run
5. Never claim tests ran if they did not

---

## Build baseline

Primary repo build:
```bash
bash ./build.sh
```

## ML EV-regret benchmark

After building the native scoring worker, run:

```bash
python3 -B -m unittest discover -s poker-core/tests -v
```

The tests cover analytical hold EVs at bets 1 and 5 for both paytables, a solver
baseline with zero regret, distinct equal-EV holds, normalized regret and interval
arithmetic, category reconciliation, all card permutations and suit renamings of
an exclusion fixture, deterministic sampling, report replay, provenance hashes and
invalid arguments/models/hands. Small tracked hands live in
`poker-core/tests/fixtures/benchmark_hands.json`.

See `docs/ml_architecture.md`, Section 5, for pilot, baseline, exclusion and replay
commands and their statistical limits. This benchmark does not verify mobile or
API builds and does not change solver strategy.
