#include "cli_hold_policy.h"

#include "autohold.h"
#include "card.h"

#include <algorithm>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <locale>
#include <utility>

namespace {
constexpr size_t kFeatures = 103;
constexpr size_t kPairFeatures = 3 * kFeatures + 2;
constexpr size_t network_parameters(size_t input, size_t hidden2) {
    return 64 * (input + 1) + hidden2 * 65 + hidden2 + 1;
}

bool consume(std::istream& in, char expected) {
    char actual;
    return (in >> actual) && actual == expected;
}

bool string_value(std::istream& in, std::string& value) {
    return (in >> std::ws).peek() == '"' && bool(in >> std::quoted(value));
}

bool weights(std::istream& in, size_t count, std::vector<float>& values) {
    if (!consume(in, '[')) return false;
    values.resize(count);
    for (size_t i = 0; i < count; ++i) {
        if ((i && !consume(in, ',')) || !(in >> values[i]) || !std::isfinite(values[i])) return false;
    }
    return consume(in, ']');
}

using Features = std::array<float, kFeatures>;
using Counts = std::array<unsigned, 13>;
constexpr unsigned kWheel = (1u << 12) | 15u;
constexpr unsigned kRoyal = 31u << 8;
constexpr std::array<unsigned, 10> kStraights = {kWheel, 31u, 31u << 1, 31u << 2, 31u << 3,
    31u << 4, 31u << 5, 31u << 6, 31u << 7, kRoyal};

unsigned bit_count(unsigned mask) {
    unsigned count = 0;
    for (; mask; mask &= mask - 1) ++count;
    return count;
}

struct Deal {
    std::array<unsigned, 5> ranks{}, suits{}, order{0, 1, 2, 3, 4};
    Counts ranks_total{};
    std::array<unsigned, 4> suits_total{};
    std::array<unsigned, 4> suit_bits{};
    unsigned rank_bits = 0;
    bool straight = false;
    bool high_card = false;

    explicit Deal(const std::array<Card*, 5>& cards) {
        for (const auto* card : cards) suit_bits[card->suit() - SPADES] |= 1u << (card->rank() - TWO);
        // Equivalent to sorting by (rank, canonical suit). Equal suit bitsets
        // use the original suit order, as in the research encoder.
        std::sort(order.begin(), order.end(), [&](unsigned a, unsigned b) {
            if (cards[a]->rank() != cards[b]->rank()) return cards[a]->rank() < cards[b]->rank();
            const auto sa = cards[a]->suit() - SPADES, sb = cards[b]->suit() - SPADES;
            return suit_bits[sa] != suit_bits[sb] ? suit_bits[sa] < suit_bits[sb] : sa < sb;
        });
        for (unsigned i = 0; i < 5; ++i) {
            ranks[i] = cards[order[i]]->rank() - TWO;
            suits[i] = cards[order[i]]->suit() - SPADES;
            ++ranks_total[ranks[i]];
            ++suits_total[suits[i]];
            rank_bits |= 1u << ranks[i];
        }
        straight = std::find(kStraights.begin(), kStraights.end(), rank_bits) != kStraights.end();
        high_card = bit_count(rank_bits) == 5 && !straight && *std::max_element(suits_total.begin(), suits_total.end()) != 5;
    }

    Features encode(unsigned mask) const {
        Counts held{}, dead{};
        std::array<unsigned, 4> suit_counts{}, suit_held{};
        unsigned kept_bits = 0;
        for (unsigned i = 0; i < 5; ++i) {
            if (!(mask & (1u << i))) continue;
            const unsigned bit = 1u << ranks[i];
            ++held[ranks[i]];
            ++suit_counts[suits[i]];
            suit_held[suits[i]] |= bit;
            kept_bits |= bit;
        }
        Features out{};
        size_t pos = 0;
        for (unsigned n : held) out[pos++] = n;
        for (size_t i = 0; i < held.size(); ++i) out[pos++] = dead[i] = ranks_total[i] - held[i];

        const unsigned count = bit_count(mask), distinct = bit_count(kept_bits);
        unsigned max_window = 0, royal_window = 0, missing = 0;
        for (unsigned window : kStraights) {
            const unsigned overlap = bit_count(kept_bits & window);
            out[pos++] = overlap;
            if (window == kRoyal) royal_window = overlap;
            else max_window = std::max(max_window, overlap);
            if (count == distinct && distinct >= 3 && distinct <= 4 && overlap == distinct) missing |= window & ~kept_bits;
        }
        for (unsigned window : kStraights) {
            unsigned dead_in_window = 0;
            for (unsigned i = 0; i < dead.size(); ++i) if (window & (1u << i)) dead_in_window += dead[i];
            out[pos++] = dead_in_window;
        }

        unsigned dominant = 0, signature = 0, used_suits = 0, dead_same_suit = 0;
        for (unsigned suit = 0; suit < 4; ++suit) {
            if (suit_counts[suit]) { ++used_suits; dead_same_suit += suits_total[suit] - suit_counts[suit]; }
            const unsigned next = (suit_counts[suit] << 26) | (suit_held[suit] << 13) | (suit_bits[suit] ^ suit_held[suit]);
            if (next > signature) { signature = next; dominant = suit; }
        }
        const unsigned suited_count = suit_counts[dominant];
        const unsigned held_suit = suit_held[dominant];
        const unsigned dead_suit = count ? suit_bits[dominant] ^ held_suit : 0;
        out[pos++] = count;
        out[pos++] = distinct;
        out[pos++] = suited_count;
        out[pos++] = dead_same_suit;
        for (unsigned n : {2u, 3u, 4u}) out[pos++] = std::count(held.begin(), held.end(), n);
        out[pos++] = std::count(held.begin() + 9, held.end(), 2u);
        out[pos++] = bit_count(kept_bits & kRoyal);
        out[pos++] = max_window;
        out[pos++] = royal_window;
        out[pos++] = suited_count == count;
        out[pos++] = used_suits;
        for (unsigned bits : {held_suit, dead_suit}) {
            for (unsigned i = 0; i < held.size(); ++i) out[pos++] = (bits >> i) & 1u;
        }
        unsigned straight_outs = 0;
        for (unsigned i = 0; i < dead.size(); ++i) {
            const bool is_missing = (missing >> i) & 1u;
            out[pos++] = is_missing ? dead[i] : 0;
            if (is_missing && count == 4) straight_outs += 4 - dead[i];
        }
        const bool suited_four = count == 4 && suited_count == 4;
        out[pos++] = straight_outs;
        out[pos++] = suited_four ? bit_count(missing & ~dead_suit) : 0;
        out[pos++] = suited_four && bit_count(held_suit & kRoyal) == 4 ? bit_count(kRoyal & ~(held_suit | dead_suit)) : 0;
        out[pos++] = straight;
        out[pos] = rank_bits == kWheel;
        return out;
    }
};

template<size_t Input, size_t Hidden>
float network(const std::array<float, Input>& features, const std::vector<float>& params) {
    std::array<float, 64> first;
    std::array<float, Hidden> second;
    const float* p = params.data();
    const auto layer = [&p](const auto& from, auto& to) {
        for (float& node : to) {
            float score = *p++;
            for (float feature : from) score += feature * *p++;
            node = std::max(0.0f, score);
        }
    };
    layer(features, first);
    layer(first, second);
    float score = *p++;
    for (float node : second) score += node * *p++;
    return score;
}
} // namespace

