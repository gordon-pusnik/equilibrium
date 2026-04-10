# Equilibrium Video Poker Suite

Equilibrium is a shared-core video poker project built around a C++17 engine that powers command-line tools, a FastAPI service, Android and iOS trainer apps, and an ML training pipeline.

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
  - FastAPI endpoints for strategy lookup and hand evaluation
- `android-app`
  - Kotlin + Jetpack Compose + JNI
- `ios-app`
  - SwiftUI + Objective-C++

## Current User-Facing Features

- Variant selection in both mobile apps
- Variant-specific RTP display and paytable display
- Solver, rule, and ML engine switching
- Post-deal engine switching to compare suggested holds on the same hand
- Explanation panel for suggested holds
- Solver-only EV detail output in the expanded explanation view
- Variant-specific bundled ML models in Android and iOS

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

Strategy endpoint:

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

## Mobile Summary

Android and iOS both use the same core logic and now bundle separate ML models per variant:

- `jacks_or_better_9_6` -> `modeljob96.json`
- `jacks_or_better_8_5` -> `modeljob85.json`

The ML engine is currently useful for comparison and experimentation, but it still trails the rule and solver engines in RTP.
