Below is a repo-style technical design doc you can hand to Codex or keep in `docs/coach_backend_design.md`.

# Equilibrium Premium Coaching Backend Design

## Purpose

This document defines the first deterministic implementation of premium coaching services for Equilibrium, exposed through FastAPI and backed by solver-grounded analysis.

Initial endpoints:

* `POST /coach/compare`
* `POST /coach/session-summary`
* `POST /coach/drill-recommendation`

This phase is:

* deterministic
* solver-backed
* API-only
* not yet wired into mobile apps
* designed to support future LLM polishing without changing the core analysis model

---

## Goals

Primary goals:

* add reusable coaching domain models
* keep solver as the strategy authority
* expose structured API responses
* support testable deterministic summaries and recommendations
* prepare for future premium mobile integration

Non-goals for this phase:

* mobile UI integration
* OpenAI API integration
* personalization beyond deterministic profiles
* authentication/billing
* session persistence design

---

## Core principles

### Solver authority

The solver remains the source of truth for:

* best hold
* EV ranking
* player-vs-best EV loss
* candidate comparison

### Deterministic coaching

Coaching logic should:

* classify
* aggregate
* map
* render via templates

It should not:

* invent strategy
* infer unsupported facts
* use freeform generative output

### Reusable analysis model

All coaching endpoints should build on shared normalized hand analysis structures, rather than each endpoint inventing its own shape.

### Thin API layer

FastAPI routes should:

* validate input
* call a service
* return structured output

Route handlers should not contain business logic.

---

# 1. Proposed module layout

A clean first-pass structure could look like this:

```text
api-server/
  app/
    routers/
      coach.py
    models/
      coach_api_models.py
    services/
      coach/
        compare_service.py
        session_summary_service.py
        drill_recommendation_service.py
        renderers.py
        classifiers.py
        mappings.py
        analysis_adapter.py
```

If some logic belongs closer to shared core, that is even better. In that case, think in terms of:

```text
poker-core/python/
  coaching/
    models.py
    classifiers.py
    mappings.py
    renderers.py
    compare_service.py
    session_summary_service.py
    drill_recommendation_service.py
```

And then FastAPI imports those services.

## Recommended split

Best option:

* solver-backed hand analysis stays where current core/backend analysis already lives
* coaching-specific deterministic logic lives in a reusable service layer
* FastAPI only adapts request/response models

---

# 2. Shared domain model

## 2.1 Enums and stable vocabularies

### `MistakeSeverity`

```python
class MistakeSeverity(str, Enum):
    PERFECT = "perfect"
    VERY_CLOSE = "very_close"
    SMALL_LEAK = "small_leak"
    MODERATE = "moderate"
    MAJOR = "major"
```

### `HoldLabel`

Use stable strings or an enum.

Suggested values:

* `high_pair`
* `low_pair`
* `two_pair`
* `three_of_a_kind`
* `four_card_flush`
* `three_card_flush`
* `four_to_open_straight`
* `four_to_inside_straight`
* `three_to_royal`
* `four_to_royal`
* `two_suited_high_cards`
* `single_high_card`
* `garbage_hand`
* `discard_all`

Keep this vocabulary narrow and versionable.

### `LeakCategory`

Suggested starting values:

* `overvaluing_weak_flush_draws`
* `breaking_made_pairs`
* `overvaluing_single_high_cards`
* `missing_royal_draw_value`
* `discarding_too_aggressively`
* `keeping_weak_inside_straights`
* `other`

These are product categories, not poker theory primitives.

### `DrillCategory`

Suggested starting values:

* `low_pair_vs_three_card_flush`
* `made_hand_preservation`
* `high_card_discipline`
* `royal_draw_recognition`
* `inside_straight_discipline`
* `general_accuracy`

---

## 2.2 Core normalized record

### `AnalyzedHandRecord`

This is the backbone structure.

```python
class AnalyzedHandRecord(BaseModel):
    variant: str
    hand: list[str]
    bet: int

    solver_best_hold_cards: list[str]
    solver_best_label: str
    solver_best_ev: float

    player_hold_cards: list[str] | None = None
    player_hold_label: str | None = None
    player_ev: float | None = None

    mistake_cost: float | None = None
    mistake_severity: MistakeSeverity | None = None
    leak_category: str | None = None

    top_alternatives: list["CompareCandidate"] | None = None

    session_id: str | None = None
    hand_index: int | None = None
    timestamp: str | None = None
```

Notes:

