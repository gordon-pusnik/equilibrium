import argparse
import hashlib
import json
import math
from pathlib import Path
import platform
import random
import shutil

import ml_data
from ml_data import VARIANTS, hand_key, sha256, validate_training_row


def encode_hand(initial, bet):
    x = [0.0] * 286
    rank_counts = [0] * 13
    suit_counts = [0] * 4
    ranks = []
    for pos, card in enumerate(initial):
        s = int(card["s"])
        r = int(card["r"])
        card_id = (s - 1) * 13 + (r - 2)
        x[pos * 52 + card_id] = 1.0
        rank_counts[r - 2] += 1
        suit_counts[s - 1] += 1
        ranks.append(r)
    x[260] = float(bet) / 5.0

    offset = 261
    for i, count in enumerate(rank_counts):
        x[offset + i] = float(count) / 4.0

    offset = 274
    for i, count in enumerate(suit_counts):
        x[offset + i] = float(count) / 5.0

    offset = 278
    for i, rank in enumerate(sorted(ranks)):
        x[offset + i] = float(rank) / 14.0

    x[283] = float(sum(1 for count in rank_counts if count > 0)) / 5.0
    x[284] = float(max(suit_counts)) / 5.0
    x[285] = float(sum(1 for rank in ranks if rank >= 11)) / 5.0
    return x


def encode_target(mask):
    return [1.0 if (mask & (1 << pos)) != 0 else 0.0 for pos in range(5)]


def load_dataset(path, max_samples=None):
    X = []
    y = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            row = json.loads(line)
            X.append(encode_hand(row["initial"], row.get("bet", 5)))
            y.append(encode_target(int(row["hold_mask"])))
            if max_samples is not None and len(X) >= max_samples:
                break

    if not X:
        raise ValueError("No training samples found in input file.")

    return X, y


def load_fixed_partition(path, partition, variant, bet, limit):
    X, y, keys = [], [], set()
    digest = hashlib.sha256()
    count = 0
    with path.open("rb") as stream:
        for number, raw in enumerate(stream, 1):
            digest.update(raw)
            if not raw.strip():
                continue
            try:
                row = json.loads(raw.decode("utf-8"))
                keys.add(hand_key(validate_training_row(row, variant, bet)))
            except ValueError as error:
                raise ValueError(f"{path}:{number}: invalid partition row: {error}") from error
            count += 1
            if limit is None or count <= limit:
                X.append(encode_hand(row["initial"], bet))
                y.append(encode_target(row["hold_mask"]))
    if digest.hexdigest() != partition["sha256"]:
        raise ValueError(f"{path}: SHA-256 does not match the manifest")
    if (not count or count != partition["rows"] or len(keys) != partition["groups"] or
            [list(key) for key in sorted(keys)] != partition["keys"]):
        raise ValueError(f"{path}: row counts or hand groups do not match the manifest")
    return (X, y), keys


