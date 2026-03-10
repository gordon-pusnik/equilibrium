#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <random>
#include <string>
#include <vector>

#include "autohold.h"
#include "card.h"

namespace {
struct SimCard {
    uint8_t suit;
    uint8_t rank;
};

uint32_t payout_for_cards(const std::array<SimCard, 5>& cards, uint32_t bet) {
    uint32_t rank_mask = 0;
    uint64_t rank_counts = 0;
    uint32_t suit_mask = 0;

    for (uint32_t i = 0; i < 5; i++) {
        const uint32_t r = cards[i].rank;
        rank_mask |= (1u << r);
        rank_counts += (1ULL << (r * 4));
        suit_mask |= (1u << cards[i].suit);
    }

    const bool flush = (suit_mask == 2 || suit_mask == 4 || suit_mask == 8 || suit_mask == 16);
    
    bool straight = false;
    if (__builtin_popcount(rank_mask) == 5) {
        uint32_t normalized = rank_mask;
        while ((normalized & 1) == 0) normalized >>= 1;
        if (normalized == 0x1F || rank_mask == 0x403C) {
            straight = true;
        }
    }

    if (flush && straight) {
        if (rank_mask == 0x7C00) { // 10, J, Q, K, A
            return (bet == 5) ? (bet * 800) : (bet * 250);
        }
        return bet * 50;
    }

    uint32_t quads = 0;
    uint32_t trips = 0;
    uint32_t pairs = 0;
    uint32_t high_pairs = 0;

    for (uint32_t r = 2; r <= 14; r++) {
        uint32_t c = (rank_counts >> (r * 4)) & 0xF;
        if (c == 4) quads++;
        else if (c == 3) trips++;
        else if (c == 2) {
            pairs++;
            if (r >= 11) high_pairs++;
        }
    }

    if (quads) return bet * 25;
    if (trips && pairs) return bet * 9;
    if (flush) return bet * 6;
    if (straight) return bet * 4;
    if (trips) return bet * 3;
    if (pairs >= 2) return bet * 2;
    if (high_pairs) return bet;

    return 0;
}

std::array<SimCard, 52> make_deck() {
    std::array<SimCard, 52> deck = {};
    uint32_t idx = 0;
    for (uint32_t suit = SPADES; suit <= DIAMONDS; suit++) {
        for (uint32_t rank = TWO; rank <= ACE; rank++) {
            deck[idx++] = {static_cast<uint8_t>(suit), static_cast<uint8_t>(rank)};
        }
    }
    return deck;
}
} // namespace

