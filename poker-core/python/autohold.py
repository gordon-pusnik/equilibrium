from itertools import combinations

from card import Rank, Suit
from hand_type import HandType
from checkforwin import check_for_win
import json

# Cache: (bet, sorted 5 card ids) -> best hold mask (0..31)
_best_mask_cache = {}
_verbose = True
_ml_model = None

_RULE_STRATEGY_TABLE = [
    "Pat Royal Flush",
    "Pat Straight Flush",
    "Pat Four of a Kind",
    "4 to Royal Flush",
    "Pat Full House",
    "Pat Flush",
    "Pat Three of a Kind",
    "Pat Straight",
    "4 to Straight Flush",
    "Pat Two Pair",
    "Pat High Pair (Jacks+)",
    "3 to Royal Flush",
    "4 to Flush",
    "Pat Low Pair",
    "4 to Outside Straight",
    "2 Suited High Cards",
    "3 to Straight Flush (Strong)",
    "2 Unsuited High Cards",
    "Suited TJ",
    "Suited QJ",
    "Suited KQ",
    "Suited JK",
    "Suited AK/AQ/AJ",
    "Unsuited TJ",
    "Unsuited QJ",
    "Unsuited KQ",
    "Unsuited JK",
    "Suited AT",
    "Suited KT",
    "Suited QT",
    "3 to Straight Flush (Medium)",
    "4 to Inside Straight (3+ High)",
    "One Ace",
    "One King",
    "One Queen",
    "One Jack",
    "One Ten",
    "Hold Nothing",
]


def print_rule_strategy():
    for idx, row in enumerate(_RULE_STRATEGY_TABLE, start=1):
        print(f"{idx:2d}. {row}")


def set_verbose(verbose: bool):
    global _verbose
    _verbose = verbose


def set_ml_model(path: str):
    global _ml_model
    with open(path, "r", encoding="utf-8") as f:
        _ml_model = json.load(f)


def _require_ml_model():
    if _ml_model is None:
        raise ValueError("ml engine selected but no model loaded; pass --ml-model <path>")


def _card_suit(card):
    return int(card.suit)


def _card_rank(card):
    return int(card.rank)


def _card_id(card):
    # Canonical 0..51 id
    return (_card_suit(card) - int(Suit.SPADES)) * 13 + (_card_rank(card) - int(Rank.TWO))


def _hand_cache_key(cards, bet):
    ids = sorted(_card_id(c) for c in cards)
    return (int(bet), tuple(ids))


def _make_full_deck():
    deck = []
    for suit in range(int(Suit.SPADES), int(Suit.DIAMONDS) + 1):
        for rank in range(int(Rank.TWO), int(Rank.ACE) + 1):
            deck.append((suit, rank))
    return deck


_FULL_DECK = _make_full_deck()


def _payout_for_cards(cards, bet):
    rank_count = [0] * 15
    suit_count = [0] * 5
    ranks = []

    for suit, rank in cards:
        rank_count[rank] += 1
        suit_count[suit] += 1
        ranks.append(rank)

    flush = any(suit_count[s] == 5 for s in range(int(Suit.SPADES), int(Suit.DIAMONDS) + 1))

    ranks.sort()

    straight = True
    for i in range(1, 5):
        if ranks[i - 1] + 1 != ranks[i]:
            straight = False
            break

    if (
        not straight
        and ranks[0] == int(Rank.TWO)
        and ranks[1] == int(Rank.THREE)
        and ranks[2] == int(Rank.FOUR)
        and ranks[3] == int(Rank.FIVE)
        and ranks[4] == int(Rank.ACE)
    ):
        straight = True

    four = False
    three = False
    pair_count = 0
    high_pair = False
    for rank in range(int(Rank.TWO), int(Rank.ACE) + 1):
        if rank_count[rank] == 4:
            four = True
        elif rank_count[rank] == 3:
            three = True
        elif rank_count[rank] == 2:
            pair_count += 1
            if rank >= int(Rank.JACK):
                high_pair = True

    if flush and straight:
        if (
            ranks[0] == int(Rank.TEN)
            and ranks[1] == int(Rank.JACK)
            and ranks[2] == int(Rank.QUEEN)
            and ranks[3] == int(Rank.KING)
            and ranks[4] == int(Rank.ACE)
        ):
            return bet * 800 if bet == 5 else bet * 250
        return bet * 50

    if four:
        return bet * 25
    if three and pair_count == 1:
        return bet * 9
    if flush:
        return bet * 6
    if straight:
        return bet * 4
    if three:
        return bet * 3
    if pair_count == 2:
        return bet * 2
    if high_pair:
        return bet
    return 0


