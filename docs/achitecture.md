# Equilibrium Architecture

## Overview

Equilibrium is a shared-core video poker trainer built around a native C++17 engine that is reused across multiple product surfaces:
- CLI tools
- FastAPI server
- Android app
- iOS app
- Python ML pipeline

The architecture is designed to keep poker rules, hand evaluation, payout logic, solver logic, and strategy outputs centralized so behavior stays consistent across platforms.

---

## System goals

The architecture should preserve these priorities:

1. Solver-correct strategy
2. Shared-core behavior across platforms
3. Fast interactive performance on mobile
4. Clear teaching/explanation support
5. Small, maintainable integration layers

---

## Top-level components

### 1. `poker-core/cpp`
Primary shared engine.

Responsibilities:
- card representation
- deck / hand structures
- hand evaluation
- payout calculation
- hold-mask generation
- solver EV logic
- rule-engine strategy logic
- trainer-facing result data

This is the most important layer in the system.

The solver is the canonical source of truth for best-play recommendations.

---

### 2. `poker-core/python`
ML-related tooling.

Responsibilities:
- generating training data from solver outputs
- training small local models
- evaluating ML strategy quality
- exporting model artifacts for mobile/API usage

This layer is experimental and should not override solver authority.

---

### 3. `api-server`
FastAPI-based service layer.

Responsibilities:
- expose strategy/evaluation endpoints
- normalize request/response contracts
- optionally provide coaching/explanation endpoints
- act as a backend integration point for premium features

This layer should orchestrate shared-core outputs, not reimplement poker logic.

---

### 4. `android-app`
Kotlin + Jetpack Compose + JNI client.

Responsibilities:
- trainer UI
- game flow and state presentation
- paytable / RTP views
- engine compare UI
- explanation rendering
- bridge to native core through JNI

Business logic should stay thin here when it belongs in shared core.

---

### 5. `ios-app`
SwiftUI + Objective-C++ client.

Responsibilities:
- trainer UI
- state presentation
- engine compare UI
- explanation rendering
- native bridge to shared C++ core through Objective-C++

Business logic should stay thin here when it belongs in shared core.

---

## Source-of-truth hierarchy

For product behavior, the intended authority order is:

### Solver
Used for:
- best-play decision authority
- EV-accurate comparisons
- premium coaching truth
- mistake-cost analysis

### Rule engine
Used for:
- deterministic strategy comparisons
- fast heuristic teaching support
- offline comparisons where appropriate

### ML engine
Used for:
- experimentation
- comparison
- future approximation/offline support

ML should not be treated as authoritative unless explicitly promoted and validated.

---

## Core request flow

A typical trainer hand flow looks like this:

1. User is dealt a 5-card hand
2. App selects variant and engine
3. App sends request into native core or backend
4. Core computes best hold / evaluation result
5. UI renders recommendation and explanation data
6. User can compare engines or submit their own hold choice
7. System computes EV difference and feedback

---

## Strategy decision flow

### Solver flow
1. Receive hand, variant, and bet
2. Enumerate all valid hold masks
3. Evaluate draw EV for each hold
4. Select highest-EV hold
5. Return:
   - best hold
   - EV
   - optional ranked alternatives
   - optional structured metadata

### Rule flow
1. Receive hand and variant
2. Apply handcrafted strategy ordering
3. Return selected hold and explanation category

### ML flow
1. Encode hand / variant features
2. Run local inference
3. Decode predicted hold
4. Return hold and model metadata

---

## Explanation architecture

Equilibrium is a trainer, so explanation matters.

Preferred explanation pipeline:

1. Solver computes best play
2. System derives structured teaching metadata
3. System computes player-vs-best EV gap
4. Explanation layer renders a response using:
   - deterministic templates
   - or tightly constrained AI generation

### Important principle
The explanation layer explains solver-backed truth.
It does not invent or decide the truth.

---

## Recommended explanation metadata

When available, the system should derive structured hand tags such as:
- `low_pair`
- `high_pair`
- `two_suited_high_cards`
- `three_card_flush`
- `four_card_flush`
- `four_to_open_straight`
- `three_to_royal`
- `garbage_hand`

It is better to compute these explicitly than to make downstream layers infer everything from raw cards.

---

## Coaching architecture

A future premium coaching feature should use this flow:

1. Mobile app or API sends:
   - variant
   - hand
   - player hold
   - skill level
2. Backend/core computes:
   - solver best hold
   - best EV
   - player EV
   - mistake cost
   - ranked alternatives
   - structured hand metadata
