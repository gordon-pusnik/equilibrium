"""Reserve a uniform test cohort and partition solver-labelled JSONL by hand class."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import platform
import random

import ml_data
from ml_data import VARIANTS, hand_key, initial_cards, sample_hands, sha256, validate_training_row

VERSION = 1


def reject_constant(value):
    raise ValueError(f"Non-finite JSON number: {value}")


def load_sources(paths, variant, bet):
    """Keep source bytes and physical line membership; hash exactly what was read."""
    rows, sources = [], []
    for source_index, path in enumerate(paths):
        digest = hashlib.sha256()
        count = 0
        with path.open("rb") as stream:
            for number, raw in enumerate(stream, 1):
                digest.update(raw)
                if not raw.strip():
                    continue
                try:
                    row = json.loads(raw.decode("utf-8"), parse_constant=reject_constant)
                    key = hand_key(validate_training_row(row, variant, bet))
                except (ValueError, TypeError) as error:
                    raise ValueError(f"{path}:{number}: invalid training row: {error}") from error
                rows.append((key, source_index, number, raw))
                count += 1
        if not count:
            raise ValueError(f"{path}: no training rows")
        sources.append({"path": str(path), "sha256": digest.hexdigest(), "rows": count})
    return rows, sources


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def row_partition(directory, name, rows):
    path = directory / f"{name}.jsonl"
    with path.open("wb") as stream:
        for _, _, _, raw in rows:
            stream.write(raw if raw.endswith(b"\n") else raw + b"\n")
    return {"path": path.name, "sha256": sha256(path), **row_membership(rows)}


def row_membership(rows):
    keys = sorted({row[0] for row in rows})
    return {"rows": len(rows), "groups": len(keys), "keys": keys,
            "members": [{"source": source, "line": line} for _, source, line, _ in rows]}


def prepare(paths, output_dir, variant, bet, test_hands=10000, test_seed=12345,
            split_seed=23456, validation_fraction=0.1):
    if variant not in VARIANTS or type(bet) is not int or not 1 <= bet <= 5:
        raise ValueError("Require a supported variant and integer bet in 1..5")
    if (type(validation_fraction) not in (int, float) or
            not math.isfinite(validation_fraction) or not 0 < validation_fraction < 1):
        raise ValueError("validation_fraction must be finite and between 0 and 1")
    if type(test_seed) is not int or type(split_seed) is not int:
        raise ValueError("Seeds must be integers")
    paths = [Path(path).resolve() for path in paths]
    if not paths or len(set(paths)) != len(paths):
        raise ValueError("Provide at least one source, with no repeated source paths")
    output_dir = Path(output_dir)
    if output_dir.exists():
        raise ValueError("Output directory must be new; existing partitions will not be overwritten")

    # Reserve independently of source contents. Filtering the test deals against
    # training data would change the test population to a conditional distribution.
    hands, _ = sample_hands(test_hands, test_seed, set())
    test_keys = {hand_key(ids) for ids in hands}
    rows, sources = load_sources(paths, variant, bet)
    remaining_keys = sorted({row[0] for row in rows} - test_keys)
    if len(remaining_keys) < 2:
        raise ValueError("Need at least two non-test hand-equivalence groups for training and validation")
    random.Random(split_seed).shuffle(remaining_keys)
    validation_groups = max(1, min(len(remaining_keys) - 1,
                                   int(len(remaining_keys) * validation_fraction)))
    validation_keys = set(remaining_keys[:validation_groups])
    training, validation, excluded = [], [], []
    for row in rows:
        if row[0] in test_keys:
            excluded.append(row)
        elif row[0] in validation_keys:
            validation.append(row)
        else:
            training.append(row)

    # Validate everything before creating artifacts. Exclusive directory creation
    # also prevents a rerun from silently replacing an experiment's fixed cohorts.
    output_dir.mkdir(parents=True, exist_ok=False)
    partitions = {"train": row_partition(output_dir, "train", training),
                  "validation": row_partition(output_dir, "validation", validation)}
    test_path = output_dir / "test.json"
    write_json(test_path, {"variant": variant, "bet": bet,
                          "samples": [{"index": i, "initial": initial_cards(ids)}
                                      for i, ids in enumerate(hands)]})
    partitions["test"] = {"path": test_path.name, "sha256": sha256(test_path),
                          "rows": len(hands), "groups": len(test_keys), "keys": sorted(test_keys)}
    manifest = {
        "manifest_version": VERSION, "variant": variant, "bet": bet,
        "preparation": {
            "driver_sha256": sha256(__file__), "helpers_sha256": sha256(ml_data.__file__),
            "python_version": platform.python_version(),
            "test_seed": test_seed, "split_seed": split_seed,
            "test_hands": test_hands, "validation_fraction": validation_fraction,
            "test_sampling": "uniform_ordered_deals_with_replacement_no_exclusions",
            "group_split": "sorted_keys_seeded_shuffle_validation_prefix_floor_clamped_nonempty",
            "equivalence": "sorted_four_suit_rank_bitsets_v1",
        },
        "sources": sources, "partitions": partitions,
        "excluded_test_equivalent": row_membership(excluded),
    }
    write_json(output_dir / "manifest.json", manifest)
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sources", type=Path, nargs="+", help="Solver-labelled JSONL sources")
    parser.add_argument("--variant", choices=VARIANTS, required=True)
    parser.add_argument("--bet", type=int, choices=range(1, 6), required=True)
    parser.add_argument("--test-hands", type=int, default=10000)
    parser.add_argument("--test-seed", type=int, default=12345)
    parser.add_argument("--split-seed", type=int, default=23456)
    parser.add_argument("--validation-fraction", type=float, default=0.1)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        manifest = prepare(args.sources, args.output_dir, args.variant, args.bet,
                           args.test_hands, args.test_seed, args.split_seed, args.validation_fraction)
    except (OSError, ValueError, TypeError, OverflowError) as error:
        parser.exit(1, f"prepare_ml_data: {error}\n")
    counts = ", ".join(f"{name}={part['rows']} rows/{part['groups']} groups"
                       for name, part in manifest["partitions"].items())
    print(f"{counts}; excluded={manifest['excluded_test_equivalent']['rows']} source rows; "
          f"manifest={args.output_dir / 'manifest.json'}")


if __name__ == "__main__":
    main()
