"""Compare model EV regret from two benchmark reports on identical ordered hands."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import statistics

from benchmark_ml import OPTIMAL_TOLERANCE
from ml_data import VARIANTS, hand_ids


def sample_regret(row, bet):
    solver_ev, model_ev = row["solver_ev"], row["model_ev"]
    if any(type(ev) not in (int, float) or not math.isfinite(ev) or ev < 0
           for ev in (solver_ev, model_ev)):
        raise ValueError("Sample EVs must be finite and nonnegative")
    for name in ("solver_mask", "model_mask"):
        mask = row[name]
        if type(mask) is not int or not 0 <= mask <= 31:
            raise ValueError(f"Invalid sample {name}")
    regret = (solver_ev - model_ev) / bet
    if regret < -OPTIMAL_TOLERANCE:
        raise ValueError("Model EV exceeds solver best EV")
    return max(0.0, regret)


def compare(baseline, candidate):
    variant, bet = baseline["variant"], baseline["bet"]
    if variant not in VARIANTS or candidate["variant"] != variant:
        raise ValueError("Reports must have the same supported variant")
    if any(type(report["bet"]) is not int or report["bet"] != bet for report in (baseline, candidate)) or not 1 <= bet <= 5:
        raise ValueError("Reports must have the same integer bet in 1..5")
    before, after = baseline["samples"], candidate["samples"]
    if (not isinstance(before, list) or not isinstance(after, list) or
            not before or len(before) != len(after)):
        raise ValueError("Reports must have the same nonzero sample count")

    pairs = []
    groups = {}
    for index, (a, b) in enumerate(zip(before, after)):
        if hand_ids(a["initial"]) != hand_ids(b["initial"]):
            raise ValueError(f"Sample {index}: ordered hands do not match")
        category = a["initial_category"]
        if not isinstance(category, str) or not category or category != b["initial_category"]:
            raise ValueError(f"Sample {index}: initial categories do not match")
        regrets = [sample_regret(row, bet) for row in (a, b)]
        if a["solver_ev"] != b["solver_ev"]:
            raise ValueError(f"Sample {index}: solver EVs do not match")
        improvement = regrets[0] - regrets[1]
        groups.setdefault(category, []).append(improvement)
        pairs.append({
            "index": index, "initial": a["initial"], "initial_category": category,
            "solver_ev": a["solver_ev"], "solver_mask": a["solver_mask"],
            "baseline_mask": a["model_mask"], "candidate_mask": b["model_mask"],
            "baseline_ev": a["model_ev"], "candidate_ev": b["model_ev"],
            "baseline_regret": regrets[0], "candidate_regret": regrets[1],
            "improvement": improvement,
        })

    count = len(pairs)
    differences = [row["improvement"] for row in pairs]
    mean = statistics.fmean(differences)
    se = statistics.stdev(differences) / math.sqrt(count) if count > 1 else None
    categories = []
    for category, values in sorted(groups.items()):
        contribution = math.fsum(values) / count
        categories.append({
            "initial_category": category, "count": len(values),
            "mean_improvement": statistics.fmean(values),
            "contribution_to_mean_improvement": contribution,
            "contribution_percentage_points": 100 * contribution,
        })
    return {
        "variant": variant, "bet": bet, "hands": count,
        "baseline_mean_regret": statistics.fmean(row["baseline_regret"] for row in pairs),
        "candidate_mean_regret": statistics.fmean(row["candidate_regret"] for row in pairs),
        "mean_improvement": mean, "improvement_percentage_points": 100 * mean,
        "paired_standard_error": se,
        "paired_approx_95_ci": [mean - 1.96 * se, mean + 1.96 * se] if se is not None else None,
        "interval_note": "Approximate paired normal interval. Interpret for the sampled cohort and its "
                         "sampling design. Checkpoint selection on this cohort can bias the comparison.",
        "categories": categories,
        "worst_regressions": sorted((row for row in pairs if row["improvement"] < -OPTIMAL_TOLERANCE),
                                    key=lambda row: (row["improvement"], row["index"]))[:20],
    }


def load_report(path):
    content = path.read_bytes()
    report = json.loads(content)
    return report, {"path": str(path), "sha256": hashlib.sha256(content).hexdigest(),
                    "model": report["model"]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        baseline, baseline_record = load_report(args.baseline)
        candidate, candidate_record = load_report(args.candidate)
        result = {"comparison_version": 1, "baseline": baseline_record, "candidate": candidate_record,
                  **compare(baseline, candidate)}
        encoded = json.dumps(result, indent=2, allow_nan=False) + "\n"
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as stream:
            stream.write(encoded)
    except (OSError, ValueError, KeyError, TypeError, OverflowError) as error:
        parser.exit(1, f"compare_ml_benchmarks: {error}\n")
    print(f"Paired EV improvement: {result['improvement_percentage_points']:+.4f} percentage points "
          f"over {result['hands']} hands. Report: {args.output}")


if __name__ == "__main__":
    main()
