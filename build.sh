#!/bin/sh

g++ -std=c++17 -O3 poker-core/c++/main.cpp poker-core/c++/deck.cpp poker-core/c++/hand.cpp poker-core/c++/card.cpp poker-core/c++/checkforwin.cpp poker-core/c++/autohold.cpp poker-core/c++/evaluator.cpp -o videopoker -lpthread 
g++ -std=c++17 -O3 poker-core/c++/verify_rtp.cpp poker-core/c++/autohold.cpp poker-core/c++/checkforwin.cpp poker-core/c++/card.cpp poker-core/c++/evaluator.cpp -o verify_rtp -lpthread