* `player_*` fields can be null for compare-only use
* `leak_category` may be derived server-side rather than supplied by clients
* `top_alternatives` is optional and more useful for compare

---

## 2.3 Compare models

```python
class CompareCandidate(BaseModel):
    rank: int
    hold_cards: list[str]
    label: str
    ev: float
    ev_gap_from_best: float
    explanation: str
```

```python
class CompareResult(BaseModel):
    variant: str
    hand: list[str]
    best_hold_cards: list[str]
    best_hold_label: str
    best_ev: float
    candidates: list[CompareCandidate]
```

---

## 2.4 Session summary models

```python
class LeakStat(BaseModel):
    category: str
    count: int
    total_ev_lost: float
    average_ev_lost: float
```

```python
class BiggestMistake(BaseModel):
    hand: list[str]
    player_hold_cards: list[str]
    solver_best_hold_cards: list[str]
    mistake_cost: float
    mistake_severity: str
    leak_category: str
```

```python
class SessionSummary(BaseModel):
    hands_played: int
    perfect_count: int
    accuracy_rate: float
    total_ev_lost: float
    average_ev_lost_per_hand: float
    biggest_mistake: BiggestMistake | None
    most_common_leak: str | None
    top_leak_categories: list[LeakStat]
    recommended_drill_focus: str
    summary_headline: str
    summary_text: str
```

---

## 2.5 Drill recommendation models

```python
class DrillSupportingStats(BaseModel):
    occurrences: int
    total_ev_lost: float
    average_ev_lost: float
```

```python
class SecondaryDrillRecommendation(BaseModel):
    category: str
    priority: str
```

```python
class DrillRecommendation(BaseModel):
    recommended_category: str
    priority: str
    reason: str
    supporting_stats: DrillSupportingStats
    suggested_focus: str
    secondary_recommendations: list[SecondaryDrillRecommendation] = []
```

---

# 3. Endpoint design

## 3.1 `POST /coach/compare`

### Purpose

Given a hand, show the top candidate holds and explain why the best one wins.

### Request

```python
class CompareRequest(BaseModel):
    variant: str
    hand: list[str]
    bet: int = 5
    top_n: int = 3
```

### Response

`CompareResult`

### Behavior

* validate variant and hand
* enumerate/rank holds using solver-backed logic
* take top `N`
* classify each candidate
* compute `ev_gap_from_best`
* render deterministic explanation for each candidate

### Notes

This should be implemented first because it is the most concrete endpoint and requires no session aggregation.

---

## 3.2 `POST /coach/session-summary`

### Purpose

Summarize how a player performed over a set of analyzed hands.

### Request, version 1

For speed, first version can accept analyzed hand records.

```python
class SessionSummaryRequest(BaseModel):
    variant: str | None = None
    hands: list[AnalyzedHandRecord]
```

### Response

`SessionSummary`

### Behavior

* count hands
* count perfect plays
* compute accuracy rate
* sum total EV lost
* average EV lost per hand
* identify biggest mistake
* aggregate leak categories
* identify most common leak
* select recommended drill
* render headline and summary text

### Later extension

A future version can accept raw player hand decisions and compute `AnalyzedHandRecord` server-side.

---

## 3.3 `POST /coach/drill-recommendation`

### Purpose

Recommend the next practice category based on recurring mistakes.

### Request, version 1

```python
class DrillRecommendationRequest(BaseModel):
    variant: str | None = None
    hands: list[AnalyzedHandRecord]
```

### Response

`DrillRecommendation`

### Behavior

* aggregate mistakes by leak category
* score categories by cost and frequency
* choose primary drill category
* produce secondary recommendations
* render deterministic reason and suggested focus

### Later extension

Can also accept a session summary object or stored session ID.

---

# 4. Service design

## 4.1 `analysis_adapter.py`

This module bridges existing solver/evaluation logic into coaching-friendly records.

Responsibilities:

* compute best hold and EV
* compute player EV if supplied
* compute mistake cost
* classify severity
* classify hold labels
* classify leak category

Suggested function:

```python
def analyze_hand_decision(
    *,
    variant: str,
    hand: list[str],
    bet: int,
    player_hold_cards: list[str] | None = None,
    top_n: int | None = None,
) -> AnalyzedHandRecord:
    ...
```

This adapter should reuse your current strategy/evaluation functionality rather than duplicating logic.

---

## 4.2 `classifiers.py`

Responsibilities:

* `classify_mistake_severity(ev_gap)`
* `classify_hold_label(hand, hold_cards, variant)`
* `classify_leak_category(record)`

