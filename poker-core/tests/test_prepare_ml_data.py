"""Deterministic preparation tests; no native build or training required."""
import copy
import json
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
PYTHON = ROOT / "poker-core/python"
sys.path.insert(0, str(PYTHON))
import ml_data as data
import prepare_ml_data as prep


class PreparationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.tmp = Path(self.directory.name)
        self.variant = data.VARIANTS[0]
        self.test_hands = data.sample_hands(20, 12345, set())[0]
        self.test_keys = {data.hand_key(h) for h in self.test_hands}
        self.hands = data.sample_hands(16, 98765, self.test_keys)[0]
        self.assertEqual(len({data.hand_key(h) for h in self.hands}), 16)
        self.sources = [self.tmp / "one.jsonl", self.tmp / "two.jsonl"]
        # Every source contains an equivalent of every class, with different
        # positional targets. Neither splitting by source nor by row is safe.
        self.rows = [self.row(h, i % 32) for i, h in enumerate(self.hands)]
        equivalents = [self.equivalent(row) for row in self.rows]
        self.write_source(self.sources[0], [self.row(self.test_hands[0]), *self.rows])
        self.write_source(self.sources[1], [*equivalents, self.equivalent(self.row(self.test_hands[0]))])

    def row(self, ids, mask=5):
        return {"initial": data.initial_cards(ids), "hold_mask": mask,
                "engine": "solver", "variant": self.variant, "bet": 5}

    def equivalent(self, row):
        ids = data.hand_ids(row["initial"])
        renamed = [((c // 13 + 1) % 4) * 13 + c % 13 for c in ids][::-1]
        mask = sum(1 << (4 - i) for i in range(5) if row["hold_mask"] & (1 << i))
        return {**row, "initial": data.initial_cards(renamed), "hold_mask": mask}

    def write_source(self, path, rows):
        # Include a blank physical line and no final newline to exercise membership
        # and byte hashing independently of JSON serialization of output rows.
        path.write_text("\n" + "\n".join(json.dumps(row) for row in rows), encoding="utf-8")

    def prepare(self, directory="prepared", **overrides):
        config = {"variant": self.variant, "bet": 5, "test_hands": 20,
                  "validation_fraction": 0.25}
        return prep.prepare(self.sources, self.tmp / directory, **{**config, **overrides})

    def test_disjoint_keys_membership_hashes_and_unchanged_rows(self):
        manifest = self.prepare()
        parts = manifest["partitions"]
        key_sets = {name: {tuple(key) for key in part["keys"]} for name, part in parts.items()}
        self.assertFalse(key_sets["train"] & key_sets["validation"])
        self.assertFalse(key_sets["train"] & key_sets["test"])
        self.assertFalse(key_sets["validation"] & key_sets["test"])
        self.assertEqual(parts["train"]["groups"], 12)
        self.assertEqual(parts["validation"]["groups"], 4)
        self.assertEqual(parts["train"]["rows"], 24)
        self.assertEqual(parts["validation"]["rows"], 8)
        excluded = manifest["excluded_test_equivalent"]
        self.assertEqual(excluded["rows"], 2)
        self.assertEqual(excluded["groups"], 1)
        self.assertEqual({tuple(k) for k in excluded["keys"]}, {data.hand_key(self.test_hands[0])})
        self.assertEqual(excluded["members"], [{"source": 0, "line": 2}, {"source": 1, "line": 18}])
        seen = []
        for name in ("train", "validation"):
            part = parts[name]
            path = self.tmp / "prepared" / part["path"]
            self.assertEqual(data.sha256(path), part["sha256"])
            lines = path.read_bytes().splitlines(keepends=True)
            self.assertEqual(len(lines), part["rows"])
            for raw, member in zip(lines, part["members"]):
                source_line = self.sources[member["source"]].read_bytes().splitlines()[member["line"] - 1]
                self.assertEqual(raw, source_line + b"\n")
                row = json.loads(raw)
                self.assertIn(data.hand_key(data.hand_ids(row["initial"])), key_sets[name])
                seen.append((member["source"], member["line"]))
        seen.extend((m["source"], m["line"]) for m in excluded["members"])
        self.assertEqual(len(seen), 34)
        self.assertEqual(len(set(seen)), 34)
        for source, meta in zip(self.sources, manifest["sources"]):
            self.assertEqual(meta["path"], str(source.resolve()))
            self.assertEqual(meta["rows"], 17)
            self.assertEqual(meta["sha256"], data.sha256(source))

    def test_byte_reproducibility_and_local_seeds(self):
        first = self.prepare("first")
        random.seed(456)
        for _ in range(10):
            random.random()
        second = self.prepare("second")
        self.assertEqual(first, second)
        for name in ("train.jsonl", "validation.jsonl", "test.json", "manifest.json"):
            self.assertEqual((self.tmp / "first" / name).read_bytes(),
                             (self.tmp / "second" / name).read_bytes())
        different = self.prepare("different", split_seed=777)
        self.assertNotEqual(first["partitions"]["validation"]["keys"],
                            different["partitions"]["validation"]["keys"])
        self.assertEqual(first["partitions"]["test"], different["partitions"]["test"])

    def test_uniform_test_is_independent_of_training_sources_and_replayable(self):
        manifest = self.prepare()
        test_path = self.tmp / "prepared/test.json"
        report = json.loads(test_path.read_text())
        self.assertEqual([data.hand_ids(row["initial"]) for row in report["samples"]], self.test_hands)
        self.assertEqual(manifest["partitions"]["test"]["sha256"], data.sha256(test_path))
        import benchmark_ml
        self.assertEqual(benchmark_ml.load_replay(test_path, self.variant, 5, set()), self.test_hands)
        self.write_source(self.sources[0], self.rows[:8])
        self.write_source(self.sources[1], self.rows[8:])
        changed = self.prepare("changed")
        self.assertEqual(manifest["partitions"]["test"], changed["partitions"]["test"])
        self.assertEqual(test_path.read_bytes(), (self.tmp / "changed/test.json").read_bytes())

    def test_repeated_test_classes_are_retained(self):
        # Actual with-replacement sampling includes repeated equivalence classes.
        result = self.prepare(test_hands=1000)
        part = result["partitions"]["test"]
        self.assertEqual(part["rows"], 1000)
        self.assertLess(part["groups"], part["rows"])
        cohort = json.loads((self.tmp / "prepared/test.json").read_text())
        self.assertEqual(len(cohort["samples"]), 1000)

    def test_invalid_rows_fail_even_when_test_equivalent(self):
        valid = self.row(self.test_hands[0])
        bad_rows = [None, [], "row", 1]
        updates = [
            {"engine": None}, {"engine": "rule"}, {"engine": "ml"},
            {"variant": None}, {"variant": data.VARIANTS[1]},
            {"bet": None}, {"bet": 1}, {"bet": True}, {"bet": 5.0}, {"bet": "5"},
            {"hold_mask": None}, {"hold_mask": True}, {"hold_mask": -1}, {"hold_mask": 32},
            {"hold_mask": 2.0}, {"hold_mask": "2"},
            {"initial": None}, {"initial": []}, {"initial": [valid["initial"][0]] * 5},
            {"initial": [None, *valid["initial"][1:]]},
            {"final": []}, {"payout": -1}, {"payout": True}, {"payout": 0.5},
        ]
        for field in ("s", "r"):
            for value in (0, 15, True, 2.0, "2", None):
                row = copy.deepcopy(valid)
                row["initial"][0][field] = value
                bad_rows.append(row)
        bad_rows.extend({**valid, **update} for update in updates)
        for field in valid:
            bad_rows.append({k: v for k, v in valid.items() if k != field})
        for row in bad_rows:
            with self.subTest(row=row):
                self.write_source(self.sources[0], [row])
                with self.assertRaisesRegex(ValueError, "one.jsonl:2: invalid training row"):
                    self.prepare()
                self.assertFalse((self.tmp / "prepared").exists())
        for raw in (b"\n{bad json}\n", b"\n\xff\n",
                    json.dumps({**valid, "extra": float("nan")}).encode()):
            self.sources[0].write_bytes(raw)
            with self.assertRaisesRegex(ValueError, "invalid training row"):
                self.prepare()

    def test_configuration_and_insufficient_groups(self):
        for config in ({"variant": "bad"}, {"bet": True}, {"bet": 0}, {"bet": 6},
                       {"validation_fraction": 0}, {"validation_fraction": 1},
                       {"validation_fraction": float("nan")}, {"validation_fraction": float("inf")},
                       {"test_hands": 0}, {"test_hands": -1}, {"test_hands": True},
                       {"test_seed": True}, {"split_seed": 1.0}):
            with self.subTest(config=config), self.assertRaises(ValueError):
                self.prepare(**config)
            self.assertFalse((self.tmp / "prepared").exists())
        for paths in ([], [self.sources[0], self.sources[0]]):
            with self.assertRaises(ValueError):
                prep.prepare(paths, self.tmp / "prepared", self.variant, 5)
        self.sources[0].write_text("\n")
        with self.assertRaisesRegex(ValueError, "no training rows"):
            self.prepare()
        for path in self.sources:
            self.write_source(path, [self.row(self.test_hands[0]), self.rows[0]])
        with self.assertRaisesRegex(ValueError, "at least two"):
            self.prepare()
        # Two groups must still produce nonempty splits for extreme fractions.
        for path in self.sources:
            self.write_source(path, self.rows[:2])
        for fraction in (0.00001, 0.99999):
            result = self.prepare(str(fraction), validation_fraction=fraction)
            self.assertEqual(result["partitions"]["train"]["groups"], 1)
            self.assertEqual(result["partitions"]["validation"]["groups"], 1)

    def test_both_paytables_and_bet_scope(self):
        self.variant = data.VARIANTS[1]
        for path in self.sources:
            self.write_source(path, [{**self.row(h), "bet": 1} for h in self.hands])
        result = self.prepare(bet=1)
        self.assertEqual(result["variant"], data.VARIANTS[1])
        self.assertEqual(result["bet"], 1)
        with self.assertRaisesRegex(ValueError, "integer bet=5"):
            self.prepare("wrong-bet")

    def test_cli_and_overwrite_protection(self):
        command = [sys.executable, "-B", str(PYTHON / "prepare_ml_data.py"),
                   *map(str, self.sources), "--variant", self.variant, "--bet", "5",
                   "--test-hands", "20", "--output-dir", str(self.tmp / "prepared")]
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        self.assertIn("manifest=", result.stdout)
        manifest_path = self.tmp / "prepared/manifest.json"
        before = manifest_path.read_bytes()
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("existing partitions will not be overwritten", result.stderr)
        self.assertEqual(manifest_path.read_bytes(), before)
        source_before = self.sources[0].read_bytes()
        result = subprocess.run([*command, "--output-dir", str(self.sources[0])],
                                capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.sources[0].read_bytes(), source_before)


if __name__ == "__main__":
    unittest.main()
