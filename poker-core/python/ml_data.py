"""Shared hand validation, equivalence and sampling for ML research tools."""
import hashlib
import random
from pathlib import Path

VARIANTS = ("jacks_or_better_9_6", "jacks_or_better_8_5")


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
    # Sorted suit rank-bitsets are invariant under card order and global suit
    # renaming, including repeated ranks and several cards of the same suit.
    suits = [0] * 4
    for card in ids:
        suits[card // 13] |= 1 << (card % 13)
    return tuple(sorted(suits))


def validate_training_row(row, variant, bet):
    """Require explicit solver provenance; return the initial hand's card IDs.

    This checks the export contract, not the optimality of the claimed label.
    Solver EV evaluation remains the authority for strategy correctness.
    """
    if not isinstance(row, dict):
        raise ValueError("Training rows must be JSON objects")
    if row.get("engine") != "solver":
        raise ValueError("Training rows require engine=solver")
    if row.get("variant") != variant:
        raise ValueError(f"Training rows require variant={variant}")
    if type(row.get("bet")) is not int or row["bet"] != bet:
        raise ValueError(f"Training rows require integer bet={bet}")
    mask = row.get("hold_mask")
    if type(mask) is not int or not 0 <= mask <= 31:
        raise ValueError("hold_mask must be an integer in 0..31")
    ids = hand_ids(row.get("initial"))
    if "final" in row:
        hand_ids(row["final"])
    if "payout" in row and (type(row["payout"]) is not int or row["payout"] < 0):
        raise ValueError("payout must be a nonnegative integer")
    return ids


def sample_hands(count, seed, exclusions):
    if type(count) is not int or count <= 0:
        raise ValueError("Hand count must be a positive integer")
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