### `classify_mistake_severity`

Initial thresholds:

* `0.0000` → `perfect`
* `0.0001 - 0.0499` → `very_close`
* `0.0500 - 0.1499` → `small_leak`
* `0.1500 - 0.3499` → `moderate`
* `0.3500+` → `major`

Centralize this so later tuning is easy.

### `classify_hold_label`

Should use deterministic pattern recognition, not text heuristics.

It can start simple:

* pair/trips/two-pair made hands
* flush draw counts
* straight draw counts
* royal draw indicators
* high-card and suited-high-card patterns
* fallback to `garbage_hand` or `discard_all`

### `classify_leak_category`

This maps player-vs-solver mismatch into a product-friendly leak label.

Simple starting rules:

* solver=`low_pair`, player=`three_card_flush` → `overvaluing_weak_flush_draws`
* solver is made pair, player breaks it → `breaking_made_pairs`
* solver is strong draw, player keeps single high card → `overvaluing_single_high_cards`
* solver is royal draw, player ignores it → `missing_royal_draw_value`
* solver better than discard, player discards too much → `discarding_too_aggressively`
* player keeps weak inside straight vs stronger alternative → `keeping_weak_inside_straights`
* else → `other`

Keep this intentionally small in v1.

---

## 4.3 `mappings.py`

Responsibilities:

* map `LeakCategory` → `DrillCategory`
* map categories to priority labels
* store reusable text fragments if needed

Example mapping:

```python
LEAK_TO_DRILL = {
    "overvaluing_weak_flush_draws": "low_pair_vs_three_card_flush",
    "breaking_made_pairs": "made_hand_preservation",
    "overvaluing_single_high_cards": "high_card_discipline",
    "missing_royal_draw_value": "royal_draw_recognition",
    "keeping_weak_inside_straights": "inside_straight_discipline",
    "other": "general_accuracy",
}
```

This file should also hold any drill descriptions.

---

## 4.4 `renderers.py`

Responsibilities:

* render compare candidate explanation
* render session summary headline/text
* render drill recommendation reason/focus

### `render_compare_explanation(candidate, best_candidate)`

Template ideas:

* best candidate:

  * “This is the strongest play because {reason}.”
* non-best:

  * “This option is weaker because it gives up {gap:.4f} expected value versus the best hold.”

### `render_session_summary(summary_stats)`

Template ideas:

* “Your biggest recurring leak is {leak}. Focusing on {drill} should improve your results fastest.”
* “You are finding many correct plays, but {leak} is costing the most expected value.”

### `render_drill_recommendation(drill, stats)`

Template ideas:

* “This category appears most often in your mistakes and accounts for the most expected value lost.”
* “Practice {drill_name} to improve recognition in these spots.”

Keep these renderers deterministic and short.

---

## 4.5 `compare_service.py`

Responsibilities:

* validate top_n bounds
* get ranked candidate holds from solver-backed analysis
* classify labels
* compute EV gaps
* render explanations
* build `CompareResult`

Suggested method:

```python
def compare_hand(*, variant: str, hand: list[str], bet: int, top_n: int = 3) -> CompareResult:
    ...
```

Implementation note:
If you already have all 32 hold masks and their EVs available or can expose them cheaply, this becomes straightforward.

---

## 4.6 `session_summary_service.py`

Responsibilities:

* aggregate `AnalyzedHandRecord`
* compute session totals
* compute leak stats
* identify biggest mistake
* choose primary drill
* render summary

Suggested method:

```python
def summarize_session(*, hands: list[AnalyzedHandRecord], variant: str | None = None) -> SessionSummary:
    ...
```

Aggregation logic:

* `hands_played = len(hands)`
* `perfect_count = count(mistake_severity == perfect)`
* `accuracy_rate = perfect_count / hands_played`
* `total_ev_lost = sum(mistake_cost or 0)`
* `average_ev_lost_per_hand = total_ev_lost / hands_played`

Leak aggregation:

* group by `leak_category` excluding null/other if desired
* compute counts and EV sums
* sort by total EV lost desc, then count desc

Recommended drill:

* derived from top leak via `mappings.py`

---

## 4.7 `drill_recommendation_service.py`

Responsibilities:

* aggregate leak categories
* select primary and secondary drill
* compute supporting stats
* render reason/focus text

Suggested method:

```python
def recommend_drill(*, hands: list[AnalyzedHandRecord], variant: str | None = None) -> DrillRecommendation:
    ...
```

