import unittest

from fastapi.testclient import TestClient

from main import create_app
from tests.test_coach_services import FakeNativeClient


class CoachRouteTests(unittest.TestCase):
    def test_coach_routes_registered_and_compare_schema(self):
        app = create_app(native_client=FakeNativeClient(), load_native_on_startup=False)
        with TestClient(app) as client:
            openapi = client.get("/openapi.json")
            self.assertEqual(openapi.status_code, 200)
            paths = openapi.json()["paths"]
            self.assertIn("/v1/video-poker/strategy", paths)
            self.assertIn("/v1/poker/evaluate", paths)
            self.assertIn("/v1/coach/compare", paths)
            self.assertIn("/v1/coach/session-summary", paths)
            self.assertIn("/v1/coach/drill-recommendation", paths)

            response = client.post(
                "/v1/coach/compare",
                json={
                    "variant": "jacks_or_better_9_6",
                    "hand": ["Ah", "Kh", "Qh", "Jh", "2c"],
                    "bet": 5,
                    "top_n": 3,
                },
            )
            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual(payload["best_hold_label"], "four_to_royal")
            self.assertEqual(payload["candidates"][0]["headline"], "Four to a royal flush")
            self.assertIn("pattern_tip", payload["candidates"][0])

    def test_strategy_route_success(self):
        app = create_app(native_client=FakeNativeClient(), load_native_on_startup=False)
        with TestClient(app) as client:
            response = client.post(
                "/v1/video-poker/strategy",
                json={
                    "variant": "jacks_or_better_9_6",
                    "hand": ["Ah", "Kh", "Qh", "Jh", "2c"],
                    "bet": 5,
                    "engine": "solver",
                },
            )
            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual(payload["variant"], "jacks_or_better_9_6")
            self.assertEqual(payload["hold"], ["Ah", "Kh", "Qh", "Jh"])
            self.assertEqual(payload["ev"], 18.5)
            self.assertEqual(payload["ev_per_coin"], 3.7)

    def test_strategy_route_validates_ml_model_path(self):
        app = create_app(native_client=FakeNativeClient(), load_native_on_startup=False)
        with TestClient(app) as client:
            response = client.post(
                "/v1/video-poker/strategy",
                json={
                    "variant": "jacks_or_better_9_6",
                    "hand": ["Ah", "Kh", "Qh", "Jh", "2c"],
                    "bet": 5,
                    "engine": "ml",
                },
            )
            self.assertEqual(response.status_code, 400)
            self.assertIn("model_path is required", response.json()["detail"])

    def test_strategy_route_validates_variant(self):
        app = create_app(native_client=FakeNativeClient(), load_native_on_startup=False)
        with TestClient(app) as client:
            response = client.post(
                "/v1/video-poker/strategy",
                json={
                    "variant": "bad_variant",
                    "hand": ["Ah", "Kh", "Qh", "Jh", "2c"],
                    "bet": 5,
                    "engine": "solver",
                },
            )
            self.assertEqual(response.status_code, 400)
            self.assertIn("invalid variant", response.json()["detail"])

    def test_evaluate_route_success(self):
        app = create_app(native_client=FakeNativeClient(), load_native_on_startup=False)
        with TestClient(app) as client:
            response = client.post(
                "/v1/poker/evaluate",
                json={
                    "hand": ["Ah", "Kh", "Qh", "Jh", "10h"],
                },
            )
            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual(payload["hand_name"], "Royal Flush")
            self.assertEqual(payload["rank_value"], 1)
