from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class MistakeSeverity(str, Enum):
    PERFECT = "perfect"
    VERY_CLOSE = "very_close"
    SMALL_LEAK = "small_leak"
    MODERATE = "moderate"
    MAJOR = "major"


class HoldLabel(str, Enum):
    HIGH_PAIR = "high_pair"
    LOW_PAIR = "low_pair"
    TWO_PAIR = "two_pair"
    THREE_OF_A_KIND = "three_of_a_kind"
    PAT_STRAIGHT = "pat_straight"
    PAT_FLUSH = "pat_flush"
    FULL_HOUSE = "full_house"
    FOUR_OF_A_KIND = "four_of_a_kind"
    STRAIGHT_FLUSH = "straight_flush"
    ROYAL_FLUSH = "royal_flush"
    FOUR_CARD_FLUSH = "four_card_flush"
    THREE_CARD_FLUSH = "three_card_flush"
    FOUR_TO_OPEN_STRAIGHT = "four_to_open_straight"
    FOUR_TO_INSIDE_STRAIGHT = "four_to_inside_straight"
    THREE_TO_ROYAL = "three_to_royal"
    FOUR_TO_ROYAL = "four_to_royal"
    TWO_SUITED_HIGH_CARDS = "two_suited_high_cards"
    SINGLE_HIGH_CARD = "single_high_card"
    GARBAGE_HAND = "garbage_hand"
    DISCARD_ALL = "discard_all"
    FOUR_TO_STRAIGHT_FLUSH = "four_to_straight_flush"
    THREE_TO_STRAIGHT_FLUSH = "three_to_straight_flush"
    TWO_HIGH_CARDS = "two_high_cards"
    BEST_EXPECTED_VALUE_HOLD = "best_expected_value_hold"


class LeakCategory(str, Enum):
    OVERVALUING_WEAK_FLUSH_DRAWS = "overvaluing_weak_flush_draws"
    BREAKING_MADE_PAIRS = "breaking_made_pairs"
    OVERVALUING_SINGLE_HIGH_CARDS = "overvaluing_single_high_cards"
    MISSING_ROYAL_DRAW_VALUE = "missing_royal_draw_value"
    DISCARDING_TOO_AGGRESSIVELY = "discarding_too_aggressively"
    KEEPING_WEAK_INSIDE_STRAIGHTS = "keeping_weak_inside_straights"
    OTHER = "other"


class DrillCategory(str, Enum):
    LOW_PAIR_VS_THREE_CARD_FLUSH = "low_pair_vs_three_card_flush"
    MADE_HAND_PRESERVATION = "made_hand_preservation"
    HIGH_CARD_DISCIPLINE = "high_card_discipline"
    ROYAL_DRAW_RECOGNITION = "royal_draw_recognition"
    INSIDE_STRAIGHT_DISCIPLINE = "inside_straight_discipline"
    GENERAL_ACCURACY = "general_accuracy"


class CompareCandidate(BaseModel):
    rank: int
    hold_cards: list[str]
    label: HoldLabel
    ev: float
    ev_gap_from_best: float
    headline: str
    summary: str
    pattern_tip: Optional[str] = None
    explanation: str


class CompareResult(BaseModel):
    variant: str
    hand: list[str]
    best_hold_cards: list[str]
    best_hold_label: HoldLabel
    best_ev: float
    candidates: list[CompareCandidate]


class AnalyzedHandRecord(BaseModel):
    variant: str
    hand: list[str] = Field(..., min_length=5, max_length=5)
    bet: int = Field(..., ge=1, le=5)
    solver_best_hold_cards: list[str]
    solver_best_label: HoldLabel
    solver_best_ev: float
    player_hold_cards: Optional[list[str]] = None
    player_hold_label: Optional[HoldLabel] = None
    player_ev: Optional[float] = None
    mistake_cost: Optional[float] = None
    mistake_severity: Optional[MistakeSeverity] = None
    leak_category: Optional[LeakCategory] = None
    top_alternatives: Optional[list[CompareCandidate]] = None
    session_id: Optional[str] = None
    hand_index: Optional[int] = None
    timestamp: Optional[str] = None


class LeakStat(BaseModel):
    category: LeakCategory
    count: int
    total_ev_lost: float
    average_ev_lost: float


class BiggestMistake(BaseModel):
    hand: list[str]
    player_hold_cards: list[str]
    solver_best_hold_cards: list[str]
    mistake_cost: float
    mistake_severity: MistakeSeverity
    leak_category: LeakCategory


class SessionSummary(BaseModel):
    hands_played: int
    perfect_count: int
    accuracy_rate: float
    total_ev_lost: float
    average_ev_lost_per_hand: float
    biggest_mistake: Optional[BiggestMistake]
    most_common_leak: Optional[LeakCategory]
    top_leak_categories: list[LeakStat]
    recommended_drill_focus: DrillCategory
    summary_headline: str
    summary_text: str


class DrillSupportingStats(BaseModel):
    occurrences: int
    total_ev_lost: float
    average_ev_lost: float


class SecondaryDrillRecommendation(BaseModel):
    category: DrillCategory
    priority: str


class DrillRecommendation(BaseModel):
    recommended_category: DrillCategory
    priority: str
    reason: str
    supporting_stats: DrillSupportingStats
    suggested_focus: str
    secondary_recommendations: list[SecondaryDrillRecommendation] = Field(default_factory=list)


class CompareRequest(BaseModel):
    variant: str
    hand: list[str] = Field(..., min_length=5, max_length=5)
    bet: int = Field(5, ge=1, le=5)
    top_n: int = Field(3, ge=1, le=10)


class SessionSummaryRequest(BaseModel):
    variant: Optional[str] = None
    hands: list[AnalyzedHandRecord]

    @model_validator(mode="after")
    def validate_hands(self) -> "SessionSummaryRequest":
        if not self.hands:
            raise ValueError("hands must not be empty")
        return self


class DrillRecommendationRequest(BaseModel):
    variant: Optional[str] = None
    hands: list[AnalyzedHandRecord]

    @model_validator(mode="after")
    def validate_hands(self) -> "DrillRecommendationRequest":
        if not self.hands:
            raise ValueError("hands must not be empty")
        return self