Scoring:

* sort by `total_ev_lost desc`
* tie-break by `count desc`

Simple and deterministic.

---

# 5. Input mode strategy

## Version 1 recommendation

### `/coach/compare`

Accept raw hand input only.

### `/coach/session-summary`

Accept analyzed hand records.

### `/coach/drill-recommendation`

Accept analyzed hand records.

This is the fastest path.

## Why this split works

* compare is naturally server-computed
* session/drill are aggregation endpoints
* accepting analyzed records reduces first-pass scope
* later, you can add server-side session reconstruction without breaking the current contract

## Version 2

Add alternate raw-decision request types that compute analysis server-side.

---

# 6. Deterministic mapping tables

## 6.1 Severity thresholds

| EV gap          | Severity   |
| --------------- | ---------- |
| 0.0000          | perfect    |
| 0.0001 - 0.0499 | very_close |
| 0.0500 - 0.1499 | small_leak |
| 0.1500 - 0.3499 | moderate   |
| 0.3500+         | major      |

Store these in one place.

---

## 6.2 Leak-to-drill mapping

| Leak category                 | Drill category               |
| ----------------------------- | ---------------------------- |
| overvaluing_weak_flush_draws  | low_pair_vs_three_card_flush |
| breaking_made_pairs           | made_hand_preservation       |
| overvaluing_single_high_cards | high_card_discipline         |
| missing_royal_draw_value      | royal_draw_recognition       |
| keeping_weak_inside_straights | inside_straight_discipline   |
| other                         | general_accuracy             |

---

## 6.3 Drill description mapping

Example:

```python
DRILL_FOCUS_TEXT = {
    "low_pair_vs_three_card_flush": "Practice choosing made low pairs over weak 3-card flush draws.",
    "made_hand_preservation": "Practice recognizing when made hands should be preserved instead of broken.",
    "high_card_discipline": "Practice avoiding weak single-high-card holds when stronger options exist.",
    "royal_draw_recognition": "Practice spotting valuable royal-draw opportunities.",
    "inside_straight_discipline": "Practice avoiding weak inside-straight holds unless they are truly best.",
    "general_accuracy": "Practice broad solver-accuracy training across mixed hands.",
}
```

---

# 7. Example API schemas

## 7.1 Compare request

```json
{
  "variant": "jacks_or_better_9_6",
  "hand": ["KS", "10H", "5H", "10D", "2H"],
  "bet": 5,
  "top_n": 3
}
```

## 7.2 Compare response

```json
{
  "variant": "jacks_or_better_9_6",
  "hand": ["KS", "10H", "5H", "10D", "2H"],
  "best_hold_cards": ["10H", "10D"],
  "best_hold_label": "low_pair",
  "best_ev": 1.5362,
  "candidates": [
    {
      "rank": 1,
      "hold_cards": ["10H", "10D"],
      "label": "low_pair",
      "ev": 1.5362,
      "ev_gap_from_best": 0.0,
      "explanation": "This is the strongest play because a made low pair has more long-term value than the weaker draw options here."
    }
  ]
}
```

## 7.3 Session summary request

```json
{
  "variant": "jacks_or_better_9_6",
  "hands": [
    {
      "variant": "jacks_or_better_9_6",
      "hand": ["KS", "10H", "5H", "10D", "2H"],
      "bet": 5,
      "solver_best_hold_cards": ["10H", "10D"],
      "solver_best_label": "low_pair",
      "solver_best_ev": 1.5362,
      "player_hold_cards": ["10H", "5H", "2H"],
      "player_hold_label": "three_card_flush",
      "player_ev": 1.2148,
      "mistake_cost": 0.3214,
      "mistake_severity": "moderate",
      "leak_category": "overvaluing_weak_flush_draws"
    }
  ]
}
```

## 7.4 Session summary response

```json
{
  "hands_played": 50,
  "perfect_count": 18,
  "accuracy_rate": 0.36,
  "total_ev_lost": 6.482,
  "average_ev_lost_per_hand": 0.1296,
  "biggest_mistake": {
    "hand": ["KS", "10H", "5H", "10D", "2H"],
    "player_hold_cards": ["10H", "5H", "2H"],
    "solver_best_hold_cards": ["10H", "10D"],
    "mistake_cost": 0.3214,
    "mistake_severity": "moderate",
    "leak_category": "overvaluing_weak_flush_draws"
  },
  "most_common_leak": "overvaluing_weak_flush_draws",
  "top_leak_categories": [
    {
      "category": "overvaluing_weak_flush_draws",
      "count": 12,
      "total_ev_lost": 2.44,
      "average_ev_lost": 0.2033
    }
  ],
  "recommended_drill_focus": "low_pair_vs_three_card_flush",
  "summary_headline": "Weak flush-draw decisions are your biggest leak.",
  "summary_text": "Your most costly recurring mistake is overvaluing weak flush draws against stronger made hands. Focused practice on low-pair versus 3-card flush spots should improve your accuracy fastest."
}
```

