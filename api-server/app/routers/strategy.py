from __future__ import annotations

import ctypes
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.native import parse_card


class StrategyRequest(BaseModel):
    model_config = {"protected_namespaces": ()}
    variant: str = Field("jacks_or_better_9_6", description="Game variant id")
    hand: List[str] = Field(..., min_length=5, max_length=5, description="List of 5 card strings, e.g., ['Ah', 'Kh', 'Qh', 'Jh', '2c']")
    bet: int = Field(5, ge=1, le=5)
    engine: str = Field("solver", description="Engine type: 'solver', 'rule', or 'ml'")
    model_path: Optional[str] = Field(None, description="Path to ML model JSON file (required if engine is 'ml')")


class StrategyResponse(BaseModel):
    variant: str
    hold: List[str]
    ev: float
    ev_per_coin: float


router = APIRouter(prefix="/v1/video-poker", tags=["video-poker"])


@router.post("/strategy", response_model=StrategyResponse)
async def get_strategy(request: StrategyRequest, api_request: Request):
    if request.engine not in ["solver", "rule", "ml"]:
        raise HTTPException(status_code=400, detail="Engine must be 'solver', 'rule', or 'ml'.")
    if request.engine == "ml" and not request.model_path:
        raise HTTPException(status_code=400, detail="model_path is required when engine is 'ml'.")

    try:
        api_request.app.state.native_client.validate_variant(request.variant)
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
    handle = lib.vp_create(0)
    try:
        if not lib.vp_set_variant(handle, request.variant.encode("utf-8")):
            raise HTTPException(status_code=400, detail=f"Invalid variant: {request.variant}")
        if not lib.vp_set_engine(handle, request.engine.encode("utf-8")):
            raise HTTPException(status_code=400, detail=f"Invalid engine: {request.engine}")
        if request.engine == "ml" and request.model_path:
            if not lib.vp_set_ml_model(handle, request.model_path.encode("utf-8")):
                raise HTTPException(status_code=400, detail=f"Failed to load ML model from {request.model_path}")

        c_suits = (ctypes.c_uint32 * 5)(*suits)
        c_ranks = (ctypes.c_uint32 * 5)(*ranks)
        out_mask = ctypes.c_uint32(0)
        ev = lib.vp_calculate_optimal_play(handle, request.bet, c_suits, c_ranks, ctypes.byref(out_mask))
        mask = out_mask.value
        hold_cards = [card for idx, card in enumerate(request.hand) if (mask & (1 << idx)) != 0]
        return {
            "variant": request.variant,
            "hold": hold_cards,
            "ev": round(float(ev), 6),
            "ev_per_coin": round(float(ev) / request.bet, 6),
        }
    finally:
        lib.vp_destroy(handle)
