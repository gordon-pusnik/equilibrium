from __future__ import annotations

from dataclasses import dataclass

from app.models.coach_api_models import HoldLabel, LeakCategory, MistakeSeverity


@dataclass(frozen=True)
class SeverityThresholds:
    very_close_max: float = 0.0499
    small_leak_max: float = 0.1499
    moderate_max: float = 0.3499


SEVERITY_THRESHOLDS = SeverityThresholds()


CATEGORY_TO_HOLD_LABEL: dict[str, HoldLabel] = {
    "high_pair": HoldLabel.HIGH_PAIR,
    "low_pair": HoldLabel.LOW_PAIR,
    "two_pair": HoldLabel.TWO_PAIR,
    "three_of_a_kind": HoldLabel.THREE_OF_A_KIND,
    "pat_straight": HoldLabel.PAT_STRAIGHT,
    "pat_flush": HoldLabel.PAT_FLUSH,
    "full_house": HoldLabel.FULL_HOUSE,
    "four_of_a_kind": HoldLabel.FOUR_OF_A_KIND,
    "straight_flush": HoldLabel.STRAIGHT_FLUSH,
    "royal_flush": HoldLabel.ROYAL_FLUSH,
    "four_card_flush": HoldLabel.FOUR_CARD_FLUSH,
    "three_card_flush": HoldLabel.THREE_CARD_FLUSH,
    "four_to_open_straight": HoldLabel.FOUR_TO_OPEN_STRAIGHT,
    "four_to_inside_straight": HoldLabel.FOUR_TO_INSIDE_STRAIGHT,
    "three_to_royal": HoldLabel.THREE_TO_ROYAL,
    "four_to_royal": HoldLabel.FOUR_TO_ROYAL,
    "two_suited_high_cards": HoldLabel.TWO_SUITED_HIGH_CARDS,
    "single_high_card": HoldLabel.SINGLE_HIGH_CARD,
    "garbage_hand": HoldLabel.GARBAGE_HAND,
    "discard_all": HoldLabel.DISCARD_ALL,
    "four_to_straight_flush": HoldLabel.FOUR_TO_STRAIGHT_FLUSH,
    "three_to_straight_flush": HoldLabel.THREE_TO_STRAIGHT_FLUSH,
    "two_high_cards": HoldLabel.TWO_HIGH_CARDS,
    "best_expected_value_hold": HoldLabel.BEST_EXPECTED_VALUE_HOLD,
}


def classify_mistake_severity(ev_gap: float) -> MistakeSeverity:
    if ev_gap <= 0.0:
        return MistakeSeverity.PERFECT
    if ev_gap <= SEVERITY_THRESHOLDS.very_close_max:
        return MistakeSeverity.VERY_CLOSE
    if ev_gap <= SEVERITY_THRESHOLDS.small_leak_max:
        return MistakeSeverity.SMALL_LEAK
    if ev_gap <= SEVERITY_THRESHOLDS.moderate_max:
        return MistakeSeverity.MODERATE
    return MistakeSeverity.MAJOR


def classify_hold_label(category: str) -> HoldLabel:
    return CATEGORY_TO_HOLD_LABEL.get(category, HoldLabel.BEST_EXPECTED_VALUE_HOLD)


def classify_leak_category(
    *,
    solver_best_label: HoldLabel,
    player_hold_label: HoldLabel | None,
) -> LeakCategory | None:
    if player_hold_label is None or player_hold_label == solver_best_label:
        return None

    if solver_best_label == HoldLabel.LOW_PAIR and player_hold_label == HoldLabel.THREE_CARD_FLUSH:
        return LeakCategory.OVERVALUING_WEAK_FLUSH_DRAWS

    if solver_best_label in {HoldLabel.HIGH_PAIR, HoldLabel.LOW_PAIR, HoldLabel.TWO_PAIR, HoldLabel.THREE_OF_A_KIND}:
        return LeakCategory.BREAKING_MADE_PAIRS

    if solver_best_label in {HoldLabel.THREE_TO_ROYAL, HoldLabel.FOUR_TO_ROYAL} and player_hold_label != solver_best_label:
        return LeakCategory.MISSING_ROYAL_DRAW_VALUE

    if player_hold_label == HoldLabel.SINGLE_HIGH_CARD and solver_best_label != HoldLabel.SINGLE_HIGH_CARD:
        return LeakCategory.OVERVALUING_SINGLE_HIGH_CARDS

    if player_hold_label in {HoldLabel.GARBAGE_HAND, HoldLabel.DISCARD_ALL} and solver_best_label not in {HoldLabel.GARBAGE_HAND, HoldLabel.DISCARD_ALL}:
        return LeakCategory.DISCARDING_TOO_AGGRESSIVELY

    if player_hold_label == HoldLabel.FOUR_TO_INSIDE_STRAIGHT and solver_best_label != HoldLabel.FOUR_TO_INSIDE_STRAIGHT:
        return LeakCategory.KEEPING_WEAK_INSIDE_STRAIGHTS

    return LeakCategory.OTHER
