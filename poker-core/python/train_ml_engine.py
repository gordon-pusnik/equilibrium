import argparse
import json
import math
import random


def encode_hand(initial, bet):
    x = [0.0] * 261
    for pos, card in enumerate(initial):
        s = int(card["s"])
        r = int(card["r"])
        card_id = (s - 1) * 13 + (r - 2)
        x[pos * 52 + card_id] = 1.0
    x[260] = float(bet) / 5.0
    return x


def load_dataset(path, max_samples=None):
    X = []
    y = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            row = json.loads(line)
            X.append(encode_hand(row["initial"], row.get("bet", 5)))
            y.append(int(row["hold_mask"]))
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


def forward(x, W1, b1, W2, b2):
    hidden = len(b1)
    out = len(b2)

    h_pre = [0.0] * hidden
    h = [0.0] * hidden
    for j in range(hidden):
        v = b1[j]
        col = W1[j]
        for i in range(len(x)):
            v += x[i] * col[i]
        h_pre[j] = v
        h[j] = relu(v)

    logits = [0.0] * out
    for k in range(out):
        v = b2[k]
        col = W2[k]
        for j in range(hidden):
            v += h[j] * col[j]
        logits[k] = v

    return h_pre, h, logits


def predict_mask(x, W1, b1, W2, b2):
    _, _, logits = forward(x, W1, b1, W2, b2)
    best_idx = 0
    best_v = logits[0]
    for i in range(1, len(logits)):
        if logits[i] > best_v:
            best_v = logits[i]
            best_idx = i
    return best_idx


def train(X, y, hidden=64, epochs=10, lr=0.01, seed=12345):
    rng = random.Random(seed)

    d = len(X[0])
    k = 32

    W1 = [[(rng.random() * 2.0 - 1.0) * math.sqrt(2.0 / d) for _ in range(d)] for _ in range(hidden)]
    b1 = [0.0 for _ in range(hidden)]
    W2 = [[(rng.random() * 2.0 - 1.0) * math.sqrt(2.0 / hidden) for _ in range(hidden)] for _ in range(k)]
    b2 = [0.0 for _ in range(k)]

    n = len(X)

    for epoch in range(1, epochs + 1):
        order = list(range(n))
        rng.shuffle(order)

        total_loss = 0.0
        correct = 0

        for idx in order:
            x = X[idx]
            target = y[idx]

            h_pre, h, logits = forward(x, W1, b1, W2, b2)
            probs = softmax(logits)
            total_loss += -math.log(max(probs[target], 1e-12))
            if max(range(k), key=lambda i: logits[i]) == target:
                correct += 1

            dlogits = probs[:]
            dlogits[target] -= 1.0

            for out_i in range(k):
                g = dlogits[out_i]
                for j in range(hidden):
                    W2[out_i][j] -= lr * g * h[j]
                b2[out_i] -= lr * g

            dh = [0.0] * hidden
            for j in range(hidden):
                s = 0.0
                for out_i in range(k):
                    s += dlogits[out_i] * W2[out_i][j]
                dh[j] = s

            dz = [dh[j] if h_pre[j] > 0.0 else 0.0 for j in range(hidden)]

            for j in range(hidden):
                g = dz[j]
                row = W1[j]
                for i in range(d):
                    row[i] -= lr * g * x[i]
                b1[j] -= lr * g

        loss = total_loss / n
        acc = correct / n
        print(f"epoch {epoch:02d} loss={loss:.4f} acc={acc:.4f}")

    return W1, b1, W2, b2


def main():
    parser = argparse.ArgumentParser(description="Train tiny ML hold model from videopoker JSONL training data.")
    parser.add_argument("input_jsonl")
    parser.add_argument("output_model_json")
    parser.add_argument("--hidden", type=int, default=32)
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--lr", type=float, default=0.01)
    parser.add_argument("--seed", type=int, default=12345)
    parser.add_argument("--max-samples", type=int, default=None)
    args = parser.parse_args()

    X, y = load_dataset(args.input_jsonl, max_samples=args.max_samples)
    print(f"loaded samples={len(X)} features={len(X[0])}")

    W1, b1, W2, b2 = train(
        X,
        y,
        hidden=args.hidden,
        epochs=args.epochs,
        lr=args.lr,
        seed=args.seed,
    )

    model = {
        "format": "videopoker-ml-v1",
        "input_size": len(X[0]),
        "hidden_size": args.hidden,
        "output_size": 32,
        "W1": W1,
        "b1": b1,
        "W2": W2,
        "b2": b2,
    }

    with open(args.output_model_json, "w", encoding="utf-8") as f:
        json.dump(model, f)

    print(f"saved model to {args.output_model_json}")


if __name__ == "__main__":
    main()
