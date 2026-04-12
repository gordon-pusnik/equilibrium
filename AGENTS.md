# AGENTS.md

## Project overview

Equilibrium is a shared-core video poker training suite built around a C++17 engine that powers:
- command-line tools
- a FastAPI service
- Android trainer apps
- iOS trainer apps
- an ML training/inference pipeline

Current supported variants:
- `jacks_or_better_9_6`
- `jacks_or_better_8_5`

Current supported engines:
- `solver`: exhaustive EV-optimal strategy, canonical source of truth
- `rule`: deterministic handcrafted strategy
- `ml`: experimental local JSON inference

## Product goals

Equilibrium is a trainer first.

Primary goals, in order:
1. Correct strategy
2. Clear teaching value
3. Cross-platform consistency
4. Fast mobile UX
5. Small, reviewable changes

Prefer:
- shared-core logic over duplicated platform logic
- explicit, readable code over clever abstractions
- additive changes over breaking changes
- narrow patches over wide refactors

## Non-negotiable invariants

### Solver authority
The solver is the source of truth for best-play decisions.

Never:
- let UI or explanation logic contradict solver results
- let ML silently replace solver authority
- weaken correctness to simplify presentation
- merge strategy changes without validating behavior

### Shared-core consistency
When business logic belongs in shared code, implement it once in shared/native layers rather than separately in Android/iOS.

### Explanation integrity
Explanations must be derived from solver-backed facts, not invented heuristics pretending to be authoritative.

## Working style

Before editing:
- inspect the relevant files and adjacent patterns
- identify the narrowest correct layer for the change
- understand whether the task touches strategy, API contract, or mobile bridges

During editing:
- keep the patch focused
- avoid unrelated renames, formatting, or drive-by refactors
- preserve naming/style already used in the directory
- comment only where logic is genuinely non-obvious

After editing:
- run the smallest relevant verification first
- then broader verification if the change is strategy-sensitive or cross-layer
- clearly summarize files touched, validation, risks, and follow-up work

## Planning expectations

For simple, localized work:
- proceed directly

For multi-file, cross-platform, or strategy-sensitive work:
- make a short plan first
- identify affected layers
- identify validation commands
- then implement

If the task expands beyond the original request:
- call out scope growth explicitly before continuing too far

## Build and verification

Start with the narrowest command that proves the change.

Primary build:
```bash
bash ./build.sh