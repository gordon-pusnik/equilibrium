"""Paired solver-regret comparisons must use the same ordered deals."""
import copy
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))
from compare_ml_benchmarks import compare
from ml_data import VARIANTS, initial_cards


def report(model_evs):
    return {
        "variant": VARIANTS[0], "bet": 5,
        "samples": [
            {"initial": initial_cards([0, 14, 28, 42, 4 + i]),
             "initial_category": "pair" if i == 1 else "high_card",
             "solver_ev": 5, "solver_mask": 3, "model_ev": model_ev, "model_mask": 7}
            for i, model_ev in enumerate(model_evs)
        ],
    }


class ComparisonTests(unittest.TestCase):
    def test_paired_mean_interval_categories_and_regressions(self):
        result = compare(report([3, 4, 5]), report([5, 3.5, 5]))
        self.assertAlmostEqual(result["mean_improvement"], 0.1)
        self.assertAlmostEqual(result["improvement_percentage_points"], 10)
        se = math.sqrt(0.07 / 3)
        self.assertAlmostEqual(result["paired_standard_error"], se)
        self.assertAlmostEqual(result["paired_approx_95_ci"][0], 0.1 - 1.96 * se)
        self.assertAlmostEqual(result["paired_approx_95_ci"][1], 0.1 + 1.96 * se)
        contributions = {r["initial_category"]: r["contribution_to_mean_improvement"]
                         for r in result["categories"]}
        self.assertAlmostEqual(contributions["high_card"], 0.4 / 3)
        self.assertAlmostEqual(contributions["pair"], -0.1 / 3)
        self.assertEqual([r["index"] for r in result["worst_regressions"]], [1])
        self.assertAlmostEqual(result["worst_regressions"][0]["improvement"], -0.1)
        self.assertIsNone(compare(report([3]), report([5]))["paired_approx_95_ci"])

    def test_reject_incompatible_reports(self):
        baseline = report([3, 4, 5])
        for field, value, reason in (("variant", VARIANTS[1], "variant"),
                                     ("bet", 1, "bet"), ("bet", 5.0, "bet"),
                                     ("samples", [], "sample count")):
            with self.subTest(field=field, value=value):
                with self.assertRaisesRegex(ValueError, reason):
                    compare(baseline, {**baseline, field: value})
        for field, value, reason in (
            ("initial", baseline["samples"][0]["initial"][::-1], "ordered hands"),
            ("initial_category", "pair", "categories"),
            ("solver_ev", 6, "solver EVs"),
            ("model_ev", float("nan"), "finite"),
            ("model_ev", 6, "exceeds"),
        ):
            with self.subTest(field=field, value=value):
                candidate = copy.deepcopy(baseline)
                candidate["samples"][0][field] = value
                with self.assertRaisesRegex(ValueError, reason):
                    compare(baseline, candidate)
        candidate = {**baseline, "samples": baseline["samples"][::-1]}
        with self.assertRaisesRegex(ValueError, "ordered hands"):
            compare(baseline, candidate)