def _evaluate_mask_ev(remaining, discard_slots, base_cards, bet):
    discard_count = len(discard_slots)

    if discard_count == 0:
        return _payout_for_cards(base_cards, bet), 1

    total_payout = 0
    ways = 0

    for drawn_cards in combinations(remaining, discard_count):
        final_cards = list(base_cards)
        for i, slot in enumerate(discard_slots):
            final_cards[slot] = drawn_cards[i]
        total_payout += _payout_for_cards(final_cards, bet)
        ways += 1

    return total_payout, ways


def _solver_auto_hold(cards, bet):
    cache_key = _hand_cache_key(cards, bet)

    cached_mask = _best_mask_cache.get(cache_key)
    if cached_mask is not None:
        for i, c in enumerate(cards):
            c.set_held((cached_mask & (1 << i)) != 0)
        if _verbose:
            print("Hold exact EV-optimal")
        return 0

    in_hand_ids = {_card_id(c) for c in cards}
    remaining = [deck_card for idx, deck_card in enumerate(_FULL_DECK) if idx not in in_hand_ids]

    best_mask = 0
    best_total = 0
    best_ways = 1
    have_best = False

    for mask in range(32):
        base_cards = [(_card_suit(c), _card_rank(c)) for c in cards]
        discard_slots = [i for i in range(5) if (mask & (1 << i)) == 0]

        total_payout, ways = _evaluate_mask_ev(remaining, discard_slots, base_cards, int(bet))

        if not have_best:
            best_mask = mask
            best_total = total_payout
            best_ways = ways
            have_best = True
            continue

        if total_payout * best_ways > best_total * ways:
            best_mask = mask
            best_total = total_payout
            best_ways = ways

    for i, c in enumerate(cards):
        c.set_held((best_mask & (1 << i)) != 0)

    _best_mask_cache[cache_key] = best_mask

    if _verbose:
        print("Hold exact EV-optimal")

    return 0


def _ml_features(cards, bet):
    x = [0.0] * 261
    for pos, c in enumerate(cards):
        card_id = (_card_suit(c) - int(Suit.SPADES)) * 13 + (_card_rank(c) - int(Rank.TWO))
        x[pos * 52 + card_id] = 1.0
    x[260] = float(bet) / 5.0
    return x


def _ml_auto_hold(cards, bet):
    _require_ml_model()
    x = _ml_features(cards, bet)
    W1 = _ml_model["W1"]
    b1 = _ml_model["b1"]
    W2 = _ml_model["W2"]
    b2 = _ml_model["b2"]

    h = []
    for j in range(len(b1)):
        v = b1[j]
        col = W1[j]
        for i in range(len(x)):
            v += x[i] * col[i]
        h.append(v if v > 0.0 else 0.0)

    best_mask = 0
    best_logit = None
    for k in range(len(b2)):
        v = b2[k]
        col = W2[k]
        for j in range(len(h)):
            v += h[j] * col[j]
        if best_logit is None or v > best_logit:
            best_logit = v
            best_mask = k

    mask = int(best_mask)
    _apply_mask(cards, mask)
    if _verbose:
        print("Hold ml-model")
    return 0


def _held_indices(mask):
    return [i for i in range(5) if (mask & (1 << i)) != 0]


def _mask_rank_score(cards, mask):
    return sum(_card_rank(cards[i]) for i in _held_indices(mask))


def _apply_mask(cards, mask):
    for i, c in enumerate(cards):
        c.set_held((mask & (1 << i)) != 0)


def _set_held_from_kept(cards):
    for c in cards:
        c.set_held(c.is_kept())


def _is_straight_ranks(ranks):
    r = sorted(ranks)
    if all(r[i - 1] + 1 == r[i] for i in range(1, len(r))):
        return True
    return len(r) == 5 and r == [int(Rank.TWO), int(Rank.THREE), int(Rank.FOUR), int(Rank.FIVE), int(Rank.ACE)]


def _mask_ranks(cards, mask):
    return [_card_rank(cards[i]) for i in _held_indices(mask)]


def _mask_same_suit(cards, mask):
    idx = _held_indices(mask)
    if not idx:
        return False
    suit = _card_suit(cards[idx[0]])
    return all(_card_suit(cards[i]) == suit for i in idx)


def _mask_is_n_to_royal(cards, mask, n):
    idx = _held_indices(mask)
    if len(idx) != n or not _mask_same_suit(cards, mask):
        return False
    royal = {int(Rank.TEN), int(Rank.JACK), int(Rank.QUEEN), int(Rank.KING), int(Rank.ACE)}
    return all(_card_rank(cards[i]) in royal for i in idx)


