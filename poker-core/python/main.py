import sys

from autohold import print_rule_strategy, set_ml_model
from deck import Deck

def parse_args(argv):
    engine = "solver"
    ml_model = None
    print_strategy = False
    positional = []
    i = 1
    while i < len(argv):
        arg = argv[i]
        if arg == "--engine":
            if i + 1 >= len(argv):
                raise ValueError("--engine requires value: solver|rule")
            engine = argv[i + 1]
            i += 2
            continue
        if arg == "--ml-model":
            if i + 1 >= len(argv):
                raise ValueError("--ml-model requires a model path")
            ml_model = argv[i + 1]
            i += 2
            continue
        if arg == "--print-strategy":
            print_strategy = True
            i += 1
            continue
        positional.append(arg)
        i += 1

    if len(positional) not in (0, 3):
        raise ValueError("usage: python main.py [--engine solver|rule|ml] [--ml-model model.json] [--print-strategy] [coins bet iterations]")

    if engine not in ("solver", "rule", "ml"):
        raise ValueError(f"invalid engine: {engine} (expected solver|rule|ml)")

    if engine == "ml" and ml_model is None:
        raise ValueError("engine ml requires --ml-model <path>")

    if len(positional) == 0:
        return None, None, None, engine, ml_model, print_strategy

    coins = int(positional[0])
    bet = int(positional[1])
    iterations = int(positional[2])
    return coins, bet, iterations, engine, ml_model, print_strategy

if __name__ == "__main__":
    try:
        coins, bet, iterations, engine, ml_model, print_strategy = parse_args(sys.argv)
    except ValueError as exc:
        print(f"Error - {exc}")
        raise SystemExit(1)

    if engine == "ml":
        set_ml_model(ml_model)

    if print_strategy:
        print("Rule engine strategy table:")
        print_rule_strategy()
        if coins is None:
            raise SystemExit(0)
        print()

    print("Running", coins, "coins with a bet of", bet, "for", iterations, "iterations using engine", engine)

    deck = Deck(True)

    for i in range(iterations):
        if coins < bet:
            print("Not enough coins to cover bet, exiting.")
            break
        print("Start hand", i + 1, "-", coins, "coins")
        coins -= bet
        deck.shuffle()
        deck.new_hand()
        deck.hand.auto_hold(bet, engine)
        deck.hand.to_console()
        deck.draw_cards()
        coins += deck.hand.check_for_win(bet)
        deck.hand.to_console()
        print("End hand", i + 1, "-", coins, "coins")
