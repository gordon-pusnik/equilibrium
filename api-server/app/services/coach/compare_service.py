from __future__ import annotations

from app.models.coach_api_models import CompareRequest, CompareResult
from app.native import NativeVideoPokerClient
from app.services.coach.analysis_adapter import build_compare_candidates


def build_compare_result(
    *,
    native_client: NativeVideoPokerClient,
    request: CompareRequest,
) -> CompareResult:
    top_n = max(1, min(request.top_n, 10))
    candidates = build_compare_candidates(
        native_client=native_client,
        variant=request.variant,
        hand=request.hand,
        bet=request.bet,
        top_n=top_n,
    )
    best_candidate = candidates[0]
    return CompareResult(
        variant=request.variant,
        hand=request.hand,
        best_hold_cards=best_candidate.hold_cards,
        best_hold_label=best_candidate.label,
        best_ev=best_candidate.ev,
        candidates=candidates,
    )