def load_fixed_data(manifest_path, validation_path, train_limit, validation_limit):
    raw_manifest = manifest_path.read_bytes()
    manifest = json.loads(raw_manifest)
    if (not isinstance(manifest, dict) or type(manifest.get("manifest_version")) is not int or
            manifest["manifest_version"] != 1):
        raise ValueError("Expected a version 1 preparation manifest")
    variant, bet = manifest["variant"], manifest["bet"]
    if variant not in VARIANTS or type(bet) is not int or not 1 <= bet <= 5:
        raise ValueError("Invalid manifest variant or bet")
    partitions = manifest["partitions"]
    train_path = manifest_path.parent / partitions["train"]["path"]
    if validation_path is None:
        validation_path = manifest_path.parent / partitions["validation"]["path"]
    datasets, data_records = {}, {}
    # The manifest supplies test keys for the leakage check. Training only reads
    # the two labelled files, so it can run with the test cohort stored separately.
    test = partitions["test"]
    seen = {tuple(key) for key in test["keys"]}
    if not seen or len(seen) != test["groups"]:
        raise ValueError("Invalid test group counts in the manifest")
    for name, path, limit in (("train", train_path, train_limit),
                              ("validation", validation_path, validation_limit)):
        partition = partitions[name]
        dataset, keys = load_fixed_partition(path, partition, variant, bet, limit)
        if seen & keys:
            raise ValueError(f"{name}: hand-equivalence groups overlap another partition")
        seen.update(keys)
        datasets[name] = dataset
        data_records[name] = {"path": str(path.resolve()), "sha256": partition["sha256"],
                              "partition_rows": partition["rows"], "used_rows": len(dataset[0])}
    provenance = {
        "manifest": {"path": str(manifest_path.resolve()),
                     "sha256": hashlib.sha256(raw_manifest).hexdigest()},
        "variant": variant, "bet": bet, "sources": manifest["sources"], "partitions": data_records,
    }
    return datasets["train"], datasets["validation"], provenance


def relu(v):
    return v if v > 0.0 else 0.0


def softmax(logits):
    m = max(logits)
    exps = [math.exp(v - m) for v in logits]
    s = sum(exps)
    return [v / s for v in exps]


def sigmoid(v):
    if v >= 0.0:
        z = math.exp(-v)
        return 1.0 / (1.0 + z)
    z = math.exp(v)
    return z / (1.0 + z)


def forward(x, W1, b1, W2, b2, W3=None, b3=None):
    hidden1 = len(b1)

    h1_pre = [0.0] * hidden1
    h1 = [0.0] * hidden1
    for j in range(hidden1):
        v = b1[j]
        row = W1[j]
        for i in range(len(x)):
            v += x[i] * row[i]
        h1_pre[j] = v
        h1[j] = relu(v)

    if W3 is None or b3 is None:
        out = len(b2)
        logits = [0.0] * out
        for k in range(out):
            v = b2[k]
            row = W2[k]
            for j in range(hidden1):
                v += h1[j] * row[j]
            logits[k] = v
        return h1_pre, h1, None, None, logits

    hidden2 = len(b2)
    h2_pre = [0.0] * hidden2
    h2 = [0.0] * hidden2
    for j in range(hidden2):
        v = b2[j]
        row = W2[j]
        for i in range(hidden1):
            v += h1[i] * row[i]
        h2_pre[j] = v
        h2[j] = relu(v)

    out = len(b3)
    logits = [0.0] * out
    for k in range(out):
        v = b3[k]
        row = W3[k]
        for j in range(hidden2):
            v += h2[j] * row[j]
        logits[k] = v

    return h1_pre, h1, h2_pre, h2, logits


def predict_mask(x, W1, b1, W2, b2, W3=None, b3=None):
    _, _, _, _, logits = forward(x, W1, b1, W2, b2, W3, b3)
    mask = 0
    for i, logit in enumerate(logits):
        if logit > 0.0:
            mask |= (1 << i)
    return mask


def evaluate(X, y, W1, b1, W2, b2, W3=None, b3=None):
    total_loss = 0.0
    exact = 0
    bit_correct = 0
    total_bits = 0

    for x, target in zip(X, y):
        _, _, _, _, logits = forward(x, W1, b1, W2, b2, W3, b3)
        sample_exact = True
        for i, logit in enumerate(logits):
            prob = sigmoid(logit)
            t = target[i]
            total_loss += -(t * math.log(max(prob, 1e-12)) + (1.0 - t) * math.log(max(1.0 - prob, 1e-12)))
            pred = 1.0 if logit > 0.0 else 0.0
            if pred == t:
                bit_correct += 1
            else:
                sample_exact = False
            total_bits += 1
        if sample_exact:
            exact += 1

    return total_loss / len(X), exact / len(X), bit_correct / total_bits


