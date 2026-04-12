from __future__ import annotations

from app.models.coach_api_models import DrillCategory, LeakCategory


LEAK_TO_DRILL: dict[LeakCategory, DrillCategory] = {
    LeakCategory.OVERVALUING_WEAK_FLUSH_DRAWS: DrillCategory.LOW_PAIR_VS_THREE_CARD_FLUSH,
    LeakCategory.BREAKING_MADE_PAIRS: DrillCategory.MADE_HAND_PRESERVATION,
    LeakCategory.OVERVALUING_SINGLE_HIGH_CARDS: DrillCategory.HIGH_CARD_DISCIPLINE,
    LeakCategory.MISSING_ROYAL_DRAW_VALUE: DrillCategory.ROYAL_DRAW_RECOGNITION,
    LeakCategory.KEEPING_WEAK_INSIDE_STRAIGHTS: DrillCategory.INSIDE_STRAIGHT_DISCIPLINE,
    LeakCategory.DISCARDING_TOO_AGGRESSIVELY: DrillCategory.GENERAL_ACCURACY,
    LeakCategory.OTHER: DrillCategory.GENERAL_ACCURACY,
}


DRILL_FOCUS_TEXT: dict[DrillCategory, str] = {
    DrillCategory.LOW_PAIR_VS_THREE_CARD_FLUSH: "Practice choosing made low pairs over weak 3-card flush draws.",
    DrillCategory.MADE_HAND_PRESERVATION: "Practice recognizing when made hands should be preserved instead of broken.",
    DrillCategory.HIGH_CARD_DISCIPLINE: "Practice avoiding weak single-high-card holds when stronger options exist.",
    DrillCategory.ROYAL_DRAW_RECOGNITION: "Practice spotting valuable royal-draw opportunities.",
    DrillCategory.INSIDE_STRAIGHT_DISCIPLINE: "Practice avoiding weak inside-straight holds unless they are truly best.",
    DrillCategory.GENERAL_ACCURACY: "Practice broad solver-accuracy training across mixed hands.",
}


def drill_for_leak(category: LeakCategory | None) -> DrillCategory:
    if category is None:
        return DrillCategory.GENERAL_ACCURACY
    return LEAK_TO_DRILL.get(category, DrillCategory.GENERAL_ACCURACY)


def drill_priority(*, occurrences: int, total_ev_lost: float) -> str:
    if occurrences >= 5 or total_ev_lost >= 1.0:
        return "high"
    if occurrences >= 2 or total_ev_lost >= 0.25:
        return "medium"
    return "low"