3. Coaching layer returns:
   - headline
   - summary
   - why-it-wins bullets
   - mistake severity
   - pattern tip

### Preferred design
Use solver-backed structured facts first, then template or AI polish second.

Preferred sequence:
- solver -> metadata -> explanation scaffold -> optional LLM polish

Avoid:
- raw cards -> LLM decides the best poker play from scratch

---

## Cross-platform integration model

### Shared native logic
Should contain:
- all poker decision logic
- variant behavior
- payout math
- evaluation logic
- strategy outputs
- mistake-cost and hand metadata if possible

### Platform layers
Should contain:
- rendering
- user interaction
- state coordination
- animations
- platform-specific UX conventions

Do not duplicate strategy logic across Android and iOS unless necessary.

---

## Android bridge model

### Responsibilities
- convert Kotlin-side requests into native-friendly structures
- call shared C++ engine
- convert native result into Kotlin UI data
- minimize JNI round trips

### Guidance
Prefer coarse, structured result payloads over many tiny JNI calls.

Good:
- one native call returns recommendation + EV + metadata

Less good:
- separate native calls for each tiny UI field

---

## iOS bridge model

### Responsibilities
- convert Swift-side requests into Objective-C++ / C++ structures
- call shared C++ engine
- convert results into Swift-friendly models
- preserve parity with Android result shapes when practical

### Guidance
Keep bridge code explicit and easy to audit.
Prefer structured DTO-style results over ad hoc field scattering.

---

## API layer model

The API layer should expose stable, structured contracts.

### Existing direction
Strategy endpoint accepts:
- variant
- hand
- bet
- engine

ML requests may also include:
- model path

### Future coaching endpoint
Should return structured fields such as:
- `best_hold_cards`
- `best_ev`
- `player_ev`
- `mistake_cost`
- `mistake_severity`
- `headline`
- `summary`
- `pattern_tip`

Avoid returning only unstructured prose if the client needs clean rendering.

---

## ML architecture role

The ML pipeline currently exists to approximate strategy and support experimentation.

Recommended role:
- comparison engine
- future offline approximation
- possible pre-ranking helper for candidate holds
- research path for better modeling

Not recommended as the current role:
- canonical source of best-play truth

### Better future ML direction
Train on richer solver outputs:
- best hold
- EV of all hold masks
- regret of non-optimal holds
- variant-aware features

This is stronger than training only on a single best-action label.

---

## Data ownership summary

### Owned by shared core
- card logic
- hand evaluation
- payout rules
- solver logic
- rule logic
- hold-mask generation
- variant-specific decision behavior
- structured hand metadata if feasible

### Owned by API layer
- transport contracts
- auth / rate limiting / premium access
- backend orchestration
- coaching service integration

### Owned by mobile layers
- interaction flow
- layout and rendering
- local session state
- presentation of explanation data

### Owned by ML pipeline
- dataset generation
- training runs
- evaluation experiments
- model export tooling

---

## Change guidance by layer

### If changing `poker-core/cpp`
Assume the change can affect all surfaces:
- CLI
- API
- Android
- iOS
- ML labeling / evaluation

### If changing `api-server`
Check:
- request/response compatibility
- mobile client assumptions
- premium feature extensibility

### If changing mobile apps
Check:
- parity between Android and iOS
- whether logic belongs in shared core instead
- whether the data contract is still structured enough

### If changing ML
Check:
- whether inference contract changes affect bundled models
- whether solver comparison remains measurable
- whether performance/regression comparisons remain reproducible

---

## Architecture principles to preserve

1. Shared-core first
2. Solver-backed truth
3. Structured outputs over opaque blobs
4. Thin platform bridges
5. Clear ownership boundaries
6. Minimal duplication
7. Narrow, reviewable changes

---

## Near-term recommended architecture additions

These are good next architectural improvements:

### 1. Structured explanation metadata
Create a shared result model that can expose:
- best hold
- top alternatives
- hand labels
- mistake cost
- severity

### 2. Coaching result DTO
Add a stable structured explanation payload for future premium features.

### 3. Session analytics model
Add shared structures for:
- EV lost
- repeated leak categories
- accuracy rate
- common mistake classes

### 4. Variant expansion support
Keep variant-specific rules isolated enough that Deuces Wild / Bonus Poker / Joker Poker can be added without large UI rewrites.

---

## Long-term direction

A likely long-term path for Equilibrium is:

1. polished free mobile trainer
2. premium coaching and analytics
3. paid variant packs
4. optional backend coaching API / engine monetization

The architecture should continue to support that sequence without requiring major rewrites.