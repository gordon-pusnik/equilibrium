from __future__ import annotations

from collections import defaultdict

from app.models.coach_api_models import (
    AnalyzedHandRecord,
    DrillRecommendation,
    DrillSupportingStats,
    SecondaryDrillRecommendation,
)
from app.services.coach.mappings import drill_for_leak, drill_priority
from app.services.coach.renderers import render_drill_focus, render_drill_reason


def build_drill_recommendation(*, hands: list[AnalyzedHandRecord]) -> DrillRecommendation:
    leak_totals: dict[object, dict[str, float]] = defaultdict(lambda: {"count": 0, "ev": 0.0})
    for hand in hands:
        if hand.leak_category is None:
            continue
        leak_totals[hand.leak_category]["count"] += 1
        leak_totals[hand.leak_category]["ev"] += float(hand.mistake_cost or 0.0)

    if not leak_totals:
        fallback_drill = drill_for_leak(None)
        return DrillRecommendation(
            recommended_category=fallback_drill,
            priority="low",
            reason=render_drill_reason(fallback_drill, occurrences=0, total_ev_lost=0.0),
            supporting_stats=DrillSupportingStats(occurrences=0, total_ev_lost=0.0, average_ev_lost=0.0),
            suggested_focus=render_drill_focus(fallback_drill),
            secondary_recommendations=[],
        )

    ranked_leaks = sorted(
        leak_totals.items(),
        key=lambda item: (-item[1]["ev"], -item[1]["count"], item[0].value),
    )
    primary_leak, primary_values = ranked_leaks[0]
    primary_drill = drill_for_leak(primary_leak)
    occurrences = int(primary_values["count"])
    total_ev_lost = round(primary_values["ev"], 6)
    average_ev_lost = round(total_ev_lost / occurrences, 6)

    secondaries = []
    for leak, values in ranked_leaks[1:3]:
        drill = drill_for_leak(leak)
        secondaries.append(
            SecondaryDrillRecommendation(
                category=drill,
                priority=drill_priority(
                    occurrences=int(values["count"]),
                    total_ev_lost=float(values["ev"]),
                ),
            )
        )

    return DrillRecommendation(
        recommended_category=primary_drill,
        priority=drill_priority(occurrences=occurrences, total_ev_lost=total_ev_lost),
        reason=render_drill_reason(primary_drill, occurrences=occurrences, total_ev_lost=total_ev_lost),
        supporting_stats=DrillSupportingStats(
            occurrences=occurrences,
            total_ev_lost=total_ev_lost,
            average_ev_lost=average_ev_lost,
        ),
        suggested_focus=render_drill_focus(primary_drill),
        secondary_recommendations=secondaries,
    )
