"""Measure native ML hold quality using exact shared-solver expected payouts."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import random
import statistics
import subprocess
import sys
import time

VERSION = "1"
ROOT = Path(__file__).resolve().parents[2]
VARIANTS = ("jacks_or_better_9_6", "jacks_or_better_8_5")
# Sorted suit rank-bitsets canonically represent a hand under card reordering
# and suit renaming, including cases with several cards of the same rank.
OPTIMAL_TOLERANCE = 1e-9  # Normalized EV: expected returned coins / wagered coin.


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def hand_ids(initial):
    if not isinstance(initial, list) or len(initial) != 5:
        raise ValueError("Each initial hand must contain five cards")
    ids = []
    for card in initial:
        if not isinstance(card, dict):
            raise ValueError("Cards must be objects with integer s and r fields")
        s, r = card.get("s"), card.get("r")
        if type(s) is not int or type(r) is not int or not 1 <= s <= 4 or not 2 <= r <= 14:
            raise ValueError("Cards require integer suit 1..4 and rank 2..14")
        ids.append((s - 1) * 13 + r - 2)
    if len(set(ids)) != 5:
        raise ValueError("Duplicate cards in hand")
    return ids


def initial_cards(ids):
    return [{"s": card // 13 + 1, "r": card % 13 + 2} for card in ids]


def hand_key(ids):
    suits = [0] * 4
    for card in ids:
        suits[card // 13] |= 1 << (card % 13)
    return tuple(sorted(suits))


def load_exclusions(paths):
    keys, metadata = set(), []
    for path in paths:
        count = 0
        with Path(path).open(encoding="utf-8") as stream:
            for number, line in enumerate(stream, 1):
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                    keys.add(hand_key(hand_ids(row["initial"])))
                except (ValueError, KeyError, TypeError) as error:
                    raise ValueError(f"{path}:{number}: invalid training hand: {error}") from error
                count += 1
        metadata.append({"path": str(path), "sha256": sha256(path), "rows": count})
    return keys, metadata


def validate_model(path):
    with Path(path).open(encoding="utf-8") as stream:
        model = json.load(stream)
    if not isinstance(model, dict):
        raise ValueError("Model must be a JSON object")

    def dimension(name):
        value = model.get(name)
        if type(value) is not int or value <= 0:
            raise ValueError(f"Invalid model dimension: {name}")
        return value

    def vector(name, length):
        values = model.get(name)
        if not isinstance(values, list) or len(values) != length:
            raise ValueError(f"Invalid model vector: {name}")
        if any(type(v) not in (int, float) or not math.isfinite(v) or abs(v) > 3.402823466e38 for v in values):
            raise ValueError(f"Non-finite or non-float32 model value in {name}")

    def matrix(name, rows, columns):
        values = model.get(name)
        if not isinstance(values, list) or len(values) != rows:
            raise ValueError(f"Invalid model matrix: {name}")
        for row in values:
            if not isinstance(row, list) or len(row) != columns:
                raise ValueError(f"Invalid model matrix: {name}")
            if any(type(v) not in (int, float) or not math.isfinite(v) or abs(v) > 3.402823466e38 for v in row):
                raise ValueError(f"Non-finite or non-float32 model value in {name}")

    inputs, outputs = dimension("input_size"), dimension("output_size")
    if inputs not in (261, 286) or outputs not in (5, 32):
        raise ValueError("Benchmark supports 261/286 inputs and 5/32 outputs")
    if "hidden1_size" in model or "hidden2_size" in model:
        h1, h2 = dimension("hidden1_size"), dimension("hidden2_size")
        matrix("W1", h1, inputs)
        vector("b1", h1)
        matrix("W2", h2, h1)
        vector("b2", h2)
        matrix("W3", outputs, h2)
        vector("b3", outputs)
    else:
        hidden = dimension("hidden_size")
        matrix("W1", hidden, inputs)
        vector("b1", hidden)
        matrix("W2", outputs, hidden)
        vector("b2", outputs)


def sample_hands(count, seed, exclusions):
    rng = random.Random(seed)
    hands, rejected = [], 0
    # Sampling with replacement preserves the uniform dealt-hand distribution.
    # Conditioning only on exclusions avoids bias from deduplicating accepted hands.
    for _ in range(max(10000, count * 100)):
        ids = rng.sample(range(52), 5)
        if hand_key(ids) in exclusions:
            rejected += 1
            continue
        hands.append(ids)
        if len(hands) == count:
            return hands, rejected
    raise ValueError("Unable to sample enough hands; exclusions may cover most hand classes")


def load_replay(path, variant, bet, exclusions):
    with Path(path).open(encoding="utf-8") as stream:
        report = json.load(stream)
    if not isinstance(report, dict) or not isinstance(report.get("samples"), list):
        raise ValueError("Replay must be a report object with a samples array")
    if report.get("variant") != variant or report.get("bet") != bet:
        raise ValueError("Replay variant and bet must match the requested benchmark")
    if any(not isinstance(row, dict) for row in report["samples"]):
        raise ValueError("Replay samples must be objects with initial hands")
    hands = [hand_ids(row["initial"]) for row in report["samples"]]
    if not hands:
        raise ValueError("Replay contains no hands")
    if any(hand_key(ids) in exclusions for ids in hands):
        raise ValueError("Replay contains an excluded training-equivalent hand")
    return hands


def score_hands(native, model, variant, bet, hands):
    command = [str(native), "--ml-model", str(model), "--variant", variant, "--bet", str(bet)]
    payload = "".join(" ".join(map(str, ids)) + "\n" for ids in hands)
    completed = subprocess.run(command, input=payload, text=True, capture_output=True, check=False)
    if completed.returncode:
        raise ValueError(f"Native scoring failed: {completed.stderr.strip()}")
    lines = completed.stdout.splitlines()
    if len(lines) != len(hands):
        raise ValueError("Native scorer returned an unexpected number of rows")
    samples = []
    for index, (ids, line) in enumerate(zip(hands, lines)):
        fields = line.split("\t")
        if len(fields) != 5:
            raise ValueError("Invalid native scoring row")
        mask, best = int(fields[0]), int(fields[1])
        best_ev, model_ev = float(fields[2]), float(fields[3])
        if not 0 <= mask <= 31 or not 0 <= best <= 31 or not all(map(math.isfinite, (best_ev, model_ev))):
            raise ValueError("Invalid native masks or EVs")
        regret = (best_ev - model_ev) / bet
        if regret < -OPTIMAL_TOLERANCE:
            raise ValueError("Model EV exceeds solver best EV")
        samples.append({
            "index": index, "initial": initial_cards(ids), "model_mask": mask,
            "solver_mask": best, "solver_ev": best_ev, "model_ev": model_ev,
            "normalized_regret": max(0.0, regret), "initial_category": fields[4],
        })
    return samples


def summarize(samples, bet):
    regrets = [row["normalized_regret"] for row in samples]
    count, mean = len(regrets), statistics.fmean(regrets)
    se = statistics.stdev(regrets) / math.sqrt(count) if count > 1 else None
    groups = {}
    for row in samples:
        groups.setdefault(row["initial_category"], []).append(row["normalized_regret"])
    categories = []
    for category, values in sorted(groups.items()):
        contribution = math.fsum(values) / count
        categories.append({
            "initial_category": category, "count": len(values), "frequency": len(values) / count,
            "mean_normalized_regret": statistics.fmean(values),
            "contribution_to_mean_regret": contribution,
            "contribution_to_gap_percentage_points": 100 * contribution,
        })
    return {
        "hands": count, "mean_normalized_regret": mean,
        "rtp_gap_percentage_points": 100 * mean,
        "regret_standard_error": se,
        "regret_approx_95_ci": [mean - 1.96 * se, mean + 1.96 * se] if se is not None else None,
        "exact_mask_agreement": sum(r["model_mask"] == r["solver_mask"] for r in samples) / count,
        "ev_optimal_agreement": sum(v <= OPTIMAL_TOLERANCE for v in regrets) / count,
        "mean_solver_expected_return_per_coin": statistics.fmean(r["solver_ev"] / bet for r in samples),
        "mean_model_expected_return_per_coin": statistics.fmean(r["model_ev"] / bet for r in samples),
        "categories": categories,
        "worst_mistakes": sorted((r for r in samples if r["normalized_regret"] > OPTIMAL_TOLERANCE),
                                 key=lambda r: (-r["normalized_regret"], r["index"]))[:20],
    }


def positive_int(value):
    result = int(value)
    if result <= 0:
        raise argparse.ArgumentTypeError("must be positive")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ml-model", type=Path, required=True)
    parser.add_argument("--variant", choices=VARIANTS, required=True)
    parser.add_argument("--bet", type=int, choices=range(1, 6), default=5)
    parser.add_argument("--seed", type=int, default=12345)
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--hands", type=positive_int)
    selection.add_argument("--input", type=Path, help="Replay ordered hands from a previous report")
    parser.add_argument("--exclude-training", type=Path, action="append", default=[])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--native", type=Path, default=ROOT / "build/benchmark_ml")
    args = parser.parse_args(argv)
    try:
        protected = [args.ml_model, args.native, Path(__file__), *args.exclude_training]
        if args.input:
            protected.append(args.input)
        if args.output.resolve() in [path.resolve() for path in protected]:
            raise ValueError("Output must not overwrite an input, model or executable")
        validate_model(args.ml_model)
        exclusions, exclusion_metadata = load_exclusions(args.exclude_training)
        if args.input:
            hands = load_replay(args.input, args.variant, args.bet, exclusions)
            rejected = None
            sampling = {"mode": "replay", "path": str(args.input), "sha256": sha256(args.input),
                        "seed": None, "rejected": rejected}
        else:
            hands, rejected = sample_hands(args.hands or 1000, args.seed, exclusions)
            sampling = {"mode": "uniform_with_replacement", "seed": args.seed, "rejected": rejected}
        started = time.perf_counter()
        print(f"Scoring {len(hands)} hands with exact solver EVs...", file=sys.stderr)
        samples = score_hands(args.native.resolve(), args.ml_model.resolve(), args.variant, args.bet, hands)
        elapsed = time.perf_counter() - started
        report = {
            "benchmark_version": VERSION, "driver_sha256": sha256(__file__),
            "native_sha256": sha256(args.native),
            "model": {"path": str(args.ml_model), "sha256": sha256(args.ml_model)},
            "variant": args.variant, "bet": args.bet,
            "optimal_tolerance_normalized_ev": OPTIMAL_TOLERANCE,
            "sampling": sampling, "excluded_training": exclusion_metadata,
            "excluded_hand_classes": len(exclusions),
            "evaluation_scope": "replayed_hands" if args.input else (
                "uniform_hands_conditioned_on_exclusions" if exclusions else "uniform_dealt_hands"),
            "provenance_note": "Training provenance is not verified; exclusions cover only supplied files. "
                               "Replay retains the supplied hands and does not establish random sampling.",
            "uncertainty_note": "Approximate normal interval over sampled hand regrets; unreliable for small "
                                "samples or rare losses. Zero observed loss does not prove zero population loss. "
                                "For replay, interpret uncertainty only if its sampling design warrants it.",
            "native_scoring_seconds": elapsed,
            "summary": summarize(samples, args.bet), "samples": samples,
        }
        encoded = json.dumps(report, indent=2, allow_nan=False) + "\n"
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
        summary = report["summary"]
        print(f"{args.variant}: gap={summary['rtp_gap_percentage_points']:.6f} percentage points; "
              f"EV-optimal={summary['ev_optimal_agreement']:.2%}; scoring={elapsed:.2f}s; "
              f"report={args.output}", file=sys.stderr)
    except (OSError, ValueError, KeyError, TypeError, OverflowError) as error:
        parser.exit(1, f"benchmark_ml: {error}\n")


if __name__ == "__main__":
    main()
