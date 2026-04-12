from __future__ import annotations

from collections.abc import Iterable

from app.models.coach_api_models import (
    AnalyzedHandRecord,
    CompareCandidate,
    HoldLabel,
)
from app.native import NativeVideoPokerClient, hold_cards_from_mask
from app.services.coach.classifiers import (
    classify_hold_label,
    classify_leak_category,
)
from app.services.coach.renderers import render_compare_explanation


def hold_mask_from_cards(hand: list[str], hold_cards: Iterable[str]) -> int:
    hold_set = set(hold_cards)
    mask = 0
    for idx, card in enumerate(hand):
        if card in hold_set:
            mask |= 1 << idx
    return mask


def build_compare_candidates(
    *,
    native_client: NativeVideoPokerClient,
    variant: str,
    hand: list[str],
    bet: int,
    top_n: int,
) -> list[CompareCandidate]:
    ranked_candidates: list[CompareCandidate] = []
    best_mask, best_ev = native_client.calculate_optimal_play(variant=variant, hand=hand, bet=bet)

    for mask in range(32):
        analysis = native_client.analyze_player_hold(variant=variant, hand=hand, bet=bet, player_mask=mask)
        explanation = native_client.explain_hold(hand=hand, hold_mask=mask)
        label = classify_hold_label(explanation["category"])
        ranked_candidates.append(
            CompareCandidate(
                rank=0,
                hold_cards=hold_cards_from_mask(hand, mask),
                label=label,
                ev=round(float(analysis["player_ev"]), 6),
                ev_gap_from_best=round(float(analysis["ev_delta"]), 6),
                headline=explanation["headline"],
                summary=explanation["summary"],
                pattern_tip=explanation["pattern_tip"] or None,
                explanation="",
            )
        )

    ranked_candidates.sort(key=lambda item: (-item.ev, len(item.hold_cards), item.hold_cards))

    if ranked_candidates:
        best_candidate = ranked_candidates[0]
        if best_mask != hold_mask_from_cards(hand, best_candidate.hold_cards):
            for idx, candidate in enumerate(ranked_candidates):
                if hold_mask_from_cards(hand, candidate.hold_cards) == best_mask:
                    ranked_candidates[0], ranked_candidates[idx] = ranked_candidates[idx], ranked_candidates[0]
                    best_candidate = ranked_candidates[0]
                    break
        best_candidate.ev = round(best_ev, 6)
        best_candidate.ev_gap_from_best = 0.0

    for rank, candidate in enumerate(ranked_candidates, start=1):
        candidate.rank = rank
        candidate.explanation = render_compare_explanation(candidate, ranked_candidates[0])

    return ranked_candidates[:top_n]


def analyze_hand_decision(
    *,
    native_client: NativeVideoPokerClient,
    variant: str,
    hand: list[str],
    bet: int,
    player_hold_cards: list[str] | None = None,
    top_n: int | None = None,
) -> AnalyzedHandRecord:
    best_mask, best_ev = native_client.calculate_optimal_play(variant=variant, hand=hand, bet=bet)
    solver_explanation = native_client.explain_hold(hand=hand, hold_mask=best_mask)
    solver_best_label = classify_hold_label(solver_explanation["category"])

    player_hold_label: HoldLabel | None = None
    player_ev: float | None = None
    mistake_cost: float | None = None
    mistake_severity = None
    leak_category = None
    player_mask: int | None = None

    if player_hold_cards is not None:
        player_mask = hold_mask_from_cards(hand, player_hold_cards)
        player_explanation = native_client.explain_hold(hand=hand, hold_mask=player_mask)
        player_hold_label = classify_hold_label(player_explanation["category"])
        analysis = native_client.analyze_player_hold(
            variant=variant,
            hand=hand,
            bet=bet,
            player_mask=player_mask,
        )
        player_ev = round(float(analysis["player_ev"]), 6)
        mistake_cost = round(float(analysis["ev_delta"]), 6)
        mistake_severity = analysis["severity"]
        leak_category = classify_leak_category(
            solver_best_label=solver_best_label,
            player_hold_label=player_hold_label,
        )

    top_alternatives = None
    if top_n is not None:
        top_alternatives = build_compare_candidates(
            native_client=native_client,
            variant=variant,
            hand=hand,
            bet=bet,
            top_n=top_n,
        )

    return AnalyzedHandRecord(
        variant=variant,
        hand=hand,
        bet=bet,
        solver_best_hold_cards=hold_cards_from_mask(hand, best_mask),
        solver_best_label=solver_best_label,
        solver_best_ev=round(best_ev, 6),
        player_hold_cards=player_hold_cards,
        player_hold_label=player_hold_label,
        player_ev=player_ev,
        mistake_cost=mistake_cost,
        mistake_severity=mistake_severity,
        leak_category=leak_category,
        top_alternatives=top_alternatives,
    )
