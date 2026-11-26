#!/bin/sh

set -e
mkdir -p build

cli_policy=poker-core/c++/cli_hold_policy.cpp
g++ -std=c++17 -O3 poker-core/c++/main.cpp poker-core/c++/deck.cpp poker-core/c++/hand.cpp poker-core/c++/card.cpp poker-core/c++/checkforwin.cpp poker-core/c++/autohold.cpp poker-core/c++/game_variant.cpp poker-core/c++/evaluator.cpp "$cli_policy" -o build/videopoker -lpthread
g++ -std=c++17 -O3 poker-core/c++/verify_rtp.cpp poker-core/c++/autohold.cpp poker-core/c++/checkforwin.cpp poker-core/c++/card.cpp poker-core/c++/game_variant.cpp poker-core/c++/evaluator.cpp "$cli_policy" -o build/verify_rtp -lpthread
g++ -std=c++17 -O3 poker-core/c++/benchmark_ml.cpp poker-core/c++/autohold.cpp poker-core/c++/checkforwin.cpp poker-core/c++/card.cpp poker-core/c++/game_variant.cpp poker-core/c++/evaluator.cpp "$cli_policy" -o build/benchmark_ml -lpthread
