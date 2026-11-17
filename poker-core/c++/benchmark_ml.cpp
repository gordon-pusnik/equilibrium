// Native scoring worker for python/benchmark_ml.py. Input: five ordered deck IDs per line.
#include <array>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>

#include "autohold.h"
#include "card.h"
#include "evaluator.h"
#include "game_variant.h"

int main(int argc, char* argv[]) {
    try {
        std::string model, engine = "ml";
        GameVariant variant = GameVariant::JACKS_OR_BETTER_9_6;
        uint32_t bet = 5;
        for (int i = 1; i < argc; ++i) {
            const std::string arg = argv[i];
            if (i + 1 >= argc) throw std::runtime_error("Missing value for " + arg);
            const std::string value = argv[++i];
            if (arg == "--ml-model") model = value;
            else if (arg == "--engine") engine = value;
            else if (arg == "--variant") {
                if (!parse_game_variant_id(value.c_str(), variant)) throw std::runtime_error("Invalid variant");
            } else if (arg == "--bet") {
                if (value.size() != 1 || value[0] < '1' || value[0] > '5') throw std::runtime_error("Bet must be 1..5");
                bet = static_cast<uint32_t>(value[0] - '0');
            } else throw std::runtime_error("Unknown argument: " + arg);
        }
        if (engine != "ml" && engine != "solver") throw std::runtime_error("Engine must be ml or solver");
        if (engine == "ml" && (model.empty() || !AutoHold::set_ml_model(model.c_str()))) {
            throw std::runtime_error("Failed to load ML model: " + model);
        }
        if (engine == "solver" && !model.empty()) throw std::runtime_error("Solver does not take an ML model");
        AutoHold::set_engine(engine.c_str());
        AutoHold::set_verbose(false);
        std::cout << std::setprecision(17);
        std::string line;
        while (std::getline(std::cin, line)) {
            std::istringstream input(line);
            std::array<int, 5> ids;
            std::array<bool, 52> seen = {};
            for (int& id : ids) {
                if (!(input >> id) || id < 0 || id >= 52 || seen[id]) {
                    throw std::runtime_error("Expected five distinct deck IDs in 0..51");
                }
                seen[id] = true;
            }
            std::string extra;
            if (input >> extra) throw std::runtime_error("Unexpected input after five cards");
            std::array<Card, 5> cards = {
                Card(ids[0] / 13 + 1, ids[0] % 13 + 2),
                Card(ids[1] / 13 + 1, ids[1] % 13 + 2),
                Card(ids[2] / 13 + 1, ids[2] % 13 + 2),
                Card(ids[3] / 13 + 1, ids[3] % 13 + 2),
                Card(ids[4] / 13 + 1, ids[4] % 13 + 2)
            };
            std::array<Card*, 5> ptrs = {&cards[0], &cards[1], &cards[2], &cards[3], &cards[4]};
            const uint32_t mask = AutoHold::auto_hold(ptrs, bet, variant);
            AutoHold::MistakeAnalysis analysis;
            if (!AutoHold::analyze_player_hold(ptrs, bet, variant, mask, analysis) ||
                !std::isfinite(analysis.best_ev) || !std::isfinite(analysis.player_ev)) {
                throw std::runtime_error("Solver analysis failed");
            }
            std::cout << mask << '\t' << analysis.best_mask << '\t' << analysis.best_ev << '\t'
                      << analysis.player_ev << '\t' << PokerEvaluator::evaluate_hand(ptrs).hand_name << '\n';
        }
        if (!std::cin.eof()) throw std::runtime_error("Failed to read hands");
        if (!std::cout) throw std::runtime_error("Failed to write scores");
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "benchmark_ml: " << error.what() << '\n';
        return 1;
    }
}