bool CliHoldPolicy::configure(const std::string& engine, const std::string& model_path,
                              GameVariant variant, uint32_t bet, std::string& error) {
    variant_ = variant;
    bet_ = bet;
    ranker_.clear();
    reranker_.clear();
    if (engine != "ml-rerank") {
        if (!AutoHold::set_engine(engine.c_str())) {
            error = "invalid engine: " + engine + " (expected solver|rule|ml|ml-rerank)";
        } else if (engine == "ml") {
            if (model_path.empty()) error = "engine ml requires --ml-model <path>";
            else if (!AutoHold::set_ml_model(model_path.c_str())) error = "failed to load ml model from: " + model_path;
            else return true;
        } else if (!model_path.empty()) {
            error = "--ml-model requires --engine ml or ml-rerank";
        } else {
            return true;
        }
        return false;
    }

    if (model_path.empty()) { error = "engine ml-rerank requires --ml-model <path>"; return false; }
    if (bet != 5) { error = "engine ml-rerank supports only a five-credit bet"; return false; }
    std::ifstream in(model_path);
    in.imbue(std::locale::classic());
    std::string format, model_variant;
    unsigned model_bet;
    float margin, gain;
    std::vector<float> ranker, reranker;
    if (!consume(in, '[') || !string_value(in, format) || format != "equilibrium-ml-rerank-v1" ||
        !consume(in, ',') || !string_value(in, model_variant) || !consume(in, ',') || !(in >> model_bet) || model_bet != 5 ||
        !consume(in, ',') || !(in >> margin) || !std::isfinite(margin) || margin < 0 ||
        !consume(in, ',') || !(in >> gain) || !std::isfinite(gain) || gain < 0 ||
        !consume(in, ',') || !weights(in, network_parameters(kFeatures, 64), ranker) ||
        !consume(in, ',') || !weights(in, network_parameters(kPairFeatures, 32), reranker) ||
        !consume(in, ']') || (in >> std::ws).peek() != std::char_traits<char>::eof()) {
        error = "invalid ml-rerank bundle: " + model_path;
        return false;
    }
    if (model_variant != game_variant_info(variant).id) {
        error = "ml-rerank bundle is for " + model_variant + ", not " + game_variant_info(variant).id;
        return false;
    }
    max_margin_ = margin;
    min_gain_ = gain;
    ranker_ = std::move(ranker);
    reranker_ = std::move(reranker);
    return true;
}

uint32_t CliHoldPolicy::hold(const std::array<Card*, 5>& cards) const {
    if (ranker_.empty()) return AutoHold::auto_hold(cards, bet_, variant_);
    const Deal deal(cards);
    std::array<Features, 32> features;
    std::array<float, 32> scores;
    unsigned first = 0, second = 0;
    for (unsigned mask = 0; mask < 32; ++mask) {
        features[mask] = deal.encode(mask);
        scores[mask] = network<kFeatures, 64>(features[mask], ranker_);
        // Strict comparisons preserve canonical mask order for tied scores.
        if (scores[mask] > scores[first]) { second = first; first = mask; }
        else if (mask != first && (first == second || scores[mask] > scores[second])) second = mask;
    }
    if (deal.high_card && scores[first] - scores[second] <= max_margin_) {
        std::array<float, kPairFeatures> pair;
        for (size_t i = 0; i < kFeatures; ++i) {
            pair[i] = features[first][i];
            pair[kFeatures + i] = features[second][i];
            pair[2 * kFeatures + i] = features[second][i] - features[first][i];
        }
        pair[3 * kFeatures] = scores[first];
        pair[3 * kFeatures + 1] = scores[second];
        if (network<kPairFeatures, 32>(pair, reranker_) > min_gain_) first = second;
    }
    uint32_t mask = 0;
    for (unsigned i = 0; i < 5; ++i) {
        const bool held = (first & (1u << i)) != 0;
        cards[deal.order[i]]->set_held(held);
        if (held) mask |= 1u << deal.order[i];
    }
    return mask;
}
