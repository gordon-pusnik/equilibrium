import json
import unittest
from pathlib import Path

from app.models.coach_api_models import (
    CompareRequest,
    DrillCategory,
    LeakCategory,
    MistakeSeverity,
    SessionSummaryRequest,
)
from app.native import VPEvaluation
from app.services.coach.compare_service import build_compare_result
from app.services.coach.drill_recommendation_service import build_drill_recommendation
from app.services.coach.session_summary_service import build_session_summary


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "session_hands.json"


class FakeNativeClient:
    def __init__(self) -> None:
        self.best_mask = 0b01111
        self.best_ev = 18.5
        self.lib = FakeLib(self)

    def validate_variant(self, variant: str) -> None:
        if variant not in {"jacks_or_better_9_6", "jacks_or_better_8_5"}:
            raise ValueError("invalid variant")

    def load(self) -> None:
        return None

    def calculate_optimal_play(self, *, variant: str, hand: list[str], bet: int):
        self.validate_variant(variant)
        return self.best_mask, self.best_ev

    def analyze_player_hold(self, *, variant: str, hand: list[str], bet: int, player_mask: int):
        self.validate_variant(variant)
        ev_map = {
            0b01111: 18.5,
            0b00111: 3.2,
            0b00011: 1.9,
            0b00001: 0.7,
            0b00000: 0.2,
        }
        player_ev = ev_map.get(player_mask, round(0.05 * bin(player_mask).count("1"), 6))
        ev_delta = round(self.best_ev - player_ev, 6)
        if ev_delta <= 0:
            severity = "perfect"
        elif ev_delta <= 0.0499:
            severity = "very_close"
        elif ev_delta <= 0.1499:
            severity = "small_leak"
        elif ev_delta <= 0.3499:
            severity = "moderate"
        else:
            severity = "major"
        return {
            "best_mask": self.best_mask,
            "best_ev": self.best_ev,
            "player_ev": player_ev,
            "ev_delta": ev_delta,
            "severity": severity,
        }

    def explain_hold(self, *, hand: list[str], hold_mask: int):
        explanations = {
            0b01111: {
                "category": "four_to_royal",
                "headline": "Four to a royal flush",
                "summary": "Keep the four royal cards because this premium draw has the highest expected value.",
                "pattern_tip": "When you already have four royal cards in one suit, avoid breaking the draw.",
            },
            0b00111: {
                "category": "three_to_royal",
                "headline": "Three to a royal flush",
                "summary": "Three-card royal draws retain some value, but not as much as the made four-card draw.",
                "pattern_tip": "Royal draws improve when more premium cards stay together.",
            },
            0b00011: {
                "category": "two_suited_high_cards",
                "headline": "Two suited high cards",
                "summary": "Two suited high cards are playable, but they trail stronger premium draws.",
                "pattern_tip": "Prefer premium draws before defaulting to high-card combinations.",
            },
            0b00001: {
                "category": "single_high_card",
                "headline": "Single high card",
                "summary": "A lone high card is a weak fallback when better draws are present.",
                "pattern_tip": "High-card holds should not replace stronger made hands or premium draws.",
            },
            0b00000: {
                "category": "garbage_hand",
                "headline": "Discard all five cards",
                "summary": "No worthwhile hold pattern is present here.",
                "pattern_tip": "",
            },
        }
        return explanations.get(
            hold_mask,
            {
                "category": "best_expected_value_hold",
                "headline": "Best expected value hold",
                "summary": "This hold is not one of the core coaching templates.",
                "pattern_tip": "",
            },
        )


class FakeLib:
    def __init__(self, client: FakeNativeClient) -> None:
        self.client = client

    def vp_create(self, seed: int) -> int:
        return 1

    def vp_destroy(self, handle: int) -> None:
        return None

    def vp_set_variant(self, handle: int, variant: bytes) -> int:
        self.client.validate_variant(variant.decode("utf-8"))
        return 1

    def vp_set_engine(self, handle: int, engine: bytes) -> int:
        return 1 if engine.decode("utf-8") in {"solver", "rule", "ml"} else 0

    def vp_set_ml_model(self, handle: int, model_path: bytes) -> int:
        return 1 if model_path.decode("utf-8") else 0

    def vp_calculate_optimal_play(self, handle: int, bet: int, suits, ranks, out_mask) -> float:
        out_mask._obj.value = self.client.best_mask
        return self.client.best_ev

    def vp_evaluate_hand(self, suits, ranks, out_eval) -> None:
        rank_values = sorted(int(ranks[idx]) for idx in range(5))
        suit_values = [int(suits[idx]) for idx in range(5)]
        evaluation = out_eval._obj
        assert isinstance(evaluation, VPEvaluation)
        if rank_values == [10, 11, 12, 13, 14] and len(set(suit_values)) == 1:
            hand_name = "Royal Flush"
            rank_value = 1
        else:
            hand_name = "High Card"
            rank_value = 10
        encoded = hand_name.encode("utf-8")
        evaluation.hand_name = encoded + (b"\0" * (64 - len(encoded)))
        evaluation.rank_value = rank_value


def load_fixture_hands():
    payload = json.loads(FIXTURE_PATH.read_text())
    return SessionSummaryRequest.model_validate(payload).hands


class CoachServiceTests(unittest.TestCase):
    def test_compare_service_returns_solver_ranked_candidates(self):
        result = build_compare_result(
            native_client=FakeNativeClient(),
            request=CompareRequest(
                variant="jacks_or_better_9_6",
                hand=["Ah", "Kh", "Qh", "Jh", "2c"],
                bet=5,
                top_n=3,
            ),
        )

        self.assertEqual(result.best_hold_label.value, "four_to_royal")
        self.assertEqual(result.best_hold_cards, ["Ah", "Kh", "Qh", "Jh"])
        self.assertEqual(result.candidates[0].ev, 18.5)
        self.assertEqual(result.candidates[1].label.value, "three_to_royal")
        self.assertEqual(result.candidates[1].ev_gap_from_best, 15.3)
        self.assertIn("highest expected value", result.candidates[0].explanation)

    def test_session_summary_aggregates_repeated_leaks(self):
        summary = build_session_summary(hands=load_fixture_hands())

        self.assertEqual(summary.hands_played, 5)
        self.assertEqual(summary.perfect_count, 1)
        self.assertEqual(summary.accuracy_rate, 0.2)
        self.assertEqual(summary.total_ev_lost, 1.79)
        self.assertIsNotNone(summary.biggest_mistake)
        self.assertEqual(summary.biggest_mistake.mistake_severity, MistakeSeverity.MAJOR)
        self.assertEqual(summary.most_common_leak, LeakCategory.BREAKING_MADE_PAIRS)
        self.assertEqual(summary.top_leak_categories[0].count, 2)
        self.assertEqual(summary.recommended_drill_focus, DrillCategory.MADE_HAND_PRESERVATION)

    def test_drill_recommendation_is_reproducible(self):
        hands = load_fixture_hands()
        first = build_drill_recommendation(hands=hands)
        second = build_drill_recommendation(hands=list(reversed(hands)))

        self.assertEqual(first.recommended_category, DrillCategory.MADE_HAND_PRESERVATION)
        self.assertEqual(first.recommended_category, second.recommended_category)
        self.assertEqual(first.priority, second.priority)
        self.assertEqual(first.supporting_stats.total_ev_lost, 0.99)
        self.assertTrue(first.secondary_recommendations)
