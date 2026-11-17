"""Run after bash ./build.sh: python3 -B -m unittest discover -s poker-core/tests -v."""
import importlib.util
import itertools
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
DRIVER = ROOT / "poker-core/python/benchmark_ml.py"
NATIVE = ROOT / "build/benchmark_ml"
FIXTURE = ROOT / "poker-core/tests/fixtures/benchmark_hands.json"
spec = importlib.util.spec_from_file_location("benchmark_ml", DRIVER)
bench = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bench)


def constant_model(mask):
    return {"input_size": 286, "hidden_size": 1, "output_size": 5,
            "W1": [[0.0] * 286], "b1": [0.0], "W2": [[0.0] for _ in range(5)],
            "b2": [1.0 if mask & (1 << i) else -1.0 for i in range(5)]}


class BenchmarkTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.tmp = Path(self.directory.name)
        self.model = self.tmp / "model.json"
        self.model.write_text(json.dumps(constant_model(31)))
        self.hands = [bench.hand_ids(row["initial"]) for row in json.loads(FIXTURE.read_text())["samples"]]

    def test_canonicalization_all_orders_and_suit_renamings(self):
        # Repeated ranks and multiple cards per suit defeat simplistic first-seen suit maps.
        ids = [0, 1, 13, 27, 42]
        key = bench.hand_key(ids)
        for suits in itertools.permutations(range(4)):
            renamed = [suits[c // 13] * 13 + c % 13 for c in ids]
            for order in itertools.permutations(renamed):
                self.assertEqual(bench.hand_key(order), key)
        self.assertNotEqual(bench.hand_key([0, 1, 13, 27, 43]), key)

    def test_sampling_is_repeatable_and_respects_exclusions(self):
        first, _ = bench.sample_hands(100, 12345, set())
        self.assertEqual(first, bench.sample_hands(100, 12345, set())[0])
        excluded = {bench.hand_key(first[0])}
        hands, rejected = bench.sample_hands(100, 12345, excluded)
        self.assertGreaterEqual(rejected, 1)
        self.assertTrue(all(bench.hand_key(h) not in excluded for h in hands))
        self.assertTrue(all(len(set(h)) == 5 for h in hands))

    def test_exclusion_loading_and_replay_rejection(self):
        path = self.tmp / "training.jsonl"
        renamed = [((c // 13 + 1) % 4) * 13 + c % 13 for c in self.hands[0]][::-1]
        path.write_text(json.dumps({"initial": bench.initial_cards(renamed)}) + "\n")
        exclusions, metadata = bench.load_exclusions([path])
        self.assertEqual(metadata[0]["rows"], 1)
        self.assertEqual(metadata[0]["sha256"], bench.sha256(path))
        with self.assertRaisesRegex(ValueError, "excluded"):
            bench.load_replay(FIXTURE, bench.VARIANTS[0], 5, exclusions)
        path.write_text('{"initial": []}\n')
        with self.assertRaisesRegex(ValueError, "invalid training hand"):
            bench.load_exclusions([path])

    def test_invalid_cards_models_and_replay_contract(self):
        for initial in ([], [{"s": 1, "r": 2}] * 5,
                        [{"s": True, "r": 2}] + bench.initial_cards(self.hands[0][1:])):
            with self.assertRaises(ValueError):
                bench.hand_ids(initial)
        for update in ({"hidden_size": 0}, {"output_size": 6}, {"b2": [float("nan")] * 5},
                       {"W1": [[0.0]]}, {"b1": [1e100]}):
            self.model.write_text(json.dumps({**constant_model(31), **update}))
            with self.assertRaises(ValueError):
                bench.validate_model(self.model)
        with self.assertRaisesRegex(ValueError, "variant and bet"):
            bench.load_replay(FIXTURE, bench.VARIANTS[1], 5, set())
        invalid_replay = self.tmp / "invalid-replay.json"
        for contents in ([], {"samples": None},
                         {"variant": bench.VARIANTS[0], "bet": 5, "samples": [None]},
                         {"variant": bench.VARIANTS[0], "bet": 5, "samples": []}):
            invalid_replay.write_text(json.dumps(contents))
            with self.assertRaises(ValueError):
                bench.load_replay(invalid_replay, bench.VARIANTS[0], 5, set())

    def test_native_ties_and_analytical_inferior_hold(self):
        samples = bench.score_hands(NATIVE, self.model, bench.VARIANTS[0], 5, self.hands)
        royal, quads = samples
        self.assertEqual(royal["solver_ev"], 4000)
        self.assertEqual(royal["normalized_regret"], 0)
        self.assertEqual(quads["solver_ev"], 125)
        self.assertEqual(quads["model_ev"], 125)
        self.assertNotEqual(quads["model_mask"], quads["solver_mask"])
        summary = bench.summarize(samples, 5)
        self.assertEqual(summary["ev_optimal_agreement"], 1)
        self.assertEqual(summary["exact_mask_agreement"], 0.5)
        self.assertEqual(summary["worst_mistakes"], [])
        self.model.write_text(json.dumps(constant_model(15)))
        for variant in bench.VARIANTS:
            for bet, royal_payout, held_four_ev in ((5, 4000, 625 / 47), (1, 250, 125 / 47)):
                row = bench.score_hands(NATIVE, self.model, variant, bet, self.hands[:1])[0]
                self.assertEqual(row["solver_ev"], royal_payout)
                # Discarding the initial ace prevents drawing that royal again:
                # holding TJQK yields a straight flush, 7 flushes,
                # 6 other straights and 9 paying pairs across the 47 draws.
                # 8/5 changes the seven flush payouts from 6 to 5 per coin.
                expected = held_four_ev - (7 * bet / 47 if variant == bench.VARIANTS[1] else 0)
                self.assertAlmostEqual(row["model_ev"], expected)
                self.assertAlmostEqual(row["normalized_regret"], (royal_payout - expected) / bet)

    def test_solver_native_baseline_and_worker_errors(self):
        payload = "".join(" ".join(map(str, h)) + "\n" for h in self.hands)
        result = subprocess.run([str(NATIVE), "--engine", "solver"], input=payload,
                                text=True, capture_output=True, check=True)
        for line in result.stdout.splitlines():
            mask, best, best_ev, selected_ev, _ = line.split("\t")
            self.assertEqual(mask, best)
            self.assertEqual(float(best_ev), float(selected_ev))
        for args, data in [(["--engine", "bad"], ""), (["--variant", "bad"], ""),
                           (["--bet", "0"], ""), (["--engine", "solver"], "0 0 1 2 3\n"),
                           (["--engine", "solver"], "0 1 2 3 52\n"),
                           (["--engine", "solver"], "0 1 2 3 4 extra\n"),
                           (["--ml-model", str(self.tmp / "missing.json")], "")]:
            result = subprocess.run([str(NATIVE), *args], input=data, text=True, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("benchmark_ml:", result.stderr)

    def test_summary_normalization_uncertainty_and_reconciliation(self):
        samples = [
            {"index": 0, "initial_category": "a", "normalized_regret": 0.0,
             "model_mask": 15, "solver_mask": 31, "model_ev": 5.0, "solver_ev": 5.0},
            {"index": 1, "initial_category": "b", "normalized_regret": 0.2,
             "model_mask": 0, "solver_mask": 31, "model_ev": 4.0, "solver_ev": 5.0},
        ]
        summary = bench.summarize(samples, 5)
        self.assertAlmostEqual(summary["mean_normalized_regret"], 0.1)
        self.assertAlmostEqual(summary["rtp_gap_percentage_points"], 10)
        self.assertAlmostEqual(summary["regret_standard_error"], 0.1)
        self.assertAlmostEqual(summary["regret_approx_95_ci"][1], 0.296)
        self.assertEqual(summary["ev_optimal_agreement"], 0.5)
        self.assertEqual(summary["exact_mask_agreement"], 0)
        self.assertAlmostEqual(sum(c["contribution_to_mean_regret"] for c in summary["categories"]), 0.1)
        self.assertEqual(summary["worst_mistakes"][0]["index"], 1)
        self.assertIsNone(bench.summarize(samples[:1], 5)["regret_standard_error"])
        near_tie = {**samples[0], "normalized_regret": bench.OPTIMAL_TOLERANCE / 2}
        self.assertEqual(bench.summarize([near_tie], 5)["ev_optimal_agreement"], 1)

    def test_cli_replay_metadata_and_invalid_arguments(self):
        first, second = self.tmp / "first.json", self.tmp / "second.json"
        base = [sys.executable, "-B", str(DRIVER), "--ml-model", str(self.model),
                "--variant", bench.VARIANTS[0]]
        subprocess.run([*base, "--input", str(FIXTURE), "--output", str(first)],
                       capture_output=True, text=True, check=True)
        subprocess.run([*base, "--input", str(first), "--output", str(second)],
                       capture_output=True, text=True, check=True)
        a, b = json.loads(first.read_text()), json.loads(second.read_text())
        self.assertEqual(a["samples"], b["samples"])
        self.assertEqual(a["summary"], b["summary"])
        self.assertEqual(a["model"]["sha256"], bench.sha256(self.model))
        self.assertEqual(a["native_sha256"], bench.sha256(NATIVE))
        self.assertEqual(a["evaluation_scope"], "replayed_hands")
        self.assertIsNone(a["sampling"]["seed"])
        for arguments in (["--hands", "0"], ["--bet", "6"], ["--variant", "invalid"],
                          ["--hands", "1", "--input", str(FIXTURE)]):
            result = subprocess.run([*base, "--output", str(first), *arguments], capture_output=True)
            self.assertNotEqual(result.returncode, 0)
        before = self.model.read_bytes()
        result = subprocess.run([*base, "--hands", "1", "--output", str(self.model)], capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.model.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
