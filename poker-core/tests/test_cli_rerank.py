"""Native reranker smoke and Python-checkpoint hold parity cases (build first)."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
VARIANTS = {"96": "jacks_or_better_9_6", "85": "jacks_or_better_8_5"}
# Saved fold-0 decisions, including several real reranker flips and made hands.
CASES = {
    "96": [([41, 16, 19, 35, 51], 24), ([0, 17, 21, 35, 51], 24),
           ([41, 29, 34, 36, 51], 24), ([31, 32, 33, 48, 50], 7),
           ([40, 42, 44, 47, 48], 31)],
    "85": [([39, 41, 18, 32, 45], 24), ([26, 27, 29, 44, 48], 7),
           ([29, 45, 46, 35, 49], 24), ([13, 14, 15, 31, 49], 7),
           ([42, 44, 46, 49, 50], 31)],
}


def run(binary, args, deals=()):
    return subprocess.run(
        [str(ROOT / "build" / binary), *args], cwd=ROOT,
        input="".join(" ".join(map(str, hand)) + "\n" for hand in deals),
        text=True, capture_output=True, timeout=15,
    )


def options(pay, model=None):
    return ["--engine", "ml-rerank", "--variant", VARIANTS[pay],
            "--ml-model", str(model or f"ml/rerank-job{pay}.json")]


class CliRerankTests(unittest.TestCase):
    def assert_ok(self, result):
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)

    def test_native_masks_match_saved_fold_and_remap(self):
        for pay, fixtures in CASES.items():
            with self.subTest(pay=pay):
                cases = fixtures + [([(card + 13) % 52 for card in reversed(cards)],
                                     sum(1 << (4 - i) for i in range(5) if mask & (1 << i)))
                                    for cards, mask in fixtures]
                result = run("benchmark_ml", [*options(pay), "--masks-only"], [cards for cards, _ in cases])
                self.assert_ok(result)
                self.assertEqual(list(map(int, result.stdout.splitlines())), [mask for _, mask in cases])

    def test_exact_benchmark_scores_reranker_mask(self):
        hand, mask = CASES["96"][1]
        result = run("benchmark_ml", options("96"), [hand])
        self.assert_ok(result)
        actual, _, best_ev, model_ev, category = result.stdout.strip().split("\t")
        self.assertEqual(int(actual), mask)
        self.assertGreater(float(model_ev), 0)
        self.assertGreaterEqual(float(best_ev), float(model_ev))
        self.assertEqual(category, "High Card")

    def test_cli_smoke_and_five_credit_limit(self):
        for binary, pay, tail, wrong_bet in (
            ("videopoker", "96", ["100", "5", "1"], ["100", "1", "1"]),
            ("verify_rtp", "85", ["10", "1", "5"], ["10", "1", "1"]),
        ):
            with self.subTest(binary=binary):
                self.assert_ok(run(binary, [*options(pay), *tail]))
                result = run(binary, [*options(pay), *wrong_bet])
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("five-credit", result.stdout + result.stderr)

    def test_rejects_paytable_mismatch_and_bad_bundle(self):
        mismatch = run("verify_rtp", [*options("85", "ml/rerank-job96.json"), "1", "1"])
        self.assertNotEqual(mismatch.returncode, 0)
        self.assertIn("bundle is for jacks_or_better_9_6, not jacks_or_better_8_5", mismatch.stdout)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "bad.json"
            path.write_text(json.dumps(["equilibrium-ml-rerank-v1", VARIANTS["96"], 5, 1, 0, [0], [0]]))
            bad = run("videopoker", [*options("96", path), "100", "5", "1"])
            self.assertNotEqual(bad.returncode, 0)
            self.assertIn("invalid ml-rerank bundle", bad.stdout)


if __name__ == "__main__":
    unittest.main()