def permute_sample(x, target, rng):
    perm = list(range(5))
    rng.shuffle(perm)

    x_perm = [0.0] * len(x)
    for new_pos, old_pos in enumerate(perm):
        src_base = old_pos * 52
        dst_base = new_pos * 52
        x_perm[dst_base:dst_base + 52] = x[src_base:src_base + 52]

    if len(x) > 260:
        x_perm[260] = x[260]
    if len(x) > 261:
        x_perm[261:] = x[261:]

    target_perm = [0.0] * 5
    for new_pos, old_pos in enumerate(perm):
        target_perm[new_pos] = target[old_pos]

    return x_perm, target_perm


def train(
    X,
    y,
    hidden=64,
    hidden2=32,
    epochs=20,
    lr=0.01,
    seed=12345,
    validation_split=0.1,
    l2=1e-6,
    *,
    validation_data=None,
    on_epoch=None,
):
    rng = random.Random(seed)

    d = len(X[0])
    k = 5

    W1 = [[(rng.random() * 2.0 - 1.0) * math.sqrt(2.0 / d) for _ in range(d)] for _ in range(hidden)]
    b1 = [0.0 for _ in range(hidden)]
    W2 = [[(rng.random() * 2.0 - 1.0) * math.sqrt(2.0 / hidden) for _ in range(hidden)] for _ in range(hidden2)]
    b2 = [0.0 for _ in range(hidden2)]
    W3 = [[(rng.random() * 2.0 - 1.0) * math.sqrt(2.0 / hidden2) for _ in range(hidden2)] for _ in range(k)]
    b3 = [0.0 for _ in range(k)]

    if validation_data is None:
        indices = list(range(len(X)))
        rng.shuffle(indices)

        val_size = int(len(indices) * validation_split)
        if validation_split > 0.0 and val_size == 0 and len(indices) > 1:
            val_size = 1
        if val_size >= len(indices):
            val_size = max(0, len(indices) - 1)

        val_indices = indices[:val_size]
        train_indices = indices[val_size:]

        X_train = [X[i] for i in train_indices]
        y_train = [y[i] for i in train_indices]
        X_val = [X[i] for i in val_indices]
        y_val = [y[i] for i in val_indices]
    else:
        X_train, y_train = X, y
        X_val, y_val = validation_data

    n = len(X_train)
    if n == 0:
        raise ValueError("Not enough training samples after validation split.")

    for epoch in range(1, epochs + 1):
        order = list(range(n))
        rng.shuffle(order)
        epoch_lr = lr * (0.98 ** (epoch - 1))
        for idx in order:
            x, target = permute_sample(X_train[idx], y_train[idx], rng)

            h1_pre, h1, h2_pre, h2, logits = forward(x, W1, b1, W2, b2, W3, b3)
            dlogits = [sigmoid(logits[i]) - target[i] for i in range(k)]

            dh2 = [0.0] * hidden2
            for out_i in range(k):
                g = dlogits[out_i]
                for j in range(hidden2):
                    dh2[j] += g * W3[out_i][j]
                    W3[out_i][j] -= epoch_lr * (g * h2[j] + l2 * W3[out_i][j])
                b3[out_i] -= epoch_lr * g

            dh1 = [0.0] * hidden
            for j in range(hidden2):
                dz2 = dh2[j] if h2_pre[j] > 0.0 else 0.0
                row = W2[j]
                for i in range(hidden):
                    dh1[i] += dz2 * row[i]
                    row[i] -= epoch_lr * (dz2 * h1[i] + l2 * row[i])
                b2[j] -= epoch_lr * dz2

            for j in range(hidden):
                dz1 = dh1[j] if h1_pre[j] > 0.0 else 0.0
                row = W1[j]
                for i in range(d):
                    row[i] -= epoch_lr * (dz1 * x[i] + l2 * row[i])
                b1[j] -= epoch_lr * dz1

        train_loss, train_exact, train_bit = evaluate(X_train, y_train, W1, b1, W2, b2, W3, b3)
        if X_val:
            val_loss, val_exact, val_bit = evaluate(X_val, y_val, W1, b1, W2, b2, W3, b3)
            print(
                f"epoch {epoch:02d} lr={epoch_lr:.5f} "
                f"train_loss={train_loss:.4f} train_exact={train_exact:.4f} train_bit={train_bit:.4f} "
                f"val_loss={val_loss:.4f} val_exact={val_exact:.4f} val_bit={val_bit:.4f}"
            )
        else:
            print(
                f"epoch {epoch:02d} lr={epoch_lr:.5f} "
                f"train_loss={train_loss:.4f} train_exact={train_exact:.4f} train_bit={train_bit:.4f}"
            )
        if on_epoch is not None:
            metrics = {
                "epoch": epoch, "learning_rate": epoch_lr,
                "train": {"loss": train_loss, "exact_mask_accuracy": train_exact,
                          "bit_accuracy": train_bit},
                "validation": ({"loss": val_loss, "exact_mask_accuracy": val_exact,
                                "bit_accuracy": val_bit} if X_val else None),
            }
            on_epoch(metrics, (W1, b1, W2, b2, W3, b3))

    return W1, b1, W2, b2, W3, b3


