import math
import random
import sys

from autohold import auto_hold, set_ml_model, set_verbose
from card import Rank, Suit


class SimCard:
    def __init__(self, suit, rank):
        self.suit = suit
        self.rank = rank
        self.held = False
        self.kept = False

    def is_held(self):
        return self.held

    def set_held(self, held):
        self.held = held

    def set_kept(self, kept):
        self.kept = kept

    def is_kept(self):
        return self.kept



def payout_for_cards(cards, bet):
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



def make_deck():
    deck = []
    for suit in range(int(Suit.SPADES), int(Suit.DIAMONDS) + 1):
        for rank in range(int(Rank.TWO), int(Rank.ACE) + 1):
            deck.append((suit, rank))
    return deck



def main():
    engine = "solver"
    ml_model = None
    positional = []

    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == "--engine":
            if i + 1 >= len(sys.argv):
                print("Error - --engine requires value: solver|rule|ml")
                return 1
            engine = sys.argv[i + 1]
            i += 2
            continue
        if arg == "--ml-model":
            if i + 1 >= len(sys.argv):
                print("Error - --ml-model requires a model path")
                return 1
            ml_model = sys.argv[i + 1]
            i += 2
            continue
        positional.append(arg)
        i += 1

    if len(positional) < 2 or len(positional) > 4:
        print("Usage: verify_rtp.py [--engine solver|rule|ml] [--ml-model model.json] hands_per_run runs [bet=5] [seed=12345]")
        return 1

    if engine not in ("solver", "rule", "ml"):
        print(f"Error - invalid engine: {engine} (expected solver|rule|ml)")
        return 1

    if engine == "ml":
        if ml_model is None:
            print("Error - engine ml requires --ml-model <path>")
            return 1
        set_ml_model(ml_model)

    hands_per_run = int(positional[0])
    runs = int(positional[1])
    bet = int(positional[2]) if len(positional) >= 3 else 5
    base_seed = int(positional[3]) if len(positional) >= 4 else 12345

    if hands_per_run <= 0 or runs <= 0 or bet <= 0 or bet > 5:
        print("Invalid args: hands_per_run>0, runs>0, 1<=bet<=5 required.")
        return 1

    target_rtp = 0.995439
    full_deck = make_deck()

    set_verbose(False)

    sum_x = 0.0
    sum_x2 = 0.0
    total_hands = 0

    for run in range(runs):
        rng = random.Random(base_seed + run)
        run_sum_x = 0.0

        for _ in range(hands_per_run):
            shuffled = full_deck[:]
            rng.shuffle(shuffled)

            cards = [
                SimCard(*shuffled[0]),
                SimCard(*shuffled[1]),
                SimCard(*shuffled[2]),
                SimCard(*shuffled[3]),
                SimCard(*shuffled[4]),
            ]

            auto_hold(cards[0], cards[1], cards[2], cards[3], cards[4], bet, engine)

            final_cards = [
                (cards[0].suit, cards[0].rank),
                (cards[1].suit, cards[1].rank),
                (cards[2].suit, cards[2].rank),
                (cards[3].suit, cards[3].rank),
                (cards[4].suit, cards[4].rank),
            ]

            draw_pos = 5
            for i in range(5):
                if not cards[i].is_held():
                    final_cards[i] = shuffled[draw_pos]
                    draw_pos += 1

            payout = payout_for_cards(final_cards, bet)
            x = payout / bet
            run_sum_x += x
            sum_x += x
            sum_x2 += x * x
            total_hands += 1

        run_rtp = run_sum_x / hands_per_run
        print(f"Run {run + 1} RTP: {run_rtp:.6f} ({run_rtp * 100.0:.6f}%)")

    mean = sum_x / total_hands
    variance = (sum_x2 / total_hands) - (mean * mean)
    if variance < 0.0:
        variance = 0.0
    se = math.sqrt(variance / total_hands)
    margin = 1.96 * se
    ci_lo = mean - margin
    ci_hi = mean + margin

    print()
    print(f"Hands: {total_hands}  Bet: {bet}  Engine: {engine}  Seed base: {base_seed}")
    print(f"Estimated RTP: {mean:.6f} ({mean * 100.0:.6f}%)")
    print(f"95% CI: [{ci_lo:.6f}, {ci_hi:.6f}]  => [{ci_lo * 100.0:.6f}%, {ci_hi * 100.0:.6f}%]")
    print(f"Target RTP: {target_rtp:.6f} ({target_rtp * 100.0:.6f}%)")
    print(f"Delta (estimate - target): {mean - target_rtp:+.6f}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