def _mask_is_n_to_flush(cards, mask, n):
    return len(_held_indices(mask)) == n and _mask_same_suit(cards, mask)


def _mask_is_low_pair(cards, mask):
    ranks = _mask_ranks(cards, mask)
    return len(ranks) == 2 and ranks[0] == ranks[1] and ranks[0] < int(Rank.JACK)


def _mask_is_4_to_outside_straight(cards, mask):
    ranks = sorted(set(_mask_ranks(cards, mask)))
    return len(ranks) == 4 and (ranks[-1] - ranks[0] == 3) and _is_straight_ranks(ranks)


def _mask_is_4_to_inside_straight(cards, mask):
    ranks = sorted(set(_mask_ranks(cards, mask)))
    if len(ranks) != 4:
        return False
    for start in range(int(Rank.ACE) - 4, int(Rank.TWO) - 1, -1):
        straight = [start, start + 1, start + 2, start + 3, start + 4]
        if start == int(Rank.ACE) - 4:
            straight = [int(Rank.ACE), int(Rank.TWO), int(Rank.THREE), int(Rank.FOUR), int(Rank.FIVE)]
        if all(r in straight for r in ranks):
            missing = [r for r in straight if r not in ranks]
            if len(missing) == 1:
                m = missing[0]
                if m != min(straight) and m != max(straight):
                    return True
    return False


def _mask_is_4_to_straight_flush(cards, mask):
    ranks = _mask_ranks(cards, mask)
    if len(ranks) != 4 or not _mask_same_suit(cards, mask) or len(set(ranks)) != 4:
        return False
    for draw_rank in range(int(Rank.TWO), int(Rank.ACE) + 1):
        if draw_rank in ranks:
            continue
        if _is_straight_ranks(ranks + [draw_rank]):
            return True
    return False


def _mask_is_3_to_straight_flush(cards, mask, min_high, max_gaps):
    ranks = sorted(_mask_ranks(cards, mask))
    if len(ranks) != 3 or not _mask_same_suit(cards, mask) or len(set(ranks)) != 3:
        return False

    highs = sum(1 for r in ranks if r >= int(Rank.JACK))
    if highs < min_high:
        return False

    gaps = (ranks[-1] - ranks[0]) - 2
    if gaps < 0 or gaps > max_gaps:
        return False

    rank_set = set(ranks)
    for a in range(int(Rank.TWO), int(Rank.ACE) + 1):
        if a in rank_set:
            continue
        for b in range(a + 1, int(Rank.ACE) + 1):
            if b in rank_set:
                continue
            if _is_straight_ranks(ranks + [a, b]):
                return True
    return False


def _mask_is_2_suited_high(cards, mask):
    idx = _held_indices(mask)
    return len(idx) == 2 and _mask_same_suit(cards, mask) and all(_card_rank(cards[i]) >= int(Rank.JACK) for i in idx)


def _mask_is_2_unsuited_high(cards, mask):
    idx = _held_indices(mask)
    return (
        len(idx) == 2
        and _card_suit(cards[idx[0]]) != _card_suit(cards[idx[1]])
        and all(_card_rank(cards[i]) >= int(Rank.JACK) for i in idx)
    )


def _mask_is_specific_pair(cards, mask, r1, r2, suited):
    idx = _held_indices(mask)
    if len(idx) != 2:
        return False
    have = sorted([_card_rank(cards[idx[0]]), _card_rank(cards[idx[1]])])
    want = sorted([int(r1), int(r2)])
    if have != want:
        return False
    same_suit = _card_suit(cards[idx[0]]) == _card_suit(cards[idx[1]])
    return same_suit if suited else (not same_suit)


def _mask_is_one_rank(cards, mask, r):
    idx = _held_indices(mask)
    return len(idx) == 1 and _card_rank(cards[idx[0]]) == int(r)


def _mask_inside_with_3_high(cards, mask):
    idx = _held_indices(mask)
    if len(idx) != 4:
        return False
    if not _mask_is_4_to_inside_straight(cards, mask):
        return False
    return sum(1 for i in idx if _card_rank(cards[i]) >= int(Rank.JACK)) >= 3


def _select_best_mask(cards, predicate):
    best_mask = None
    best_score = -1
    for mask in range(1, 32):
        if not predicate(cards, mask):
            continue
        score = _mask_rank_score(cards, mask)
        if best_mask is None or score > best_score:
            best_mask = mask
            best_score = score
    return best_mask