int main(int argc, char* argv[]) {
    std::string engine = "solver";
    std::string ml_model_path;
    std::vector<std::string> positional;

    for (int i = 1; i < argc; i++) {
        const std::string arg = argv[i];
        if (arg == "--engine") {
            if (i + 1 >= argc) {
                std::cout << "Error - --engine requires value: solver|rule|ml" << std::endl;
                return 1;
            }
            engine = argv[++i];
        } else if (arg == "--ml-model") {
            if (i + 1 >= argc) {
                std::cout << "Error - --ml-model requires model path" << std::endl;
                return 1;
            }
            ml_model_path = argv[++i];
        } else {
            positional.push_back(arg);
        }
    }

    if (positional.size() < 2 || positional.size() > 4) {
        std::cout << "Usage: verify_rtp [--engine solver|rule|ml] [--ml-model model.json] hands_per_run runs [bet=5] [seed=12345]" << std::endl;
        return 1;
    }

    if (!AutoHold::set_engine(engine.c_str())) {
        std::cout << "Error - invalid engine: " << engine << " (expected solver|rule|ml)" << std::endl;
        return 1;
    }

    if (engine == "ml") {
        if (ml_model_path.empty()) {
            std::cout << "Error - engine ml requires --ml-model <path>" << std::endl;
            return 1;
        }
        if (!AutoHold::set_ml_model(ml_model_path.c_str())) {
            std::cout << "Error - failed to load ml model from: " << ml_model_path << std::endl;
            return 1;
        }
    }

    if (engine != "ml" && !ml_model_path.empty()) {
        std::cout << "Error - --ml-model can only be used with --engine ml" << std::endl;
        return 1;
    }

    const uint64_t hands_per_run = std::strtoull(positional[0].c_str(), nullptr, 10);
    const uint32_t runs = static_cast<uint32_t>(std::strtoul(positional[1].c_str(), nullptr, 10));
    const uint32_t bet = (positional.size() >= 3) ? static_cast<uint32_t>(std::strtoul(positional[2].c_str(), nullptr, 10)) : 5;
    const uint64_t base_seed = (positional.size() >= 4) ? std::strtoull(positional[3].c_str(), nullptr, 10) : 12345ULL;

    if (hands_per_run == 0 || runs == 0 || bet == 0 || bet > 5) {
        std::cout << "Invalid args: hands_per_run>0, runs>0, 1<=bet<=5 required." << std::endl;
        return 1;
    }

    const double target_rtp = 0.995439;
    const std::array<SimCard, 52> full_deck = make_deck();

    AutoHold::set_verbose(false);

    long double sum_x = 0.0L;
    long double sum_x2 = 0.0L;
    uint64_t total_hands = 0;

    for (uint32_t run = 0; run < runs; run++) {
        std::mt19937_64 rng(base_seed + run);
        long double run_sum_x = 0.0L;

        for (uint64_t hand = 0; hand < hands_per_run; hand++) {
            std::array<SimCard, 52> shuffled = full_deck;
            std::shuffle(shuffled.begin(), shuffled.end(), rng);

            std::array<Card, 5> cards = {
                Card(shuffled[0].suit, shuffled[0].rank),
                Card(shuffled[1].suit, shuffled[1].rank),
                Card(shuffled[2].suit, shuffled[2].rank),
                Card(shuffled[3].suit, shuffled[3].rank),
                Card(shuffled[4].suit, shuffled[4].rank),
            };

            std::array<Card*, 5> card_ptrs = {&cards[0], &cards[1], &cards[2], &cards[3], &cards[4]};
            AutoHold::auto_hold(card_ptrs, bet);

            std::array<SimCard, 5> final_cards = {
                SimCard{static_cast<uint8_t>(cards[0].suit()), static_cast<uint8_t>(cards[0].rank())},
                SimCard{static_cast<uint8_t>(cards[1].suit()), static_cast<uint8_t>(cards[1].rank())},
                SimCard{static_cast<uint8_t>(cards[2].suit()), static_cast<uint8_t>(cards[2].rank())},
                SimCard{static_cast<uint8_t>(cards[3].suit()), static_cast<uint8_t>(cards[3].rank())},
                SimCard{static_cast<uint8_t>(cards[4].suit()), static_cast<uint8_t>(cards[4].rank())},
            };

            uint32_t draw_pos = 5;
            for (uint32_t i = 0; i < 5; i++) {
                if (!cards[i].is_held()) {
                    final_cards[i] = shuffled[draw_pos++];
                }
            }

            const uint32_t payout = payout_for_cards(final_cards, bet);
            const long double x = static_cast<long double>(payout) / static_cast<long double>(bet);
            run_sum_x += x;
            sum_x += x;
            sum_x2 += x * x;
            total_hands++;
        }

        const long double run_rtp = run_sum_x / static_cast<long double>(hands_per_run);
        std::cout << "Run " << (run + 1) << " RTP: " << std::fixed << std::setprecision(6)
                  << static_cast<double>(run_rtp) << " (" << static_cast<double>(run_rtp * 100.0L) << "%)" << std::endl;
    }

    const long double mean = sum_x / static_cast<long double>(total_hands);
    long double variance = (sum_x2 / static_cast<long double>(total_hands)) - (mean * mean);
    if (variance < 0.0L) {
        variance = 0.0L;
    }
    const long double se = std::sqrt(variance / static_cast<long double>(total_hands));
    const long double margin = 1.96L * se;
    const long double ci_lo = mean - margin;
    const long double ci_hi = mean + margin;

    std::cout << "\nHands: " << total_hands
              << "  Bet: " << bet
              << "  Engine: " << engine
              << "  Seed base: " << base_seed << std::endl;
    std::cout << "Estimated RTP: " << std::fixed << std::setprecision(6)
              << static_cast<double>(mean) << " (" << static_cast<double>(mean * 100.0L) << "%)" << std::endl;
    std::cout << "95% CI: [" << static_cast<double>(ci_lo) << ", " << static_cast<double>(ci_hi)
              << "]  => [" << static_cast<double>(ci_lo * 100.0L) << "%, " << static_cast<double>(ci_hi * 100.0L) << "%]" << std::endl;
    std::cout << "Target RTP: " << std::fixed << std::setprecision(6)
              << target_rtp << " (" << (target_rtp * 100.0) << "%)" << std::endl;
    std::cout << "Delta (estimate - target): " << std::showpos << std::setprecision(6)
              << static_cast<double>(mean - target_rtp) << std::noshowpos << std::endl;

    return 0;
}
