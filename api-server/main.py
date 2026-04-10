import os
import ctypes
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

# Constants matching C++ enums
SUITS = {"s": 1, "c": 2, "h": 3, "d": 4}
RANKS = {
    "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9, "10": 10,
    "j": 11, "q": 12, "k": 13, "a": 14
}

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

class EvaluateRequest(BaseModel):
    hand: List[str] = Field(..., min_length=5, max_length=5, description="List of 5 card strings, e.g., ['Ah', 'Kh', 'Qh', 'Jh', '10h']")

class EvaluateResponse(BaseModel):
    hand_name: str
    rank_value: int

class VPEvaluation(ctypes.Structure):
    _fields_ = [
        ("hand_name", ctypes.c_char * 64),
        ("rank_value", ctypes.c_uint32)
    ]

app = FastAPI(title="Video Poker API")

# Path to the shared library
LIB_PATH = os.path.join(os.path.dirname(__file__), "libvideopoker.so")
lib = None

def load_lib():
    global lib
    if not os.path.exists(LIB_PATH):
        raise RuntimeError(f"Shared library not found at {LIB_PATH}. Build it first.")
    
    lib = ctypes.CDLL(LIB_PATH)
    
    # VPHandle vp_create(uint64_t seed);
    lib.vp_create.restype = ctypes.c_void_p
    lib.vp_create.argtypes = [ctypes.c_uint64]
    
    # void vp_destroy(VPHandle handle);
    lib.vp_destroy.argtypes = [ctypes.c_void_p]

    # int vp_set_engine(VPHandle handle, const char* engine_name);
    lib.vp_set_engine.restype = ctypes.c_int
    lib.vp_set_engine.argtypes = [ctypes.c_void_p, ctypes.c_char_p]

    # int vp_set_variant(VPHandle handle, const char* variant_id);
    lib.vp_set_variant.restype = ctypes.c_int
    lib.vp_set_variant.argtypes = [ctypes.c_void_p, ctypes.c_char_p]

    # int vp_set_ml_model(VPHandle handle, const char* model_path);
    lib.vp_set_ml_model.restype = ctypes.c_int
    lib.vp_set_ml_model.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
    
    # double vp_calculate_optimal_play(VPHandle handle, uint32_t bet, const uint32_t* suits, const uint32_t* ranks, uint32_t* out_mask);
    lib.vp_calculate_optimal_play.restype = ctypes.c_double
    lib.vp_calculate_optimal_play.argtypes = [
        ctypes.c_void_p, 
        ctypes.c_uint32, 
        ctypes.POINTER(ctypes.c_uint32), 
        ctypes.POINTER(ctypes.c_uint32), 
        ctypes.POINTER(ctypes.c_uint32)
    ]

    # void vp_evaluate_hand(const uint32_t* suits, const uint32_t* ranks, VPEvaluation* out_eval);
    lib.vp_evaluate_hand.restype = None
    lib.vp_evaluate_hand.argtypes = [
        ctypes.POINTER(ctypes.c_uint32), 
        ctypes.POINTER(ctypes.c_uint32), 
        ctypes.POINTER(VPEvaluation)
    ]

@app.on_event("startup")
def startup_event():
    load_lib()

@app.get("/")
async def root():
    return {
        "service": "Video Poker API",
        "status": "ok",
        "docs": "/docs",
        "openapi": "/openapi.json",
        "endpoints": [
            "/v1/video-poker/strategy",
            "/v1/poker/evaluate",
        ],
    }

def parse_card(card_str: str):
    card_str = card_str.lower().strip()
    if len(card_str) < 2:
        raise ValueError(f"Invalid card string: {card_str}")
    
    rank_part = card_str[:-1]
    suit_part = card_str[-1]
    
    if rank_part not in RANKS:
        raise ValueError(f"Invalid rank: {rank_part}")
    if suit_part not in SUITS:
        raise ValueError(f"Invalid suit: {suit_part}")
        
    return SUITS[suit_part], RANKS[rank_part]

@app.post("/v1/video-poker/strategy", response_model=StrategyResponse)
async def get_strategy(request: StrategyRequest):
    if request.variant not in ["jacks_or_better_9_6", "jacks_or_better_8_5"]:
        raise HTTPException(status_code=400, detail="Variant must be 'jacks_or_better_9_6' or 'jacks_or_better_8_5'.")
    
    if request.engine not in ["solver", "rule", "ml"]:
        raise HTTPException(status_code=400, detail="Engine must be 'solver', 'rule', or 'ml'.")

    if request.engine == "ml" and not request.model_path:
        raise HTTPException(status_code=400, detail="model_path is required when engine is 'ml'.")

    try:
        suits = []
        ranks = []
        for c in request.hand:
            s, r = parse_card(c)
            suits.append(s)
            ranks.append(r)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    handle = lib.vp_create(0)
    try:
        if not lib.vp_set_variant(handle, request.variant.encode('utf-8')):
            raise HTTPException(status_code=400, detail=f"Invalid variant: {request.variant}")
        lib.vp_set_engine(handle, request.engine.encode('utf-8'))
        if request.engine == "ml" and request.model_path:
            if not lib.vp_set_ml_model(handle, request.model_path.encode('utf-8')):
                raise HTTPException(status_code=400, detail=f"Failed to load ML model from {request.model_path}")

        c_suits = (ctypes.c_uint32 * 5)(*suits)
        c_ranks = (ctypes.c_uint32 * 5)(*ranks)
        out_mask = ctypes.c_uint32(0)
        
        ev = lib.vp_calculate_optimal_play(handle, request.bet, c_suits, c_ranks, ctypes.byref(out_mask))
        
        mask = out_mask.value
        hold_cards = []
        for i in range(5):
            if (mask & (1 << i)) != 0:
                hold_cards.append(request.hand[i])
        
        return {
            "variant": request.variant,
            "hold": hold_cards,
            "ev": round(ev, 6),
            "ev_per_coin": round(ev / request.bet, 6)
        }
    finally:
        lib.vp_destroy(handle)

@app.post("/v1/poker/evaluate", response_model=EvaluateResponse)
async def evaluate_hand(request: EvaluateRequest):
    try:
        suits = []
        ranks = []
        for c in request.hand:
            s, r = parse_card(c)
            suits.append(s)
            ranks.append(r)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    c_suits = (ctypes.c_uint32 * 5)(*suits)
    c_ranks = (ctypes.c_uint32 * 5)(*ranks)
    out_eval = VPEvaluation()
    
    lib.vp_evaluate_hand(c_suits, c_ranks, ctypes.byref(out_eval))
    
    return {
        "hand_name": out_eval.hand_name.decode('utf-8'),
        "rank_value": out_eval.rank_value
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
