from __future__ import annotations

import ctypes
from typing import List

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.native import VPEvaluation, parse_card


class EvaluateRequest(BaseModel):
    hand: List[str] = Field(..., min_length=5, max_length=5, description="List of 5 card strings, e.g., ['Ah', 'Kh', 'Qh', 'Jh', '10h']")


class EvaluateResponse(BaseModel):
    hand_name: str
    rank_value: int


router = APIRouter(prefix="/v1/poker", tags=["poker"])


@router.post("/evaluate", response_model=EvaluateResponse)
async def evaluate_hand(request: EvaluateRequest, api_request: Request):
    try:
        suits = []
        ranks = []
        for card in request.hand:
            suit, rank = parse_card(card)
            suits.append(suit)
            ranks.append(rank)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    api_request.app.state.native_client.load()
    lib = api_request.app.state.native_client.lib
    c_suits = (ctypes.c_uint32 * 5)(*suits)
    c_ranks = (ctypes.c_uint32 * 5)(*ranks)
    out_eval = VPEvaluation()
    lib.vp_evaluate_hand(c_suits, c_ranks, ctypes.byref(out_eval))
    return {
        "hand_name": out_eval.hand_name.decode("utf-8"),
        "rank_value": out_eval.rank_value,
    }
