"""Tests for training from fixed solver-labelled partitions."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
PYTHON = ROOT / "poker-core/python"
sys.path.insert(0, str(PYTHON))
import ml_data
import prepare_ml_data
import train_ml_engine as trainer


class ManifestTrainingTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        source = self.directory / "source.jsonl"
        self.partition_dir = self.directory / "partitions"
        self.manifest = self.partition_dir / "manifest.json"
        variant = ml_data.VARIANTS[0]
        # In a dealt four of a kind, holding the four matching cards is optimal.
        with source.open("w", encoding="utf-8") as stream:
            for rank in range(13):
                ids = [rank + 13 * suit for suit in range(4)] + [(rank + 1) % 13]
                row = {"initial": ml_data.initial_cards(ids), "hold_mask": 15,
                       "engine": "solver", "variant": variant, "bet": 5}
                stream.write(json.dumps(row) + "\n")
        prepare_ml_data.prepare([source], self.partition_dir, variant, 5,
                                test_hands=20, validation_fraction=0.25)
        self.command = [sys.executable, "-B", str(PYTHON / "train_ml_engine.py"),
                        "--manifest", str(self.manifest), "--epochs", "2",
                        "--max-samples", "5", "--max-validation-samples", "2", "--seed", "24680"]

    def run_training(self, name, *args):
        return subprocess.run([*self.command, "--run-dir", str(self.directory / name), *args],
                              capture_output=True, text=True)

    def test_reproducible_artifacts_and_fixed_partition_metrics(self):
        validation = self.directory / "relocated-validation.jsonl"
        shutil.move(self.partition_dir / "validation.jsonl", validation)
        (self.partition_dir / "test.json").rename(self.directory / "reserved.json")
        for name in ("first", "repeat"):
            result = self.run_training(name, "--validation-data", str(validation))
            self.assertEqual(result.returncode, 0, result.stderr)
        first, repeat = self.directory / "first", self.directory / "repeat"
        files = [path.relative_to(first) for path in first.rglob("*.json")]
        self.assertEqual(len(files), 4)
        for path in files:
            self.assertEqual((first / path).read_bytes(), (repeat / path).read_bytes(), path)

        manifest = json.loads(self.manifest.read_bytes())
        record = json.loads((first / "run.json").read_bytes())
        self.assertEqual(record["status"], "complete")
        self.assertEqual(record["dataset"]["manifest"]["sha256"], ml_data.sha256(self.manifest))
        self.assertEqual(record["dataset"]["sources"], manifest["sources"])
        self.assertEqual(record["configuration"]["seed"], 24680)
        self.assertEqual(record["dataset"]["partitions"]["train"]["used_rows"], 5)
        self.assertEqual(record["dataset"]["partitions"]["validation"]["used_rows"], 2)

        candidate = record["candidate"]
        model = json.loads((first / candidate["path"]).read_bytes())
        self.assertEqual((model["input_size"], model["hidden1_size"],
                          model["hidden2_size"], model["output_size"]), (286, 128, 64, 5))
        self.assertEqual(ml_data.sha256(first / candidate["path"]), candidate["sha256"])
        self.assertEqual(candidate["sha256"], record["epochs"][-1]["checkpoint"]["sha256"])
        weights = [model[key] for key in ("W1", "b1", "W2", "b2", "W3", "b3")]
        datasets = (("train", self.partition_dir / "train.jsonl", 5), ("validation", validation, 2))
        for split, path, limit in datasets:
            X, y = trainer.load_dataset(path, max_samples=limit)
            expected = dict(zip(("loss", "exact_mask_accuracy", "bit_accuracy"),
                                trainer.evaluate(X, y, *weights)))
            self.assertEqual(record["epochs"][-1][split], expected)
        for epoch in record["epochs"]:
            checkpoint = epoch["checkpoint"]
            self.assertEqual(checkpoint["sha256"], ml_data.sha256(first / checkpoint["path"]))
        rerun = self.run_training("first", "--validation-data", str(validation))
        self.assertNotEqual(rerun.returncode, 0)
        self.assertIn("Run directory must be new", rerun.stderr)
        self.assertEqual((first / "run.json").read_bytes(), (repeat / "run.json").read_bytes())

    def test_reject_changed_validation_even_beyond_sample_limit(self):
        path = self.partition_dir / "validation.jsonl"
        with path.open("ab") as stream:
            stream.write(b"\n")
        result = self.run_training("changed")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SHA-256 does not match", result.stderr)
        self.assertFalse((self.directory / "changed").exists())

    def test_reject_overlap_with_reserved_keys_outside_training_prefix(self):
        manifest = json.loads(self.manifest.read_bytes())
        train = self.partition_dir / "train.jsonl"
        row = json.loads(train.read_bytes().splitlines()[-1])
        key = ml_data.hand_key(ml_data.hand_ids(row["initial"]))
        test = manifest["partitions"]["test"]
        test["keys"].append(list(key))
        test["groups"] += 1
        self.manifest.write_text(json.dumps(manifest), encoding="utf-8")
        result = self.run_training("overlap")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("hand-equivalence groups overlap", result.stderr)
        self.assertFalse((self.directory / "overlap").exists())


if __name__ == "__main__":
    unittest.main()