## 7.5 Drill recommendation response

```json
{
  "variant": "jacks_or_better_9_6",
  "hands": [
    {
      "variant": "jacks_or_better_9_6",
      "hand": ["KS", "10H", "5H", "10D", "2H"],
      "bet": 5,
      "solver_best_hold_cards": ["10H", "10D"],
      "solver_best_label": "low_pair",
      "solver_best_ev": 1.5362,
      "player_hold_cards": ["10H", "5H", "2H"],
      "player_hold_label": "three_card_flush",
      "player_ev": 1.2148,
      "mistake_cost": 0.3214,
      "mistake_severity": "moderate",
      "leak_category": "overvaluing_weak_flush_draws"
    }
  ]
}
```

## 7.6 Drill recommendation response

```json
{
  "recommended_category": "low_pair_vs_three_card_flush",
  "priority": "high",
  "reason": "This is your most frequent and most costly recurring mistake pattern.",
  "supporting_stats": {
    "occurrences": 12,
    "total_ev_lost": 2.44,
    "average_ev_lost": 0.2033
  },
  "suggested_focus": "Practice choosing made low pairs over weak 3-card flush draws.",
  "secondary_recommendations": [
    {
      "category": "high_card_discipline",
      "priority": "medium"
    }
  ]
}
```

---

# 8. Validation and test plan

## 8.1 Unit tests

### `classifiers.py`

Test:

* severity threshold boundaries
* hold label classification for representative hands
* leak category classification for common mismatch patterns

### `mappings.py`

Test:

* every leak category maps to a drill
* unknown categories fall back to `general_accuracy`

### `renderers.py`

Test:

* deterministic output for known inputs
* no empty explanations/headlines
* formatting stable enough for golden-style assertions

---

## 8.2 Service tests

### `compare_service.py`

Representative hands:

* low pair vs weak 3-card flush
* 4-card flush draw
* 4 to open straight
* 3 to royal
* single high card
* discard-all hand

Assertions:

* candidates sorted by EV desc
* best candidate has `ev_gap_from_best == 0`
* explanations consistent with best candidate

### `session_summary_service.py`

Use fixtures with:

* repeated weak flush draw mistakes
* repeated single-high-card leaks
* mixed-quality play

Assertions:

* counts and EV totals correct
* biggest mistake chosen correctly
* most common leak chosen correctly
* recommended drill matches top leak

### `drill_recommendation_service.py`

Assertions:

* primary recommendation follows highest-cost leak
* secondary recommendations ordered deterministically
* suggested_focus matches drill mapping

---

## 8.3 API tests

Test that:

* routes register
* invalid payloads return 400/422 as appropriate
* valid payloads return the correct response model
* response schema is structured and complete

---

# 9. Future compatibility design

This design should support later LLM enhancement without changing core contracts.

## Future addition path

Later, an LLM could:

* rewrite `summary_text`
* adapt `reason`
* elaborate compare explanations
* tune tone/verbosity

But the following must remain solver/deterministic:

* best hold
* EVs
* severity
* labels
* leak category
* drill category

That separation is the key long-term design choice.

---

# 10. Milestone plan

## Milestone 1

Shared models and deterministic classifiers

Deliver:

* `MistakeSeverity`
* `HoldLabel`
* `LeakCategory`
* `DrillCategory`
* `AnalyzedHandRecord`
* severity classifier
* hold-label classifier
* leak classifier
* mapping tables

## Milestone 2

`POST /coach/compare`

Deliver:

* compare request/response models
* compare service
* compare route
* tests with representative hands

## Milestone 3

`POST /coach/session-summary`

Deliver:

* session summary models
* summary aggregation service
* summary renderer
* route
* tests with mixed hand fixtures

## Milestone 4

`POST /coach/drill-recommendation`

Deliver:

* drill recommendation models
* drill service
* route
* tests

## Milestone 5

Documentation and examples

Deliver:

* example payloads
* endpoint docs
* notes on future raw-input mode
* notes on future OpenAI augmentation

---
