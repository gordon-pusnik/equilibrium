from __future__ import annotations

import ctypes
import os
from contextlib import contextmanager


SUITS = {"s": 1, "c": 2, "h": 3, "d": 4}
RANKS = {
    "2": 2,
    "3": 3,
    "4": 4,
    "5": 5,
    "6": 6,
    "7": 7,
    "8": 8,
    "9": 9,
    "10": 10,
    "j": 11,
    "q": 12,
    "k": 13,
    "a": 14,
}
VALID_VARIANTS = {"jacks_or_better_9_6", "jacks_or_better_8_5"}


class VPEvaluation(ctypes.Structure):
    _fields_ = [
        ("hand_name", ctypes.c_char * 64),
        ("rank_value", ctypes.c_uint32),
    ]


class VPHoldExplanation(ctypes.Structure):
    _fields_ = [
        ("category", ctypes.c_char * 64),
        ("headline", ctypes.c_char * 96),
        ("summary", ctypes.c_char * 192),
        ("pattern_tip", ctypes.c_char * 192),
    ]


class VPMistakeAnalysis(ctypes.Structure):
    _fields_ = [
        ("best_mask", ctypes.c_uint32),
        ("best_ev", ctypes.c_double),
        ("player_ev", ctypes.c_double),
        ("ev_delta", ctypes.c_double),
        ("severity", ctypes.c_char * 32),
    ]


def parse_card(card_str: str) -> tuple[int, int]:
    value = card_str.lower().strip()
    if len(value) < 2:
        raise ValueError(f"Invalid card string: {card_str}")
    rank_part = value[:-1]
    suit_part = value[-1]
    if rank_part not in RANKS:
        raise ValueError(f"Invalid rank: {rank_part}")
    if suit_part not in SUITS:
        raise ValueError(f"Invalid suit: {suit_part}")
    return SUITS[suit_part], RANKS[rank_part]


def hold_cards_from_mask(hand: list[str], mask: int) -> list[str]:
    return [card for idx, card in enumerate(hand) if (mask & (1 << idx)) != 0]


class NativeVideoPokerClient:
    def __init__(self, lib_path: str) -> None:
        self.lib_path = lib_path
        self.lib: ctypes.CDLL | None = None

    def load(self) -> None:
        if self.lib is not None:
            return
        if not os.path.exists(self.lib_path):
            raise RuntimeError(f"Shared library not found at {self.lib_path}. Build it first.")
        lib = ctypes.CDLL(self.lib_path)
        lib.vp_create.restype = ctypes.c_void_p
        lib.vp_create.argtypes = [ctypes.c_uint64]
        lib.vp_destroy.argtypes = [ctypes.c_void_p]
        lib.vp_set_engine.restype = ctypes.c_int
        lib.vp_set_engine.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        lib.vp_set_variant.restype = ctypes.c_int
        lib.vp_set_variant.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        lib.vp_calculate_optimal_play.restype = ctypes.c_double
        lib.vp_calculate_optimal_play.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.POINTER(ctypes.c_uint32),
            ctypes.POINTER(ctypes.c_uint32),
            ctypes.POINTER(ctypes.c_uint32),
        ]
        lib.vp_evaluate_hand.restype = None
        lib.vp_evaluate_hand.argtypes = [
            ctypes.POINTER(ctypes.c_uint32),
            ctypes.POINTER(ctypes.c_uint32),
            ctypes.POINTER(VPEvaluation),
        ]
        lib.vp_explain_hold.restype = None
        lib.vp_explain_hold.argtypes = [
            ctypes.POINTER(ctypes.c_uint32),
            ctypes.POINTER(ctypes.c_uint32),
            ctypes.c_uint32,
            ctypes.POINTER(VPHoldExplanation),
        ]
        lib.vp_analyze_player_hold.restype = ctypes.c_int
        lib.vp_analyze_player_hold.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_uint32),
            ctypes.POINTER(ctypes.c_uint32),
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.POINTER(VPMistakeAnalysis),
        ]
        self.lib = lib

    def validate_variant(self, variant: str) -> None:
        if variant not in VALID_VARIANTS:
            raise ValueError("Variant must be 'jacks_or_better_9_6' or 'jacks_or_better_8_5'.")

    def _hand_arrays(self, hand: list[str]) -> tuple[ctypes.Array[ctypes.c_uint32], ctypes.Array[ctypes.c_uint32]]:
        suits: list[int] = []
        ranks: list[int] = []
        for card in hand:
            suit, rank = parse_card(card)
            suits.append(suit)
            ranks.append(rank)
        return (ctypes.c_uint32 * 5)(*suits), (ctypes.c_uint32 * 5)(*ranks)

    @contextmanager
    def solver_handle(self, variant: str):
        self.load()
        assert self.lib is not None
        handle = self.lib.vp_create(0)
        try:
            if not self.lib.vp_set_variant(handle, variant.encode("utf-8")):
                raise ValueError(f"Invalid variant: {variant}")
            if not self.lib.vp_set_engine(handle, b"solver"):
                raise RuntimeError("Failed to set solver engine")
            yield handle
        finally:
            self.lib.vp_destroy(handle)

    def calculate_optimal_play(self, *, variant: str, hand: list[str], bet: int) -> tuple[int, float]:
        self.validate_variant(variant)
        suits, ranks = self._hand_arrays(hand)
        with self.solver_handle(variant) as handle:
            out_mask = ctypes.c_uint32(0)
            ev = self.lib.vp_calculate_optimal_play(handle, bet, suits, ranks, ctypes.byref(out_mask))
            return out_mask.value, float(ev)

    def analyze_player_hold(self, *, variant: str, hand: list[str], bet: int, player_mask: int) -> dict[str, object]:
        self.validate_variant(variant)
        suits, ranks = self._hand_arrays(hand)
        with self.solver_handle(variant) as handle:
            analysis = VPMistakeAnalysis()
            ok = self.lib.vp_analyze_player_hold(handle, suits, ranks, bet, player_mask, ctypes.byref(analysis))
            if ok != 1:
                raise RuntimeError("Failed to analyze player hold")
            return {
                "best_mask": int(analysis.best_mask),
                "best_ev": float(analysis.best_ev),
                "player_ev": float(analysis.player_ev),
                "ev_delta": float(analysis.ev_delta),
                "severity": analysis.severity.decode("utf-8"),
            }

    def explain_hold(self, *, hand: list[str], hold_mask: int) -> dict[str, str]:
        self.load()
        suits, ranks = self._hand_arrays(hand)
        explanation = VPHoldExplanation()
        self.lib.vp_explain_hold(suits, ranks, hold_mask, ctypes.byref(explanation))
        return {
            "category": explanation.category.decode("utf-8"),
            "headline": explanation.headline.decode("utf-8"),
            "summary": explanation.summary.decode("utf-8"),
            "pattern_tip": explanation.pattern_tip.decode("utf-8"),
        }
