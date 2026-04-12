from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.models.coach_api_models import (
    CompareRequest,
    CompareResult,
    DrillRecommendation,
    DrillRecommendationRequest,
    SessionSummary,
    SessionSummaryRequest,
)
from app.services.coach.compare_service import build_compare_result
from app.services.coach.drill_recommendation_service import build_drill_recommendation
from app.services.coach.session_summary_service import build_session_summary


router = APIRouter(prefix="/v1/coach", tags=["coach"])


@router.post("/compare", response_model=CompareResult)
def compare_hand(request: CompareRequest, api_request: Request) -> CompareResult:
    try:
        return build_compare_result(native_client=api_request.app.state.native_client, request=request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/session-summary", response_model=SessionSummary)
def session_summary(request: SessionSummaryRequest) -> SessionSummary:
    return build_session_summary(hands=request.hands)


@router.post("/drill-recommendation", response_model=DrillRecommendation)
def drill_recommendation(request: DrillRecommendationRequest) -> DrillRecommendation:
    return build_drill_recommendation(hands=request.hands)
