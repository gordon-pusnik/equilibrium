import argparse
import json
import math
import random


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

    return W1, b1, W2, b2, W3, b3


def main():
    parser = argparse.ArgumentParser(description="Train tiny ML hold model from videopoker JSONL training data.")
    parser.add_argument("input_jsonl")
    parser.add_argument("output_model_json")
    parser.add_argument("--hidden", type=int, default=64)
    parser.add_argument("--hidden2", type=int, default=32)
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--lr", type=float, default=0.01)
    parser.add_argument("--validation-split", type=float, default=0.1)
    parser.add_argument("--l2", type=float, default=1e-6)
    parser.add_argument("--seed", type=int, default=12345)
    parser.add_argument("--max-samples", type=int, default=None)
    args = parser.parse_args()

    X, y = load_dataset(args.input_jsonl, max_samples=args.max_samples)
    print(f"loaded samples={len(X)} features={len(X[0])}")

    W1, b1, W2, b2, W3, b3 = train(
        X,
        y,
        hidden=args.hidden,
        hidden2=args.hidden2,
        epochs=args.epochs,
        lr=args.lr,
        seed=args.seed,
        validation_split=args.validation_split,
        l2=args.l2,
    )

    model = {
        "format": "videopoker-ml-v3",
        "input_size": len(X[0]),
        "hidden1_size": args.hidden,
        "hidden2_size": args.hidden2,
        "output_size": 5,
        "W1": W1,
        "b1": b1,
        "W2": W2,
        "b2": b2,
        "W3": W3,
        "b3": b3,
    }

    with open(args.output_model_json, "w", encoding="utf-8") as f:
        json.dump(model, f)

    print(f"saved model to {args.output_model_json}")


if __name__ == "__main__":
    main()
