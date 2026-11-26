"""Export a selected research fold to the CLI-only ml-rerank JSON format."""
import argparse
import json
import math
from pathlib import Path

from ml_data import VARIANTS, sha256


def parameters(state, sizes):
    result = []
    for index, (inputs, outputs) in zip((0, 2, 4), zip(sizes, sizes[1:])):
        weights, biases = state[f"{index}.weight"], state[f"{index}.bias"]
        if tuple(weights.shape) != (outputs, inputs) or tuple(biases.shape) != (outputs,):
            raise ValueError(f"Wrong checkpoint dimensions at layer {index}")
        for row, bias in zip(weights.tolist(), biases.tolist()):
            result.extend((bias, *row))
    return result


def export(fold_dir, plan_path, variant, output):
    # PyTorch is only required to export research checkpoints, not to run them.
    import torch

    plan = json.loads(plan_path.read_text())
    selection = json.loads((fold_dir / "selection.json").read_text())
    if (selection["plan_sha256"] != sha256(plan_path) or plan["bet"] != 5
            or variant not in plan["variants"].values()):
        raise ValueError("Fold selection, plan, variant or bet do not match")
    # The research plan spans both paytables; fold directories identify which
    # one was used to label and train the checkpoint.
    table = {"jacks_or_better_9_6": "96", "jacks_or_better_8_5": "85"}[variant]
    if not fold_dir.name.startswith(f"{table}-fold-") or selection["selected_policy"] != "active":
        raise ValueError("Expected an active fold checkpoint for the requested paytable")
    state = []
    for name, sizes in (("base.pt", (103, 64, 64, 1)), ("active.pt", (311, 64, 32, 1))):
        checkpoint = fold_dir / name
        expected = [digest for path, digest in selection["files"].items() if Path(path).name == name]
        if expected != [sha256(checkpoint)]:
            raise ValueError(f"Checkpoint hash mismatch: {checkpoint}")
        state.append(parameters(torch.load(checkpoint, map_location="cpu", weights_only=True), sizes))
    active = selection["active"]
    margin, gain = active["margin_limit"], active["predicted_gain_threshold"]
    if not all(math.isfinite(x) and x >= 0 for x in (margin, gain)):
        raise ValueError("Invalid thresholds")
    # Emit one parameter vector per line without losing float32 precision.
    parts = ["equilibrium-ml-rerank-v1", variant, 5, margin, gain, *state]
    text = "[\n" + ",\n".join(json.dumps(p, separators=(",", ":"), allow_nan=False) for p in parts) + "\n]\n"
    with output.open("x", encoding="utf-8") as stream:
        stream.write(text)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fold-dir", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--variant", choices=VARIANTS, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    export(args.fold_dir, args.plan, args.variant, args.output)


if __name__ == "__main__":
    main()
