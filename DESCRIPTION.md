# Equilibrium Video Poker Suite

Equilibrium is a shared-core video poker project built around a C++17 engine that powers command-line tools, a FastAPI service, Android and iOS trainer apps, a deterministic coaching backend, and an ML training pipeline.

## What It Supports

- Variants:
  - `jacks_or_better_9_6`
  - `jacks_or_better_8_5`
- Engines:
  - `solver`: exhaustive EV-optimal autohold
  - `rule`: handcrafted strategy table
  - `ml`: local JSON neural-network inference

## Main Components

- `poker-core/c++`
  - hand evaluation
  - payout calculation
  - variant-aware solver and rule logic
  - trainer API used by mobile and API layers
- `poker-core/python`
  - ML model training from solver-generated JSONL data
- `api-server`
  - FastAPI endpoints for strategy lookup, hand evaluation, and deterministic coaching
- `android-app`
  - Kotlin + Jetpack Compose + JNI
- `ios-app`
  - SwiftUI + Objective-C++

## Current User-Facing Features

- Variant selection in both mobile apps
- Variant-specific RTP display and paytable display
- Solver-backed trainer flow in both mobile apps
- Deterministic coaching explanation panel for suggested holds
- Solver EV detail output in the expanded explanation view
- Mistake severity feedback for player-selected holds
- Premium coaching API endpoints for compare, session summaries, and drill recommendations

## CLI Summary

Build:

```bash
bash ./build.sh
```

Run gameplay simulation:

```bash
./build/videopoker --variant jacks_or_better_9_6 100 5 10
```

Verify RTP:

```bash
./build/verify_rtp --engine solver --variant jacks_or_better_8_5 50000 3 5 12345
```

Run ML:

```bash
./build/videopoker --engine ml --variant jacks_or_better_9_6 --ml-model ml/modeljob96.json 100 5 10
```

## API Summary

Strategy/evaluate endpoints:

```json
{
  "variant": "jacks_or_better_9_6",
  "hand": ["KS", "10H", "5H", "10D", "2H"],
  "bet": 5,
  "engine": "solver"
}
```

ML requests additionally require:

```json
{
  "model_path": "/absolute/path/to/model.json"
}
```

Coaching endpoints now exist under `/v1/coach`:
- `/v1/coach/compare`
- `/v1/coach/session-summary`
- `/v1/coach/drill-recommendation`

They are deterministic, solver-backed, and return structured labels, EV comparisons, leak categories, and drill recommendations.

## Mobile Summary

Android and iOS both use the same shared core, but the current trainer UI is solver-backed rather than exposing engine switching. The ML engine and variant-specific models remain in the repo for CLI evaluation, experimentation, and future product work, but they still trail the rule and solver engines in RTP.
