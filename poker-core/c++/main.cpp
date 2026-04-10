#include <array>
#include <cstdint>
#include <ctime>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>
#include <memory>
#include <thread>
#include <mutex>
#include <sstream>

#include "autohold.h"
#include "card.h"
#include "checkforwin.h"
#include "deck.h"
#include "game_variant.h"
#include "hand.h"

int main(int argc, char *argv[]) {
    std::string engine_name = "solver";
    std::string ml_model_path;
    GameVariant variant = GameVariant::JACKS_OR_BETTER_9_6;
    bool print_strategy = false;
    std::string dump_training_path;
    std::vector<std::string> positional;

    for (int i = 1; i < argc; i++) {
        const std::string arg = argv[i];
        if (arg == "--engine") {
            if (i + 1 >= argc) {
                std::cout << "Error - --engine requires value: solver|rule|ml" << std::endl;
                return 1;
            }
            engine_name = argv[++i];
        } else if (arg == "--variant") {
            if (i + 1 >= argc) {
                std::cout << "Error - --variant requires value: jacks_or_better_9_6|jacks_or_better_8_5" << std::endl;
                return 1;
            }
            if (!parse_game_variant_id(argv[++i], variant)) {
                std::cout << "Error - invalid variant: " << argv[i] << std::endl;
                return 1;
            }
        } else if (arg == "--ml-model") {
            if (i + 1 >= argc) {
                std::cout << "Error - --ml-model requires model path" << std::endl;
                return 1;
            }
            ml_model_path = argv[++i];
        } else if (arg == "--print-strategy") {
            print_strategy = true;
        } else if (arg == "--dump-training") {
            if (i + 1 >= argc) {
                std::cout << "Error - --dump-training requires output path" << std::endl;
                return 1;
            }
            dump_training_path = argv[++i];
        } else {
            positional.push_back(arg);
        }
    }

    if (positional.size() != 3 && positional.size() != 0) {
        std::cout << "Error - usage: main [--engine solver|rule|ml] [--variant jacks_or_better_9_6|jacks_or_better_8_5] [--ml-model model.json] [--print-strategy] [--dump-training path.jsonl] [coins bet iterations]" << std::endl;
        return 1;
    }

    if (!AutoHold::set_engine(engine_name.c_str())) {
        std::cout << "Error - invalid engine: " << engine_name << " (expected solver|rule|ml)" << std::endl;
        return 1;
    }

    if (engine_name == "ml") {
        if (ml_model_path.empty()) {
            std::cout << "Error - engine ml requires --ml-model <path>" << std::endl;
            return 1;
        }
        if (!AutoHold::set_ml_model(ml_model_path.c_str())) {
            std::cout << "Error - failed to load ml model from: " << ml_model_path << std::endl;
            return 1;
        }
    }

    if (engine_name != "ml" && !ml_model_path.empty()) {
        std::cout << "Error - --ml-model can only be used with --engine ml" << std::endl;
        return 1;
    }

    if (print_strategy) {
        std::cout << "Rule engine strategy table:" << std::endl;
        AutoHold::print_rule_strategy();
        if (positional.empty()) {
            return 0;
        }
        std::cout << std::endl;
    }

    if (positional.size() != 3) {
        std::cout << "Error - usage: main [--engine solver|rule|ml] [--variant jacks_or_better_9_6|jacks_or_better_8_5] [--ml-model model.json] [--print-strategy] [--dump-training path.jsonl] [coins bet iterations]" << std::endl;
        return 1;
    }

    const GameVariantInfo& variant_info = game_variant_info(variant);
    uint32_t coins = atoi(positional[0].c_str());
    uint32_t bet = atoi(positional[1].c_str());
    uint32_t iterations = atoi(positional[2].c_str());
    std::cout << "Running " << coins << " coins with a bet of " << bet
              << " for " << iterations << " iterations"
              << " using engine " << engine_name
              << " on variant " << variant_info.id << std::endl;

    const bool dump_training = !dump_training_path.empty();
    if (dump_training) {
        AutoHold::set_verbose(false);
        std::ofstream training_out(dump_training_path);
        if (!training_out) {
            std::cout << "Error - could not open training output file: " << dump_training_path << std::endl;
            return 1;
        }

        std::mutex file_mutex;
        std::mutex coins_mutex;
        uint32_t num_threads = std::thread::hardware_concurrency();
        if (num_threads == 0) num_threads = 1;
        
        std::cout << "Dumping training data using " << num_threads << " threads..." << std::endl;

        std::vector<std::thread> threads;
        for (uint32_t t = 0; t < num_threads; t++) {
            threads.emplace_back([&, t, num_threads]() {
                auto deck = std::make_unique<Deck>();
                deck->init(static_cast<uint32_t>(time(NULL)) + t);
                
                uint32_t thread_iterations = iterations / num_threads;
                if (t == num_threads - 1) thread_iterations += iterations % num_threads;

                std::stringstream ss;
                for (uint32_t i = 0; i < thread_iterations; i++) {
                    {
                        std::lock_guard<std::mutex> lock(coins_mutex);
                        if (coins < bet) break;
                        coins -= bet;
                    }

                    deck->shuffle();
                    deck->new_hand();
                    deck->hand()->auto_hold(bet, variant);

                    auto initial_cards_ptr = deck->hand()->cards();
                    uint32_t hold_mask = 0;
                    for (uint32_t c = 0; c < 5; c++) {
                        if (initial_cards_ptr[c]->is_held()) {
                            hold_mask |= (1u << c);
                        }
                    }

                    deck->draw_cards();
                    auto final_cards_ptr = deck->hand()->cards();
                    const uint32_t win_type = CheckForWin::check_for_win(final_cards_ptr);
                    const uint32_t winnings = payout_for_result(win_type, bet, variant);

                    {
                        std::lock_guard<std::mutex> lock(coins_mutex);
                        coins += winnings;
                    }

                    ss << "{\"engine\":\"" << engine_name << "\",\"variant\":\"" << variant_info.id << "\",\"bet\":" << bet
                       << ",\"initial\":[";
                    for (uint32_t c = 0; c < 5; c++) {
                        if (c > 0) ss << ",";
                        ss << "{\"s\":" << initial_cards_ptr[c]->suit() << ",\"r\":" << initial_cards_ptr[c]->rank() << "}";
                    }
                    ss << "],\"hold_mask\":" << hold_mask
                       << ",\"final\":[";
                    for (uint32_t c = 0; c < 5; c++) {
                        if (c > 0) ss << ",";
                        ss << "{\"s\":" << final_cards_ptr[c]->suit() << ",\"r\":" << final_cards_ptr[c]->rank() << "}";
                    }
                    ss << "],\"payout\":" << winnings << "}\n";

                    if (i % 1000 == 0) {
                        std::lock_guard<std::mutex> lock(file_mutex);
                        training_out << ss.str();
                        ss.str("");
                        ss.clear();
                    }
                }
                std::lock_guard<std::mutex> lock(file_mutex);
                training_out << ss.str();
            });
        }

        for (auto& th : threads) {
            th.join();
        }
        std::cout << "Training data written to " << dump_training_path << std::endl;
        return 0;
    }

    // Normal non-training path
    auto deck = std::make_unique<Deck>();
    deck->init(static_cast<uint32_t>(time(NULL)));

    for (uint32_t i = 0; i < iterations; i++) {
        if (coins < bet) {
            std::cout << "Not enough coins to cover bet, exiting." << std::endl;
            break;
        }
        std::cout << "Start hand " << i + 1 << " - " << coins << " coins - bet " << bet << std::endl;

        coins -= bet;
        deck->shuffle();
        deck->new_hand();
        deck->hand()->auto_hold(bet, variant);
        deck->hand()->to_console();
        
        deck->draw_cards();
        uint32_t winnings = deck->hand()->check_for_win(bet, variant);
        deck->hand()->to_console();

        coins += winnings;
        std::cout << "End hand " << i + 1 << " - " << coins << " coins" << std::endl;
    }

    return 0;
}