def _rule_auto_hold(cards):
    win = check_for_win(cards[0], cards[1], cards[2], cards[3], cards[4])
    if win != HandType.NONE:
        _set_held_from_kept(cards)
        if _verbose:
            print("Hold rule-based")
        return 0

    chosen = None
    rules = [
        lambda c: _select_best_mask(c, lambda cs, m: _mask_is_n_to_royal(cs, m, 4)),
        lambda c: _select_best_mask(c, _mask_is_4_to_straight_flush),
        lambda c: _select_best_mask(c, lambda cs, m: _mask_is_n_to_royal(cs, m, 3)),
        lambda c: _select_best_mask(c, lambda cs, m: _mask_is_n_to_flush(cs, m, 4)),
        lambda c: _select_best_mask(c, _mask_is_low_pair),
        lambda c: _select_best_mask(c, _mask_is_4_to_outside_straight),
        lambda c: _select_best_mask(c, _mask_is_2_suited_high),
        lambda c: _select_best_mask(c, lambda cs, m: _mask_is_3_to_straight_flush(cs, m, min_high=2, max_gaps=1)),
        lambda c: _select_best_mask(c, _mask_is_2_unsuited_high),
        lambda c: _select_best_mask(c, lambda cs, m: _mask_is_specific_pair(cs, m, Rank.TEN, Rank.JACK, True)),
        lambda c: _select_best_mask(c, lambda cs, m: _mask_is_specific_pair(cs, m, Rank.QUEEN, Rank.JACK, True)),
        lambda c: _select_best_mask(c, lambda cs, m: _mask_is_specific_pair(cs, m, Rank.KING, Rank.QUEEN, True)),
        lambda c: _select_best_mask(c, lambda cs, m: _mask_is_specific_pair(cs, m, Rank.JACK, Rank.KING, True)),
        lambda c: _select_best_mask(
            c,
            lambda cs, m: _mask_is_specific_pair(cs, m, Rank.ACE, Rank.KING, True)
            or _mask_is_specific_pair(cs, m, Rank.ACE, Rank.QUEEN, True)
            or _mask_is_specific_pair(cs, m, Rank.ACE, Rank.JACK, True),
        ),
        lambda c: _select_best_mask(c, lambda cs, m: _mask_is_specific_pair(cs, m, Rank.TEN, Rank.JACK, False)),
        lambda c: _select_best_mask(c, lambda cs, m: _mask_is_specific_pair(cs, m, Rank.QUEEN, Rank.JACK, False)),
        lambda c: _select_best_mask(c, lambda cs, m: _mask_is_specific_pair(cs, m, Rank.KING, Rank.QUEEN, False)),
        lambda c: _select_best_mask(c, lambda cs, m: _mask_is_specific_pair(cs, m, Rank.JACK, Rank.KING, False)),
        lambda c: _select_best_mask(c, lambda cs, m: _mask_is_specific_pair(cs, m, Rank.ACE, Rank.TEN, True)),
        lambda c: _select_best_mask(c, lambda cs, m: _mask_is_specific_pair(cs, m, Rank.KING, Rank.TEN, True)),
        lambda c: _select_best_mask(c, lambda cs, m: _mask_is_specific_pair(cs, m, Rank.QUEEN, Rank.TEN, True)),
        lambda c: _select_best_mask(c, lambda cs, m: _mask_is_3_to_straight_flush(cs, m, min_high=1, max_gaps=2)),
        lambda c: _select_best_mask(c, _mask_inside_with_3_high),
        lambda c: _select_best_mask(c, lambda cs, m: _mask_is_one_rank(cs, m, Rank.ACE)),
        lambda c: _select_best_mask(c, lambda cs, m: _mask_is_one_rank(cs, m, Rank.KING)),
        lambda c: _select_best_mask(c, lambda cs, m: _mask_is_one_rank(cs, m, Rank.QUEEN)),
        lambda c: _select_best_mask(c, lambda cs, m: _mask_is_one_rank(cs, m, Rank.JACK)),
        lambda c: _select_best_mask(c, lambda cs, m: _mask_is_one_rank(cs, m, Rank.TEN)),
    ]

    for picker in rules:
        chosen = picker(cards)
        if chosen is not None:
            break

    _apply_mask(cards, 0 if chosen is None else chosen)

    if _verbose:
        print("Hold rule-based")

    return 0


def auto_hold(card1, card2, card3, card4, card5, bet=5, engine="solver"):
    cards = [card1, card2, card3, card4, card5]

    for c in cards:
        c.set_held(False)
        if hasattr(c, "set_kept"):
            c.set_kept(False)

    if engine == "rule":
        return _rule_auto_hold(cards)
    if engine == "ml":
        return _ml_auto_hold(cards, bet)
    if engine != "solver":
        raise ValueError(f"invalid engine: {engine} (expected solver|rule|ml)")

    return _solver_auto_hold(cards, bet)