def export_model(weights):
    W1, b1, W2, b2, W3, b3 = weights
    return {
        "format": "videopoker-ml-v3",
        "input_size": len(W1[0]),
        "hidden1_size": len(b1),
        "hidden2_size": len(b2),
        "output_size": len(b3),
        "W1": W1,
        "b1": b1,
        "W2": W2,
        "b2": b2,
        "W3": W3,
        "b3": b3,
    }


def write_json(path, value, *, indent=None):
    temporary = path.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, indent=indent, allow_nan=False)
    temporary.replace(path)


def run_fixed_training(args, config):
    directory = args.run_dir
    if directory.exists():
        raise ValueError("Run directory must be new to preserve existing artifacts")
    (X, y), validation, provenance = load_fixed_data(
        args.manifest, args.validation_data, args.max_samples, args.max_validation_samples)
    directory.mkdir(parents=True, exist_ok=False)
    checkpoint_dir = directory / "checkpoints"
    checkpoint_dir.mkdir()
    record_path = directory / "run.json"
    record = {
        "run_version": 1, "status": "in_progress", "dataset": provenance,
        "runtime": {"python": platform.python_version(),
                    "implementation": platform.python_implementation(),
                    "system": platform.system(), "machine": platform.machine()},
        "code_sha256": {"train_ml_engine.py": sha256(__file__),
                        "ml_data.py": sha256(ml_data.__file__)},
        "configuration": {
            **config, "input_size": len(X[0]), "output_size": len(y[0]),
            "loss": "binary_cross_entropy", "optimizer": "per_sample_sgd_with_l2",
            "learning_rate_decay": 0.98, "augmentation": "position_shuffle_preserving_summary",
            "max_samples": args.max_samples, "max_validation_samples": args.max_validation_samples,
        },
        "epochs": [],
    }
    write_json(record_path, record, indent=2)

    def save_epoch(metrics, weights):
        checkpoint = checkpoint_dir / f"epoch-{metrics['epoch']:03d}.json"
        write_json(checkpoint, export_model(weights))
        record["epochs"].append({**metrics, "checkpoint": {
            "path": checkpoint.relative_to(directory).as_posix(), "sha256": sha256(checkpoint),
        }})
        write_json(record_path, record, indent=2)

    print(f"loaded train={len(X)} validation={len(validation[0])} features={len(X[0])}")
    train(X, y, **config, validation_data=validation, on_epoch=save_epoch)
    candidate = directory / f"candidate-{provenance['variant']}.json"
    last = record["epochs"][-1]["checkpoint"]
    temporary = candidate.with_suffix(".tmp")
    shutil.copyfile(directory / last["path"], temporary)
    temporary.replace(candidate)
    record["candidate"] = {"path": candidate.name, "sha256": sha256(candidate),
                           "epoch": config["epochs"]}
    record["status"] = "complete"
    write_json(record_path, record, indent=2)
    print(f"saved final-epoch candidate to {candidate}")
    print(f"saved run record to {record_path}")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Train an ML hold model from videopoker JSONL data.")
    parser.add_argument("input_jsonl", nargs="?")
    parser.add_argument("output_model_json", nargs="?")
    parser.add_argument("--manifest", type=Path, help="Preparation manifest for fixed partitions")
    parser.add_argument("--validation-data", type=Path,
                        help="Path to the manifest's validation JSONL if stored separately")
    parser.add_argument("--run-dir", type=Path, help="New directory for checkpoints and candidate")
    parser.add_argument("--hidden", type=int, help="First layer width (manifest: 128, legacy: 64)")
    parser.add_argument("--hidden2", type=int, help="Second layer width (manifest: 64, legacy: 32)")
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--lr", type=float, default=0.01)
    parser.add_argument("--validation-split", type=float, help="Legacy split fraction (default: 0.1)")
    parser.add_argument("--l2", type=float, default=1e-6)
    parser.add_argument("--seed", type=int, default=12345)
    parser.add_argument("--max-samples", type=int, help="Use at most this many input rows")
    parser.add_argument("--max-validation-samples", type=int,
                        help="Use a fixed validation prefix for a small manifest run")
    args = parser.parse_args(argv)
    if args.manifest:
        if not args.run_dir or args.input_jsonl or args.output_model_json:
            parser.error("--manifest requires --run-dir and replaces the positional input and output")
        if args.validation_split is not None:
            parser.error("--validation-split cannot be used with fixed manifest partitions")
        hidden_defaults = (128, 64)
    else:
        if not args.input_jsonl or not args.output_model_json:
            parser.error("provide both input_jsonl and output_model_json, or use --manifest")
        if any(value is not None for value in
               (args.run_dir, args.validation_data, args.max_validation_samples)):
            parser.error("--run-dir, --validation-data and --max-validation-samples require --manifest")
        hidden_defaults = (64, 32)
    config = {
        "hidden": args.hidden if args.hidden is not None else hidden_defaults[0],
        "hidden2": args.hidden2 if args.hidden2 is not None else hidden_defaults[1],
        "epochs": args.epochs, "lr": args.lr, "seed": args.seed, "l2": args.l2,
    }
    for name, value in (("hidden", config["hidden"]), ("hidden2", config["hidden2"]),
                        ("epochs", args.epochs), ("max-samples", args.max_samples),
                        ("max-validation-samples", args.max_validation_samples)):
        if value is not None and value <= 0:
            parser.error(f"--{name} must be positive")
    if not math.isfinite(args.lr) or args.lr <= 0 or not math.isfinite(args.l2) or args.l2 < 0:
        parser.error("--lr must be finite and positive and --l2 must be finite and nonnegative")
    if args.validation_split is not None and not 0 <= args.validation_split <= 1:
        parser.error("--validation-split must be between 0 and 1")
    try:
        if args.manifest:
            run_fixed_training(args, config)
        else:
            X, y = load_dataset(args.input_jsonl, max_samples=args.max_samples)
            print(f"loaded samples={len(X)} features={len(X[0])}")
            split = 0.1 if args.validation_split is None else args.validation_split
            weights = train(X, y, **config, validation_split=split)
            with open(args.output_model_json, "w", encoding="utf-8") as stream:
                json.dump(export_model(weights), stream)
            print(f"saved model to {args.output_model_json}")
    except (OSError, ValueError, KeyError, TypeError, OverflowError) as error:
        parser.exit(1, f"train_ml_engine: {error}\n")


if __name__ == "__main__":
    main()
