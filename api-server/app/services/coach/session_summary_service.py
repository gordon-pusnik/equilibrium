from __future__ import annotations

from collections import defaultdict

from app.models.coach_api_models import (
    AnalyzedHandRecord,
    BiggestMistake,
    DrillCategory,
    LeakCategory,
    LeakStat,
    MistakeSeverity,
    SessionSummary,
)
from app.services.coach.mappings import drill_for_leak
from app.services.coach.renderers import (
    render_session_summary_headline,
    render_session_summary_text,
)


def _normalize_leak_category(record: AnalyzedHandRecord) -> LeakCategory | None:
    return record.leak_category


def _top_leak_stats(hands: list[AnalyzedHandRecord]) -> list[LeakStat]:
    totals: dict[LeakCategory, dict[str, float]] = defaultdict(lambda: {"count": 0, "ev": 0.0})
    for hand in hands:
        leak = _normalize_leak_category(hand)
        if leak is None:
            continue
        totals[leak]["count"] += 1
        totals[leak]["ev"] += float(hand.mistake_cost or 0.0)

    leak_stats = [
        LeakStat(
            category=category,
            count=int(values["count"]),
            total_ev_lost=round(values["ev"], 6),
            average_ev_lost=round(values["ev"] / values["count"], 6),
        )
        for category, values in totals.items()
        if values["count"] > 0
    ]
    leak_stats.sort(key=lambda item: (-item.total_ev_lost, -item.count, item.category.value))
    return leak_stats


def build_session_summary(*, hands: list[AnalyzedHandRecord]) -> SessionSummary:
    hands_played = len(hands)
    perfect_count = sum(1 for hand in hands if hand.mistake_severity == MistakeSeverity.PERFECT)
    total_ev_lost = round(sum(float(hand.mistake_cost or 0.0) for hand in hands), 6)
    average_ev_lost_per_hand = round(total_ev_lost / hands_played, 6)
    top_leak_categories = _top_leak_stats(hands)
    most_common_leak = top_leak_categories[0].category if top_leak_categories else None
    recommended_drill_focus: DrillCategory = drill_for_leak(most_common_leak)

    biggest_source = max(
        (hand for hand in hands if hand.mistake_cost is not None and hand.player_hold_cards is not None),
        key=lambda hand: (float(hand.mistake_cost or 0.0), hand.hand_index or -1),
        default=None,
    )
    biggest_mistake = None
    if biggest_source is not None and (biggest_source.mistake_cost or 0.0) > 0.0:
        biggest_mistake = BiggestMistake(
            hand=biggest_source.hand,
            player_hold_cards=biggest_source.player_hold_cards or [],
            solver_best_hold_cards=biggest_source.solver_best_hold_cards,
            mistake_cost=round(float(biggest_source.mistake_cost or 0.0), 6),
            mistake_severity=biggest_source.mistake_severity or MistakeSeverity.PERFECT,
            leak_category=biggest_source.leak_category or LeakCategory.OTHER,
        )

    return SessionSummary(
        hands_played=hands_played,
        perfect_count=perfect_count,
        accuracy_rate=round(perfect_count / hands_played, 6),
        total_ev_lost=total_ev_lost,
        average_ev_lost_per_hand=average_ev_lost_per_hand,
        biggest_mistake=biggest_mistake,
        most_common_leak=most_common_leak,
        top_leak_categories=top_leak_categories,
        recommended_drill_focus=recommended_drill_focus,
        summary_headline=render_session_summary_headline(most_common_leak),
        summary_text=render_session_summary_text(most_common_leak, recommended_drill_focus),
    )
