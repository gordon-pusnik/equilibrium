from __future__ import annotations

from app.models.coach_api_models import CompareCandidate, DrillCategory, LeakCategory
from app.services.coach.mappings import DRILL_FOCUS_TEXT


LEAK_HEADLINES: dict[LeakCategory, str] = {
    LeakCategory.OVERVALUING_WEAK_FLUSH_DRAWS: "Weak flush-draw decisions are your biggest leak.",
    LeakCategory.BREAKING_MADE_PAIRS: "Breaking made hands is costing you the most value.",
    LeakCategory.OVERVALUING_SINGLE_HIGH_CARDS: "Single high-card decisions are dragging down your results.",
    LeakCategory.MISSING_ROYAL_DRAW_VALUE: "Royal-draw recognition is your biggest missed opportunity.",
    LeakCategory.KEEPING_WEAK_INSIDE_STRAIGHTS: "Weak inside-straight decisions are costing too much EV.",
    LeakCategory.DISCARDING_TOO_AGGRESSIVELY: "Over-discarding is leaving value on the table.",
    LeakCategory.OTHER: "A mixed set of mistakes is costing you expected value.",
}


def render_compare_explanation(candidate: CompareCandidate, best_candidate: CompareCandidate) -> str:
    if candidate.rank == 1:
        return f"This is the strongest play because {candidate.label.value} returns the highest expected value in this spot."
    return (
        f"This option is weaker because it gives up {candidate.ev_gap_from_best:.4f} expected value "
        f"versus the best hold."
    )


def render_session_summary_headline(leak: LeakCategory | None) -> str:
    return LEAK_HEADLINES.get(leak or LeakCategory.OTHER, LEAK_HEADLINES[LeakCategory.OTHER])


def render_session_summary_text(leak: LeakCategory | None, drill: DrillCategory) -> str:
    leak_text = (leak or LeakCategory.OTHER).value.replace("_", " ")
    return (
        f"Your most costly recurring mistake is {leak_text}. "
        f"{DRILL_FOCUS_TEXT[drill]} This is the clearest next area to improve."
    )


def render_drill_reason(drill: DrillCategory, *, occurrences: int, total_ev_lost: float) -> str:
    return (
        f"This category appears {occurrences} times and accounts for {total_ev_lost:.4f} total expected value lost."
    )


def render_drill_focus(drill: DrillCategory) -> str:
    return DRILL_FOCUS_TEXT[drill]
