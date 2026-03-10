#include "autohold.h"
#include "card.h"
#include "checkforwin.h"
#include "hand.h"

#include <algorithm>
#include <array>
#include <cctype>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iostream>
#include <sstream>
#include <unordered_map>
#include <utility>
#include <vector>

namespace {
bool g_autohold_verbose = true;
AutoHold::Engine g_engine = AutoHold::Engine::SOLVER;
bool g_ml_model_loaded = false;
uint32_t g_ml_input_size = 0;
uint32_t g_ml_hidden_size = 0;
uint32_t g_ml_output_size = 0;
std::vector<float> g_ml_w1;
std::vector<float> g_ml_b1;
std::vector<float> g_ml_w2;
std::vector<float> g_ml_b2;
const char* kRuleStrategyTable[] = {
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
    "Hold Nothing"
};

struct LiteCard {
    uint8_t suit;
    uint8_t rank;
};

std::array<LiteCard, 52> make_full_deck() {
    std::array<LiteCard, 52> deck = {};
    uint32_t idx = 0;
    for (uint32_t suit = SPADES; suit <= DIAMONDS; suit++) {
        for (uint32_t rank = TWO; rank <= ACE; rank++) {
            deck[idx++] = {static_cast<uint8_t>(suit), static_cast<uint8_t>(rank)};
        }
    }
    return deck;
}

const std::array<LiteCard, 52> kFullDeck = make_full_deck();

bool parse_json_uint_field(const std::string& text, const char* key, uint32_t& value) {
    const std::string needle = std::string("\"") + key + "\"";
    size_t pos = text.find(needle);
    if (pos == std::string::npos) {
        return false;
    }
    pos = text.find(':', pos);
    if (pos == std::string::npos) {
        return false;
    }
    pos++;
    while (pos < text.size() && std::isspace(static_cast<unsigned char>(text[pos]))) {
        pos++;
    }
    size_t end = pos;
    while (end < text.size() && std::isdigit(static_cast<unsigned char>(text[end]))) {
        end++;
    }
    if (end == pos) {
        return false;
    }
    value = static_cast<uint32_t>(std::strtoul(text.substr(pos, end - pos).c_str(), nullptr, 10));
    return true;
}

bool parse_json_float_array_field(const std::string& text, const char* key, std::vector<float>& out_values) {
    out_values.clear();
    const std::string needle = std::string("\"") + key + "\"";
    size_t pos = text.find(needle);
    if (pos == std::string::npos) {
        return false;
    }
    pos = text.find('[', pos);
    if (pos == std::string::npos) {
        return false;
    }

    int depth = 0;
    std::string token;
    for (size_t i = pos; i < text.size(); i++) {
        const char ch = text[i];
        if (ch == '[') {
            depth++;
            continue;
        }
        if (ch == ']') {
            if (!token.empty()) {
                out_values.push_back(std::strtof(token.c_str(), nullptr));
                token.clear();
            }
            depth--;
            if (depth == 0) {
                break;
            }
            continue;
        }
        if (depth <= 0) {
            break;
        }
        if ((ch >= '0' && ch <= '9') || ch == '-' || ch == '+' || ch == '.' || ch == 'e' || ch == 'E') {
            token.push_back(ch);
        } else if (!token.empty()) {
            out_values.push_back(std::strtof(token.c_str(), nullptr));
            token.clear();
        }
    }

    return !out_values.empty();
}

uint64_t hand_cache_key(const std::array<Card*, 5>& cards, uint32_t bet) {
    std::array<uint8_t, 5> ids = {0, 0, 0, 0, 0};
    for (uint8_t i = 0; i < 5; i++) {
        // 0..51 canonical card id
        ids[i] = static_cast<uint8_t>((cards[i]->suit() - SPADES) * 13 + (cards[i]->rank() - TWO));
    }
    std::sort(ids.begin(), ids.end());

    uint64_t key = static_cast<uint64_t>(bet) << 40;
    for (uint8_t i = 0; i < 5; i++) {
        key |= static_cast<uint64_t>(ids[i]) << (i * 6);
    }
    return key;
}

uint32_t payout_for_cards(const std::array<LiteCard, 5>& cards, uint32_t bet) {
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
    
    // Straight check: 5 consecutive bits, or the Ace-low wheel (A,2,3,4,5)
    // ACE is 14, so mask for wheel is (1<<14 | 1<<2 | 1<<3 | 1<<4 | 1<<5) = 0x403C
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

    // Use rank_counts to find pairs, trips, quads
    // Each 4-bit nibble in rank_counts stores the count of that rank
    uint32_t quads = 0;
    uint32_t trips = 0;
    uint32_t pairs = 0;
    uint32_t high_pairs = 0;

    uint64_t temp_counts = rank_counts;
    for (uint32_t r = 2; r <= 14; r++) {
        uint32_t c = (temp_counts >> (r * 4)) & 0xF;
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

void evaluate_mask_ev(
    const std::vector<LiteCard>& remaining,
    const std::array<uint8_t, 5>& discard_slots,
    uint8_t discard_count,
    const std::array<LiteCard, 5>& base_cards,
    uint32_t bet,
    uint64_t& total_payout,
    uint32_t& ways
) {
    total_payout = 0;
    ways = 0;

    if (discard_count == 0) {
        total_payout = payout_for_cards(base_cards, bet);
        ways = 1;
        return;
    }

    std::array<LiteCard, 5> final_cards = base_cards;
    const uint32_t n = static_cast<uint32_t>(remaining.size());

    switch (discard_count) {
        case 1: {
            for (uint32_t i = 0; i < n; i++) {
                final_cards[discard_slots[0]] = remaining[i];
                total_payout += payout_for_cards(final_cards, bet);
            }
            ways = n;
            return;
        }
        case 2: {
            for (uint32_t i = 0; i + 1 < n; i++) {
                final_cards[discard_slots[0]] = remaining[i];
                for (uint32_t j = i + 1; j < n; j++) {
                    final_cards[discard_slots[1]] = remaining[j];
                    total_payout += payout_for_cards(final_cards, bet);
                    ways++;
                }
            }
            return;
        }
        case 3: {
            for (uint32_t i = 0; i + 2 < n; i++) {
                final_cards[discard_slots[0]] = remaining[i];
                for (uint32_t j = i + 1; j < n; j++) {
                    final_cards[discard_slots[1]] = remaining[j];
                    for (uint32_t k = j + 1; k < n; k++) {
                        final_cards[discard_slots[2]] = remaining[k];
                        total_payout += payout_for_cards(final_cards, bet);
                        ways++;
                    }
                }
            }
            return;
        }
        case 4: {
            for (uint32_t i = 0; i + 3 < n; i++) {
                final_cards[discard_slots[0]] = remaining[i];
                for (uint32_t j = i + 1; j < n; j++) {
                    final_cards[discard_slots[1]] = remaining[j];
                    for (uint32_t k = j + 1; k < n; k++) {
                        final_cards[discard_slots[2]] = remaining[k];
                        for (uint32_t m = k + 1; m < n; m++) {
                            final_cards[discard_slots[3]] = remaining[m];
                            total_payout += payout_for_cards(final_cards, bet);
                            ways++;
                        }
                    }
                }
            }
            return;
        }
        case 5: {
            for (uint32_t i = 0; i + 4 < n; i++) {
                final_cards[discard_slots[0]] = remaining[i];
                for (uint32_t j = i + 1; j < n; j++) {
                    final_cards[discard_slots[1]] = remaining[j];
                    for (uint32_t k = j + 1; k < n; k++) {
                        final_cards[discard_slots[2]] = remaining[k];
                        for (uint32_t m = k + 1; m < n; m++) {
                            final_cards[discard_slots[3]] = remaining[m];
                            for (uint32_t p = m + 1; p < n; p++) {
                                final_cards[discard_slots[4]] = remaining[p];
                                total_payout += payout_for_cards(final_cards, bet);
                                ways++;
                            }
                        }
                    }
                }
            }
            return;
        }
    }
}

void set_held_from_kept(const std::array<Card*, 5>& cards) {
    for (uint8_t i = 0; i < 5; i++) {
        cards[i]->set_held(cards[i]->is_kept());
    }
}

uint8_t held_count(uint8_t mask) {
    uint8_t n = 0;
    for (uint8_t i = 0; i < 5; i++) {
        if ((mask & (1u << i)) != 0) {
            n++;
        }
    }
    return n;
}

void apply_mask(const std::array<Card*, 5>& cards, uint8_t mask) {
    for (uint8_t i = 0; i < 5; i++) {
        cards[i]->set_held((mask & (1u << i)) != 0);
    }
}

uint32_t mask_rank_score(const std::array<Card*, 5>& cards, uint8_t mask) {
    uint32_t score = 0;
    for (uint8_t i = 0; i < 5; i++) {
        if ((mask & (1u << i)) != 0) {
            score += cards[i]->rank();
        }
    }
    return score;
}

bool mask_same_suit(const std::array<Card*, 5>& cards, uint8_t mask) {
    uint32_t suit = 0;
    bool have = false;
    for (uint8_t i = 0; i < 5; i++) {
        if ((mask & (1u << i)) == 0) {
            continue;
        }
        if (!have) {
            suit = cards[i]->suit();
            have = true;
        } else if (cards[i]->suit() != suit) {
            return false;
        }
    }
    return have;
}

bool is_straight_ranks(std::vector<uint32_t> ranks) {
    std::sort(ranks.begin(), ranks.end());
    bool straight = true;
    for (size_t i = 1; i < ranks.size(); i++) {
        if (ranks[i - 1] + 1 != ranks[i]) {
            straight = false;
            break;
        }
    }
    if (straight) {
        return true;
    }
    return ranks.size() == 5 &&
           ranks[0] == TWO &&
           ranks[1] == THREE &&
           ranks[2] == FOUR &&
           ranks[3] == FIVE &&
           ranks[4] == ACE;
}

std::vector<uint32_t> mask_ranks(const std::array<Card*, 5>& cards, uint8_t mask) {
    std::vector<uint32_t> ranks;
    ranks.reserve(5);
    for (uint8_t i = 0; i < 5; i++) {
        if ((mask & (1u << i)) != 0) {
            ranks.push_back(cards[i]->rank());
        }
    }
    return ranks;
}

bool mask_is_n_to_royal(const std::array<Card*, 5>& cards, uint8_t mask, uint8_t n) {
    if (held_count(mask) != n || !mask_same_suit(cards, mask)) {
        return false;
    }
    for (uint8_t i = 0; i < 5; i++) {
        if ((mask & (1u << i)) == 0) {
            continue;
        }
        const uint32_t r = cards[i]->rank();
        if (!(r == TEN || r == JACK || r == QUEEN || r == KING || r == ACE)) {
            return false;
        }
    }
    return true;
}

bool mask_is_n_to_flush(const std::array<Card*, 5>& cards, uint8_t mask, uint8_t n) {
    return held_count(mask) == n && mask_same_suit(cards, mask);
}

bool mask_is_low_pair(const std::array<Card*, 5>& cards, uint8_t mask) {
    if (held_count(mask) != 2) {
        return false;
    }
    std::vector<uint32_t> ranks = mask_ranks(cards, mask);
    return ranks[0] == ranks[1] && ranks[0] < JACK;
}

bool mask_is_4_to_outside_straight(const std::array<Card*, 5>& cards, uint8_t mask) {
    if (held_count(mask) != 4) {
        return false;
    }
    std::vector<uint32_t> ranks = mask_ranks(cards, mask);
    std::sort(ranks.begin(), ranks.end());
    if (std::unique(ranks.begin(), ranks.end()) != ranks.end()) {
        return false;
    }
    return ranks[3] - ranks[0] == 3 && is_straight_ranks(ranks);
}

bool mask_is_4_to_inside_straight(const std::array<Card*, 5>& cards, uint8_t mask) {
    if (held_count(mask) != 4) {
        return false;
    }
    std::vector<uint32_t> ranks = mask_ranks(cards, mask);
    std::sort(ranks.begin(), ranks.end());
    if (std::unique(ranks.begin(), ranks.end()) != ranks.end()) {
        return false;
    }

    // Wheel [A,2,3,4,5]
    {
        std::vector<uint32_t> straight = {ACE, TWO, THREE, FOUR, FIVE};
        uint32_t matched = 0;
        uint32_t missing = 0;
        for (uint32_t r : straight) {
            if (std::find(ranks.begin(), ranks.end(), r) != ranks.end()) {
                matched++;
            } else {
                missing = r;
            }
        }
        if (matched == 4 && missing != ACE && missing != FIVE) {
            return true;
        }
    }

    for (uint32_t start = TWO; start <= TEN; start++) {
        std::vector<uint32_t> straight = {start, start + 1, start + 2, start + 3, start + 4};
        uint32_t matched = 0;
        uint32_t missing = 0;
        for (uint32_t r : straight) {
            if (std::find(ranks.begin(), ranks.end(), r) != ranks.end()) {
                matched++;
            } else {
                missing = r;
            }
        }
        if (matched == 4 && missing != start && missing != start + 4) {
            return true;
        }
    }

    return false;
}

bool mask_is_4_to_straight_flush(const std::array<Card*, 5>& cards, uint8_t mask) {
    if (held_count(mask) != 4 || !mask_same_suit(cards, mask)) {
        return false;
    }
    std::vector<uint32_t> ranks = mask_ranks(cards, mask);
    std::sort(ranks.begin(), ranks.end());
    if (std::unique(ranks.begin(), ranks.end()) != ranks.end()) {
        return false;
    }
    for (uint32_t r = TWO; r <= ACE; r++) {
        if (std::find(ranks.begin(), ranks.end(), r) != ranks.end()) {
            continue;
        }
        std::vector<uint32_t> test = ranks;
        test.push_back(r);
        if (is_straight_ranks(test)) {
            return true;
        }
    }
    return false;
}

bool mask_is_3_to_straight_flush_tuned(const std::array<Card*, 5>& cards, uint8_t mask, uint8_t min_high, uint8_t max_gaps) {
    if (held_count(mask) != 3 || !mask_same_suit(cards, mask)) {
        return false;
    }
    std::vector<uint32_t> ranks = mask_ranks(cards, mask);
    std::sort(ranks.begin(), ranks.end());
    if (std::unique(ranks.begin(), ranks.end()) != ranks.end()) {
        return false;
    }

    uint8_t high_count = 0;
    for (uint32_t r : ranks) {
        if (r >= JACK) {
            high_count++;
        }
    }
    if (high_count < min_high) {
        return false;
    }

    int gaps = static_cast<int>(ranks[2] - ranks[0]) - 2;
    if (gaps < 0 || gaps > static_cast<int>(max_gaps)) {
        return false;
    }

    for (uint32_t a = TWO; a <= ACE; a++) {
        if (std::find(ranks.begin(), ranks.end(), a) != ranks.end()) {
            continue;
        }
        for (uint32_t b = a + 1; b <= ACE; b++) {
            if (std::find(ranks.begin(), ranks.end(), b) != ranks.end()) {
                continue;
            }
            std::vector<uint32_t> test = ranks;
            test.push_back(a);
            test.push_back(b);
            if (is_straight_ranks(test)) {
                return true;
            }
        }
    }
    return false;
}

bool mask_is_2_suited_high(const std::array<Card*, 5>& cards, uint8_t mask) {
    if (held_count(mask) != 2 || !mask_same_suit(cards, mask)) {
        return false;
    }
    for (uint8_t i = 0; i < 5; i++) {
        if ((mask & (1u << i)) == 0) {
            continue;
        }
        if (cards[i]->rank() < JACK) {
            return false;
        }
    }
    return true;
}

bool mask_is_2_unsuited_high(const std::array<Card*, 5>& cards, uint8_t mask) {
    if (held_count(mask) != 2) {
        return false;
    }
    uint32_t suit = 0;
    bool have = false;
    for (uint8_t i = 0; i < 5; i++) {
        if ((mask & (1u << i)) == 0) {
            continue;
        }
        if (cards[i]->rank() < JACK) {
            return false;
        }
        if (!have) {
            suit = cards[i]->suit();
            have = true;
        } else if (cards[i]->suit() == suit) {
            return false;
        }
    }
    return true;
}

bool mask_is_1_high(const std::array<Card*, 5>& cards, uint8_t mask) {
    if (held_count(mask) != 1) {
        return false;
    }
    for (uint8_t i = 0; i < 5; i++) {
        if ((mask & (1u << i)) != 0) {
            return cards[i]->rank() >= JACK;
        }
    }
    return false;
}

bool mask_is_1_rank(const std::array<Card*, 5>& cards, uint8_t mask, uint32_t rank) {
    if (held_count(mask) != 1) {
        return false;
    }
    for (uint8_t i = 0; i < 5; i++) {
        if ((mask & (1u << i)) != 0) {
            return cards[i]->rank() == rank;
        }
    }
    return false;
}

bool mask_is_specific_pair(const std::array<Card*, 5>& cards, uint8_t mask, uint32_t a, uint32_t b, bool suited) {
    if (held_count(mask) != 2) {
        return false;
    }
    int idx_a = -1;
    int idx_b = -1;
    for (uint8_t i = 0; i < 5; i++) {
        if ((mask & (1u << i)) != 0) {
            if (idx_a < 0) {
                idx_a = i;
            } else {
                idx_b = i;
            }
        }
    }
    if (idx_a < 0 || idx_b < 0) {
        return false;
    }
    const uint32_t r1 = cards[idx_a]->rank();
    const uint32_t r2 = cards[idx_b]->rank();
    if (!((r1 == a && r2 == b) || (r1 == b && r2 == a))) {
        return false;
    }
    const bool same_suit = cards[idx_a]->suit() == cards[idx_b]->suit();
    return suited ? same_suit : !same_suit;
}

bool mask_is_inside_with_3_high(const std::array<Card*, 5>& cards, uint8_t mask) {
    if (!mask_is_4_to_inside_straight(cards, mask)) {
        return false;
    }
    uint8_t high_count = 0;
    for (uint8_t i = 0; i < 5; i++) {
        if ((mask & (1u << i)) != 0 && cards[i]->rank() >= JACK) {
            high_count++;
        }
    }
    return high_count >= 3;
}

bool select_best_mask(
    const std::array<Card*, 5>& cards,
    bool (*predicate)(const std::array<Card*, 5>&, uint8_t),
    uint8_t& selected_mask
) {
    bool found = false;
    uint32_t best_score = 0;

    for (uint8_t mask = 1; mask < 32; mask++) {
        if (!predicate(cards, mask)) {
            continue;
        }
        const uint32_t score = mask_rank_score(cards, mask);
        if (!found || score > best_score) {
            best_score = score;
            selected_mask = mask;
            found = true;
        }
    }

    return found;
}

bool pred_4_to_royal(const std::array<Card*, 5>& cards, uint8_t mask) { return mask_is_n_to_royal(cards, mask, 4); }
bool pred_4_to_flush(const std::array<Card*, 5>& cards, uint8_t mask) { return mask_is_n_to_flush(cards, mask, 4); }
bool pred_3_to_royal(const std::array<Card*, 5>& cards, uint8_t mask) { return mask_is_n_to_royal(cards, mask, 3); }
bool pred_3_to_sf_strong(const std::array<Card*, 5>& cards, uint8_t mask) { return mask_is_3_to_straight_flush_tuned(cards, mask, 2, 1); }
bool pred_3_to_sf_medium(const std::array<Card*, 5>& cards, uint8_t mask) { return mask_is_3_to_straight_flush_tuned(cards, mask, 1, 2); }
bool pred_suited_tj(const std::array<Card*, 5>& cards, uint8_t mask) { return mask_is_specific_pair(cards, mask, TEN, JACK, true); }
bool pred_suited_qj(const std::array<Card*, 5>& cards, uint8_t mask) { return mask_is_specific_pair(cards, mask, QUEEN, JACK, true); }
bool pred_suited_kq(const std::array<Card*, 5>& cards, uint8_t mask) { return mask_is_specific_pair(cards, mask, KING, QUEEN, true); }
bool pred_suited_jk(const std::array<Card*, 5>& cards, uint8_t mask) { return mask_is_specific_pair(cards, mask, JACK, KING, true); }
bool pred_suited_ak_aq_aj(const std::array<Card*, 5>& cards, uint8_t mask) {
    return mask_is_specific_pair(cards, mask, ACE, KING, true) ||
           mask_is_specific_pair(cards, mask, ACE, QUEEN, true) ||
           mask_is_specific_pair(cards, mask, ACE, JACK, true);
}
bool pred_unsuited_tj(const std::array<Card*, 5>& cards, uint8_t mask) { return mask_is_specific_pair(cards, mask, TEN, JACK, false); }
bool pred_unsuited_qj(const std::array<Card*, 5>& cards, uint8_t mask) { return mask_is_specific_pair(cards, mask, QUEEN, JACK, false); }
bool pred_unsuited_kq(const std::array<Card*, 5>& cards, uint8_t mask) { return mask_is_specific_pair(cards, mask, KING, QUEEN, false); }
bool pred_unsuited_jk(const std::array<Card*, 5>& cards, uint8_t mask) { return mask_is_specific_pair(cards, mask, JACK, KING, false); }
bool pred_suited_at(const std::array<Card*, 5>& cards, uint8_t mask) { return mask_is_specific_pair(cards, mask, ACE, TEN, true); }
bool pred_suited_kt(const std::array<Card*, 5>& cards, uint8_t mask) { return mask_is_specific_pair(cards, mask, KING, TEN, true); }
bool pred_suited_qt(const std::array<Card*, 5>& cards, uint8_t mask) { return mask_is_specific_pair(cards, mask, QUEEN, TEN, true); }
bool pred_inside_3_high(const std::array<Card*, 5>& cards, uint8_t mask) { return mask_is_inside_with_3_high(cards, mask); }
bool pred_one_ace(const std::array<Card*, 5>& cards, uint8_t mask) { return mask_is_1_rank(cards, mask, ACE); }
bool pred_one_king(const std::array<Card*, 5>& cards, uint8_t mask) { return mask_is_1_rank(cards, mask, KING); }
bool pred_one_queen(const std::array<Card*, 5>& cards, uint8_t mask) { return mask_is_1_rank(cards, mask, QUEEN); }
bool pred_one_jack(const std::array<Card*, 5>& cards, uint8_t mask) { return mask_is_1_rank(cards, mask, JACK); }
bool pred_one_ten(const std::array<Card*, 5>& cards, uint8_t mask) { return mask_is_1_rank(cards, mask, TEN); }

uint32_t rule_auto_hold(const std::array<Card*, 5>& cards) {
    for (uint8_t i = 0; i < 5; i++) {
        cards[i]->reset();
    }

    uint8_t mask = 0;
    const uint32_t win = CheckForWin::check_for_win(cards);
    if (win != NONE) {
        for (uint8_t i = 0; i < 5; i++) {
            if (cards[i]->is_kept()) mask |= (1u << i);
        }
    } else {
        if (select_best_mask(cards, pred_4_to_royal, mask)) {}
        else if (select_best_mask(cards, mask_is_4_to_straight_flush, mask)) {}
        else if (select_best_mask(cards, pred_3_to_royal, mask)) {}
        else if (select_best_mask(cards, pred_4_to_flush, mask)) {}
        else if (select_best_mask(cards, mask_is_low_pair, mask)) {}
        else if (select_best_mask(cards, mask_is_4_to_outside_straight, mask)) {}
        else if (select_best_mask(cards, mask_is_2_suited_high, mask)) {}
        else if (select_best_mask(cards, pred_3_to_sf_strong, mask)) {}
        else if (select_best_mask(cards, mask_is_2_unsuited_high, mask)) {}
        else if (select_best_mask(cards, pred_suited_tj, mask)) {}
        else if (select_best_mask(cards, pred_suited_qj, mask)) {}
        else if (select_best_mask(cards, pred_suited_kq, mask)) {}
        else if (select_best_mask(cards, pred_suited_jk, mask)) {}
        else if (select_best_mask(cards, pred_suited_ak_aq_aj, mask)) {}
        else if (select_best_mask(cards, pred_unsuited_tj, mask)) {}
        else if (select_best_mask(cards, pred_unsuited_qj, mask)) {}
        else if (select_best_mask(cards, pred_unsuited_kq, mask)) {}
        else if (select_best_mask(cards, pred_unsuited_jk, mask)) {}
        else if (select_best_mask(cards, pred_suited_at, mask)) {}
        else if (select_best_mask(cards, pred_suited_kt, mask)) {}
        else if (select_best_mask(cards, pred_suited_qt, mask)) {}
        else if (select_best_mask(cards, pred_3_to_sf_medium, mask)) {}
        else if (select_best_mask(cards, pred_inside_3_high, mask)) {}
        else if (select_best_mask(cards, pred_one_ace, mask)) {}
        else if (select_best_mask(cards, pred_one_king, mask)) {}
        else if (select_best_mask(cards, pred_one_queen, mask)) {}
        else if (select_best_mask(cards, pred_one_jack, mask)) {}
        else if (select_best_mask(cards, pred_one_ten, mask)) {}
        else { mask = 0; }
    }

    apply_mask(cards, mask);
    if (g_autohold_verbose) {
        std::cout << "Hold rule-based" << std::endl;
    }
    return mask;
}

uint32_t solver_auto_hold(const std::array<Card*, 5>& cards, uint32_t bet, double* out_ev) {
    thread_local std::unordered_map<uint64_t, uint8_t> best_mask_cache;
    thread_local std::unordered_map<uint64_t, double> ev_cache;

    const uint64_t cache_key = hand_cache_key(cards, bet);

    for (uint32_t i = 0; i < 5; i++) {
        cards[i]->reset();
    }

    if (best_mask_cache.count(cache_key)) {
        const uint8_t mask = best_mask_cache[cache_key];
        apply_mask(cards, mask);
        if (out_ev) *out_ev = ev_cache[cache_key];
        if (g_autohold_verbose) std::cout << "Hold exact EV-optimal" << std::endl;
        return mask;
    }

    bool in_hand_flags[52] = {false};
    for (uint32_t i = 0; i < 5; i++) {
        const uint32_t deck_idx = (cards[i]->suit() - SPADES) * 13 + (cards[i]->rank() - TWO);
        in_hand_flags[deck_idx] = true;
    }

    std::vector<LiteCard> remaining;
    remaining.reserve(47);
    for (uint32_t idx = 0; idx < 52; idx++) {
        if (!in_hand_flags[idx]) {
            remaining.push_back(kFullDeck[idx]);
        }
    }

    uint32_t best_mask = 0;
    uint64_t best_total_payout = 0;
    uint32_t best_ways = 1;
    bool have_best = false;

    for (uint32_t mask = 0; mask < 32; mask++) {
        std::array<LiteCard, 5> base_cards;
        std::array<uint8_t, 5> discard_slots = {0, 0, 0, 0, 0};
        uint8_t discard_count = 0;

        for (uint8_t i = 0; i < 5; i++) {
            base_cards[i] = {static_cast<uint8_t>(cards[i]->suit()), static_cast<uint8_t>(cards[i]->rank())};
            if ((mask & (1u << i)) == 0) discard_slots[discard_count++] = i;
        }

        uint64_t total_payout = 0;
        uint32_t ways = 0;
        evaluate_mask_ev(remaining, discard_slots, discard_count, base_cards, bet, total_payout, ways);

        if (!have_best) {
            best_mask = mask;
            best_total_payout = total_payout;
            best_ways = ways;
            have_best = true;
            continue;
        }

        __uint128_t lhs = static_cast<__uint128_t>(total_payout) * best_ways;
        __uint128_t rhs = static_cast<__uint128_t>(best_total_payout) * ways;
        if (lhs > rhs) {
            best_mask = mask;
            best_total_payout = total_payout;
            best_ways = ways;
        }
    }

    double ev = static_cast<double>(best_total_payout) / static_cast<double>(best_ways);
    if (out_ev) *out_ev = ev;

    apply_mask(cards, best_mask);
    best_mask_cache[cache_key] = static_cast<uint8_t>(best_mask);
    ev_cache[cache_key] = ev;

    if (g_autohold_verbose) {
        std::cout << "Hold exact EV-optimal" << std::endl;
    }

    return best_mask;
}

uint32_t ml_auto_hold(const std::array<Card*, 5>& cards, uint32_t bet) {
    if (!g_ml_model_loaded) {
        if (g_autohold_verbose) std::cout << "ML model not loaded; hold nothing" << std::endl;
        apply_mask(cards, 0);
        return 0;
    }

    std::vector<float> x(g_ml_input_size, 0.0f);
    for (uint32_t pos = 0; pos < 5; pos++) {
        const uint32_t card_id = (cards[pos]->suit() - SPADES) * 13 + (cards[pos]->rank() - TWO);
        const uint32_t feature_idx = pos * 52 + card_id;
        if (feature_idx < x.size()) x[feature_idx] = 1.0f;
    }
    if (x.size() > 260) x[260] = static_cast<float>(bet) / 5.0f;

    std::vector<float> hidden(g_ml_hidden_size, 0.0f);
    for (uint32_t j = 0; j < g_ml_hidden_size; j++) {
        float v = g_ml_b1[j];
        const size_t row_offset = static_cast<size_t>(j) * g_ml_input_size;
        for (uint32_t i = 0; i < g_ml_input_size; i++) v += x[i] * g_ml_w1[row_offset + i];
        hidden[j] = (v > 0.0f) ? v : 0.0f;
    }

    uint32_t best_mask = 0;
    float best_logit = 0.0f;
    bool have_best = false;
    for (uint32_t k = 0; k < g_ml_output_size; k++) {
        float v = g_ml_b2[k];
        const size_t row_offset = static_cast<size_t>(k) * g_ml_hidden_size;
        for (uint32_t j = 0; j < g_ml_hidden_size; j++) v += hidden[j] * g_ml_w2[row_offset + j];
        if (!have_best || v > best_logit) {
            best_logit = v;
            best_mask = k;
            have_best = true;
        }
    }

    if (best_mask > 31) best_mask = 31;
    apply_mask(cards, static_cast<uint8_t>(best_mask));

    if (g_autohold_verbose) std::cout << "Hold ml-model" << std::endl;
    return best_mask;
}
} // namespace

void AutoHold::set_verbose(bool verbose) {
    g_autohold_verbose = verbose;
}

bool AutoHold::set_engine(const char* engine_name) {
    if (engine_name == nullptr) return false;
    if (std::strcmp(engine_name, "solver") == 0) { g_engine = Engine::SOLVER; return true; }
    if (std::strcmp(engine_name, "rule") == 0) { g_engine = Engine::RULE; return true; }
    if (std::strcmp(engine_name, "ml") == 0) { g_engine = Engine::ML; return true; }
    return false;
}

bool AutoHold::set_ml_model(const char* model_path) {
    if (model_path == nullptr) return false;
    std::ifstream in(model_path);
    if (!in) return false;
    std::stringstream buffer;
    buffer << in.rdbuf();
    const std::string text = buffer.str();

    uint32_t input_size = 0, hidden_size = 0, output_size = 0;
    std::vector<float> w1, b1, w2, b2;

    if (!parse_json_uint_field(text, "input_size", input_size) ||
        !parse_json_uint_field(text, "hidden_size", hidden_size) ||
        !parse_json_uint_field(text, "output_size", output_size) ||
        !parse_json_float_array_field(text, "W1", w1) ||
        !parse_json_float_array_field(text, "b1", b1) ||
        !parse_json_float_array_field(text, "W2", w2) ||
        !parse_json_float_array_field(text, "b2", b2)) {
        return false;
    }

    if (w1.size() != static_cast<size_t>(hidden_size) * input_size ||
        b1.size() != hidden_size ||
        w2.size() != static_cast<size_t>(output_size) * hidden_size ||
        b2.size() != output_size) {
        return false;
    }

    g_ml_input_size = input_size;
    g_ml_hidden_size = hidden_size;
    g_ml_output_size = output_size;
    g_ml_w1 = std::move(w1);
    g_ml_b1 = std::move(b1);
    g_ml_w2 = std::move(w2);
    g_ml_b2 = std::move(b2);
    g_ml_model_loaded = true;
    return true;
}

AutoHold::Engine AutoHold::engine() {
    return g_engine;
}

void AutoHold::print_rule_strategy() {
    const uint32_t n = static_cast<uint32_t>(sizeof(kRuleStrategyTable) / sizeof(kRuleStrategyTable[0]));
    for (uint32_t i = 0; i < n; i++) std::cout << (i + 1) << ". " << kRuleStrategyTable[i] << std::endl;
}

uint32_t AutoHold::auto_hold(const std::array<Card*, 5>& cards, uint32_t bet, double* out_ev) {
    if (g_engine == Engine::RULE) {
        if (out_ev) *out_ev = 0.0; // Rule engine doesn't compute EV easily
        return rule_auto_hold(cards);
    } else if (g_engine == Engine::ML) {
        if (out_ev) *out_ev = 0.0; // ML engine doesn't compute EV easily
        return ml_auto_hold(cards, bet);
    }
    return solver_auto_hold(cards, bet, out_ev);
}
