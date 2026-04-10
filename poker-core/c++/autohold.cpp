#include "autohold.h"
#include "card.h"
#include "checkforwin.h"
#include "game_variant.h"
#include "hand.h"

#include <algorithm>
#include <array>
#include <cctype>
#include <cmath>
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
uint32_t g_ml_hidden1_size = 0;
uint32_t g_ml_hidden2_size = 0;
uint32_t g_ml_output_size = 0;
std::vector<float> g_ml_w1;
std::vector<float> g_ml_b1;
std::vector<float> g_ml_w2;
std::vector<float> g_ml_b2;
std::vector<float> g_ml_w3;
std::vector<float> g_ml_b3;
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

uint64_t hand_cache_key(const std::array<Card*, 5>& cards, uint32_t bet, GameVariant variant) {
    std::array<uint8_t, 5> ids = {0, 0, 0, 0, 0};
    for (uint8_t i = 0; i < 5; i++) {
        // 0..51 canonical card id
        ids[i] = static_cast<uint8_t>((cards[i]->suit() - SPADES) * 13 + (cards[i]->rank() - TWO));
    }
    std::sort(ids.begin(), ids.end());

    uint64_t key = (static_cast<uint64_t>(static_cast<uint32_t>(variant)) << 48) | (static_cast<uint64_t>(bet) << 40);
    for (uint8_t i = 0; i < 5; i++) {
        key |= static_cast<uint64_t>(ids[i]) << (i * 6);
    }
    return key;
}

uint32_t payout_for_cards(const std::array<LiteCard, 5>& cards, uint32_t bet, GameVariant variant) {
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
            return payout_for_result(ROYALFLUSH, bet, variant);
        }
        return payout_for_result(STRAIGHTFLUSH, bet, variant);
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

    if (quads) return payout_for_result(FOUROFAKIND, bet, variant);
    if (trips && pairs) return payout_for_result(FULLHOUSE, bet, variant);
    if (flush) return payout_for_result(FLUSH, bet, variant);
    if (straight) return payout_for_result(STRAIGHT, bet, variant);
    if (trips) return payout_for_result(THREEOFAKIND, bet, variant);
    if (pairs >= 2) return payout_for_result(TWOPAIR, bet, variant);
    if (high_pairs) return payout_for_result(HIGHPAIR, bet, variant);

    return 0;
}

void evaluate_mask_ev(
    const std::vector<LiteCard>& remaining,
    const std::array<uint8_t, 5>& discard_slots,
    uint8_t discard_count,
    const std::array<LiteCard, 5>& base_cards,
    uint32_t bet,
    GameVariant variant,
    uint64_t& total_payout,
    uint32_t& ways
) {
    total_payout = 0;
    ways = 0;

    if (discard_count == 0) {
        total_payout = payout_for_cards(base_cards, bet, variant);
        ways = 1;
        return;
    }

    std::array<LiteCard, 5> final_cards = base_cards;
    const uint32_t n = static_cast<uint32_t>(remaining.size());

    switch (discard_count) {
        case 1: {
            for (uint32_t i = 0; i < n; i++) {
                final_cards[discard_slots[0]] = remaining[i];
                total_payout += payout_for_cards(final_cards, bet, variant);
            }
            ways = n;
            return;
        }
        case 2: {
            for (uint32_t i = 0; i + 1 < n; i++) {
                final_cards[discard_slots[0]] = remaining[i];
                for (uint32_t j = i + 1; j < n; j++) {
                    final_cards[discard_slots[1]] = remaining[j];
                    total_payout += payout_for_cards(final_cards, bet, variant);
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
                        total_payout += payout_for_cards(final_cards, bet, variant);
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
                            total_payout += payout_for_cards(final_cards, bet, variant);
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
                                total_payout += payout_for_cards(final_cards, bet, variant);
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

std::vector<uint32_t> mask_ranks(const std::array<Card*, 5>& cards, uint8_t mask);
bool mask_is_4_to_straight_flush(const std::array<Card*, 5>& cards, uint8_t mask);
bool mask_is_low_pair(const std::array<Card*, 5>& cards, uint8_t mask);
bool mask_is_4_to_outside_straight(const std::array<Card*, 5>& cards, uint8_t mask);
bool mask_is_2_suited_high(const std::array<Card*, 5>& cards, uint8_t mask);
bool mask_is_2_unsuited_high(const std::array<Card*, 5>& cards, uint8_t mask);
bool select_best_mask(
    const std::array<Card*, 5>& cards,
    bool (*predicate)(const std::array<Card*, 5>&, uint8_t),
    uint8_t& selected_mask
);
bool pred_4_to_royal(const std::array<Card*, 5>& cards, uint8_t mask);
bool pred_3_to_royal(const std::array<Card*, 5>& cards, uint8_t mask);
bool pred_4_to_flush(const std::array<Card*, 5>& cards, uint8_t mask);
bool pred_3_to_sf_strong(const std::array<Card*, 5>& cards, uint8_t mask);
bool pred_suited_tj(const std::array<Card*, 5>& cards, uint8_t mask);
bool pred_suited_qj(const std::array<Card*, 5>& cards, uint8_t mask);
bool pred_suited_kq(const std::array<Card*, 5>& cards, uint8_t mask);
bool pred_suited_jk(const std::array<Card*, 5>& cards, uint8_t mask);
bool pred_suited_ak_aq_aj(const std::array<Card*, 5>& cards, uint8_t mask);
bool pred_unsuited_tj(const std::array<Card*, 5>& cards, uint8_t mask);
bool pred_unsuited_qj(const std::array<Card*, 5>& cards, uint8_t mask);
bool pred_unsuited_kq(const std::array<Card*, 5>& cards, uint8_t mask);
bool pred_unsuited_jk(const std::array<Card*, 5>& cards, uint8_t mask);
bool pred_suited_at(const std::array<Card*, 5>& cards, uint8_t mask);
bool pred_suited_kt(const std::array<Card*, 5>& cards, uint8_t mask);
bool pred_suited_qt(const std::array<Card*, 5>& cards, uint8_t mask);
bool pred_3_to_sf_medium(const std::array<Card*, 5>& cards, uint8_t mask);
bool pred_inside_3_high(const std::array<Card*, 5>& cards, uint8_t mask);
bool pred_one_ace(const std::array<Card*, 5>& cards, uint8_t mask);
bool pred_one_king(const std::array<Card*, 5>& cards, uint8_t mask);
bool pred_one_queen(const std::array<Card*, 5>& cards, uint8_t mask);
bool pred_one_jack(const std::array<Card*, 5>& cards, uint8_t mask);
bool pred_one_ten(const std::array<Card*, 5>& cards, uint8_t mask);

uint8_t kept_mask_from_win_eval(const std::array<Card*, 5>& cards, uint32_t* out_win_type = nullptr) {
    std::array<Card, 5> copies = {
        Card(cards[0]->suit(), cards[0]->rank()),
        Card(cards[1]->suit(), cards[1]->rank()),
        Card(cards[2]->suit(), cards[2]->rank()),
        Card(cards[3]->suit(), cards[3]->rank()),
        Card(cards[4]->suit(), cards[4]->rank())
    };
    std::array<Card*, 5> temp = {&copies[0], &copies[1], &copies[2], &copies[3], &copies[4]};
    const uint32_t win_type = CheckForWin::check_for_win(temp);
    if (out_win_type) {
        *out_win_type = win_type;
    }
    uint8_t mask = 0;
    for (uint8_t i = 0; i < 5; i++) {
        if (temp[i]->is_kept()) {
            mask |= (1u << i);
        }
    }
    return mask;
}

bool mask_is_high_pair(const std::array<Card*, 5>& cards, uint8_t mask) {
    if (held_count(mask) != 2) {
        return false;
    }
    std::vector<uint32_t> ranks = mask_ranks(cards, mask);
    return ranks[0] == ranks[1] && ranks[0] >= JACK;
}

const char* explanation_summary_for_label(const std::string& label) {
    if (label == "Pat royal flush") return "Keep all five cards because you already have the top-paying made hand.";
    if (label == "Pat straight flush") return "Keep all five cards because the hand is already a straight flush.";
    if (label == "Pat four of a kind") return "Keep the made four of a kind rather than drawing away from a premium winner.";
    if (label == "4 to a royal flush") return "Keep the four royal cards because drawing to a royal is the strongest premium draw.";
    if (label == "Pat full house") return "Keep the full house because it is already a strong made hand.";
    if (label == "Pat flush") return "Keep the made flush instead of breaking a paying hand.";
    if (label == "Pat three of a kind") return "Keep the trips and draw two cards to improve to a full house or four of a kind.";
    if (label == "Pat straight") return "Keep the made straight because it already returns a payout.";
    if (label == "4 to a straight flush") return "Keep the four-card straight flush draw because it combines straight and flush potential.";
    if (label == "Pat two pair") return "Keep both pairs and draw one card for a full house.";
    if (label == "High pair") return "Keep the high pair because it already pays and can improve further.";
    if (label == "3 to a royal flush") return "Keep the suited royal cards because they retain premium draw value.";
    if (label == "4 to a flush") return "Keep four suited cards to draw one card toward a flush.";
    if (label == "Low pair") return "Keep the pair and draw three cards to improve to trips, two pair, full house, or quads.";
    if (label == "4 to an outside straight") return "Keep the four-card open straight draw because it has multiple improving outs.";
    if (label == "2 suited high cards") return "Keep the suited high cards because they can make strong paying draws and high pairs.";
    if (label == "3 to a straight flush") return "Keep the suited connected cards because they retain straight flush potential.";
    if (label == "2 high cards") return "Keep the high cards because they can form a paying high pair or stronger draw.";
    if (label == "Suited ten-jack" || label == "Suited queen-jack" || label == "Suited king-queen" ||
        label == "Suited jack-king" || label == "Suited ace-high draw" || label == "Suited ace-ten" ||
        label == "Suited king-ten" || label == "Suited queen-ten") {
        return "Keep the suited high cards because they preserve both high-card value and flush potential.";
    }
    if (label == "Unsuited ten-jack" || label == "Unsuited queen-jack" || label == "Unsuited king-queen" ||
        label == "Unsuited jack-king") {
        return "Keep the connected high cards because they retain strong high-pair and straight-building value.";
    }
    if (label == "Single ace" || label == "Single king" || label == "Single queen" || label == "Single jack" || label == "Single ten") {
        return "Keep the best single high card when no stronger made hand or draw is available.";
    }
    if (label == "Hold nothing") return "Discard all five cards because there is no hold with better draw value.";
    return "Keep this combination because it best matches the strongest available strategy pattern.";
}

std::string rule_style_label_for_mask(const std::array<Card*, 5>& cards, uint8_t hold_mask) {
    if (hold_mask == 0) {
        return "Hold nothing";
    }

    uint32_t win_type = NONE;
    if (kept_mask_from_win_eval(cards, &win_type) == hold_mask) {
        switch (win_type) {
            case ROYALFLUSH: return "Pat royal flush";
            case STRAIGHTFLUSH: return "Pat straight flush";
            case FOUROFAKIND: return "Pat four of a kind";
            case FULLHOUSE: return "Pat full house";
            case FLUSH: return "Pat flush";
            case THREEOFAKIND: return "Pat three of a kind";
            case STRAIGHT: return "Pat straight";
            case TWOPAIR: return "Pat two pair";
            case HIGHPAIR: return "High pair";
            default: break;
        }
    }

    uint8_t selected_mask = 0;
    if (select_best_mask(cards, pred_4_to_royal, selected_mask) && selected_mask == hold_mask) return "4 to a royal flush";
    if (select_best_mask(cards, mask_is_4_to_straight_flush, selected_mask) && selected_mask == hold_mask) return "4 to a straight flush";
    if (select_best_mask(cards, pred_3_to_royal, selected_mask) && selected_mask == hold_mask) return "3 to a royal flush";
    if (select_best_mask(cards, pred_4_to_flush, selected_mask) && selected_mask == hold_mask) return "4 to a flush";
    if (select_best_mask(cards, mask_is_low_pair, selected_mask) && selected_mask == hold_mask) return "Low pair";
    if (select_best_mask(cards, mask_is_4_to_outside_straight, selected_mask) && selected_mask == hold_mask) return "4 to an outside straight";
    if (select_best_mask(cards, mask_is_2_suited_high, selected_mask) && selected_mask == hold_mask) return "2 suited high cards";
    if (select_best_mask(cards, pred_3_to_sf_strong, selected_mask) && selected_mask == hold_mask) return "3 to a straight flush";
    if (select_best_mask(cards, mask_is_2_unsuited_high, selected_mask) && selected_mask == hold_mask) return "2 high cards";
    if (select_best_mask(cards, pred_suited_tj, selected_mask) && selected_mask == hold_mask) return "Suited ten-jack";
    if (select_best_mask(cards, pred_suited_qj, selected_mask) && selected_mask == hold_mask) return "Suited queen-jack";
    if (select_best_mask(cards, pred_suited_kq, selected_mask) && selected_mask == hold_mask) return "Suited king-queen";
    if (select_best_mask(cards, pred_suited_jk, selected_mask) && selected_mask == hold_mask) return "Suited jack-king";
    if (select_best_mask(cards, pred_suited_ak_aq_aj, selected_mask) && selected_mask == hold_mask) return "Suited ace-high draw";
    if (select_best_mask(cards, pred_unsuited_tj, selected_mask) && selected_mask == hold_mask) return "Unsuited ten-jack";
    if (select_best_mask(cards, pred_unsuited_qj, selected_mask) && selected_mask == hold_mask) return "Unsuited queen-jack";
    if (select_best_mask(cards, pred_unsuited_kq, selected_mask) && selected_mask == hold_mask) return "Unsuited king-queen";
    if (select_best_mask(cards, pred_unsuited_jk, selected_mask) && selected_mask == hold_mask) return "Unsuited jack-king";
    if (select_best_mask(cards, pred_suited_at, selected_mask) && selected_mask == hold_mask) return "Suited ace-ten";
    if (select_best_mask(cards, pred_suited_kt, selected_mask) && selected_mask == hold_mask) return "Suited king-ten";
    if (select_best_mask(cards, pred_suited_qt, selected_mask) && selected_mask == hold_mask) return "Suited queen-ten";
    if (select_best_mask(cards, pred_3_to_sf_medium, selected_mask) && selected_mask == hold_mask) return "3 to a straight flush";
    if (select_best_mask(cards, pred_inside_3_high, selected_mask) && selected_mask == hold_mask) return "3 high cards to an inside straight";
    if (select_best_mask(cards, pred_one_ace, selected_mask) && selected_mask == hold_mask) return "Single ace";
    if (select_best_mask(cards, pred_one_king, selected_mask) && selected_mask == hold_mask) return "Single king";
    if (select_best_mask(cards, pred_one_queen, selected_mask) && selected_mask == hold_mask) return "Single queen";
    if (select_best_mask(cards, pred_one_jack, selected_mask) && selected_mask == hold_mask) return "Single jack";
    if (select_best_mask(cards, pred_one_ten, selected_mask) && selected_mask == hold_mask) return "Single ten";
    if (mask_is_high_pair(cards, hold_mask)) return "High pair";

    return "Best expected value hold";
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

uint32_t solver_auto_hold(const std::array<Card*, 5>& cards, uint32_t bet, GameVariant variant, double* out_ev) {
    thread_local std::unordered_map<uint64_t, uint8_t> best_mask_cache;
    thread_local std::unordered_map<uint64_t, double> ev_cache;

    const uint64_t cache_key = hand_cache_key(cards, bet, variant);

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
        evaluate_mask_ev(remaining, discard_slots, discard_count, base_cards, bet, variant, total_payout, ways);

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
    std::array<uint32_t, 13> rank_counts = {0};
    std::array<uint32_t, 4> suit_counts = {0};
    std::array<uint32_t, 5> ranks = {0};
    for (uint32_t pos = 0; pos < 5; pos++) {
        const uint32_t suit_idx = cards[pos]->suit() - SPADES;
        const uint32_t rank_idx = cards[pos]->rank() - TWO;
        const uint32_t card_id = suit_idx * 13 + rank_idx;
        const uint32_t feature_idx = pos * 52 + card_id;
        if (feature_idx < x.size()) x[feature_idx] = 1.0f;
        if (rank_idx < rank_counts.size()) rank_counts[rank_idx]++;
        if (suit_idx < suit_counts.size()) suit_counts[suit_idx]++;
        ranks[pos] = cards[pos]->rank();
    }
    if (x.size() > 260) x[260] = static_cast<float>(bet) / 5.0f;
    if (x.size() > 261) {
        for (uint32_t i = 0; i < rank_counts.size() && (261 + i) < x.size(); i++) {
            x[261 + i] = static_cast<float>(rank_counts[i]) / 4.0f;
        }
    }
    if (x.size() > 274) {
        for (uint32_t i = 0; i < suit_counts.size() && (274 + i) < x.size(); i++) {
            x[274 + i] = static_cast<float>(suit_counts[i]) / 5.0f;
        }
    }
    if (x.size() > 278) {
        std::sort(ranks.begin(), ranks.end());
        for (uint32_t i = 0; i < ranks.size() && (278 + i) < x.size(); i++) {
            x[278 + i] = static_cast<float>(ranks[i]) / 14.0f;
        }
    }
    if (x.size() > 283) {
        uint32_t distinct_ranks = 0;
        for (uint32_t count : rank_counts) {
            if (count > 0) distinct_ranks++;
        }
        x[283] = static_cast<float>(distinct_ranks) / 5.0f;
    }
    if (x.size() > 284) {
        uint32_t max_suit = 0;
        for (uint32_t count : suit_counts) {
            if (count > max_suit) max_suit = count;
        }
        x[284] = static_cast<float>(max_suit) / 5.0f;
    }
    if (x.size() > 285) {
        uint32_t high_cards = 0;
        for (uint32_t rank : ranks) {
            if (rank >= JACK) high_cards++;
        }
        x[285] = static_cast<float>(high_cards) / 5.0f;
    }

    std::vector<float> hidden1(g_ml_hidden1_size, 0.0f);
    for (uint32_t j = 0; j < g_ml_hidden1_size; j++) {
        float v = g_ml_b1[j];
        const size_t row_offset = static_cast<size_t>(j) * g_ml_input_size;
        for (uint32_t i = 0; i < g_ml_input_size; i++) v += x[i] * g_ml_w1[row_offset + i];
        hidden1[j] = (v > 0.0f) ? v : 0.0f;
    }

    std::vector<float> hidden2;
    const bool has_second_hidden = g_ml_hidden2_size > 0 && !g_ml_w3.empty() && !g_ml_b3.empty();
    if (has_second_hidden) {
        hidden2.assign(g_ml_hidden2_size, 0.0f);
        for (uint32_t j = 0; j < g_ml_hidden2_size; j++) {
            float v = g_ml_b2[j];
            const size_t row_offset = static_cast<size_t>(j) * g_ml_hidden1_size;
            for (uint32_t i = 0; i < g_ml_hidden1_size; i++) v += hidden1[i] * g_ml_w2[row_offset + i];
            hidden2[j] = (v > 0.0f) ? v : 0.0f;
        }
    }

    uint32_t best_mask = 0;
    if (g_ml_output_size == 5) {
        for (uint32_t k = 0; k < 5; k++) {
            float v = has_second_hidden ? g_ml_b3[k] : g_ml_b2[k];
            if (has_second_hidden) {
                const size_t row_offset = static_cast<size_t>(k) * g_ml_hidden2_size;
                for (uint32_t j = 0; j < g_ml_hidden2_size; j++) v += hidden2[j] * g_ml_w3[row_offset + j];
            } else {
                const size_t row_offset = static_cast<size_t>(k) * g_ml_hidden1_size;
                for (uint32_t j = 0; j < g_ml_hidden1_size; j++) v += hidden1[j] * g_ml_w2[row_offset + j];
            }
            if (v > 0.0f) {
                best_mask |= (1u << k);
            }
        }
    } else {
        float best_logit = 0.0f;
        bool have_best = false;
        for (uint32_t k = 0; k < g_ml_output_size; k++) {
            float v = has_second_hidden ? g_ml_b3[k] : g_ml_b2[k];
            if (has_second_hidden) {
                const size_t row_offset = static_cast<size_t>(k) * g_ml_hidden2_size;
                for (uint32_t j = 0; j < g_ml_hidden2_size; j++) v += hidden2[j] * g_ml_w3[row_offset + j];
            } else {
                const size_t row_offset = static_cast<size_t>(k) * g_ml_hidden1_size;
                for (uint32_t j = 0; j < g_ml_hidden1_size; j++) v += hidden1[j] * g_ml_w2[row_offset + j];
            }
            if (!have_best || v > best_logit) {
                best_logit = v;
                best_mask = k;
                have_best = true;
            }
        }
        if (best_mask > 31) best_mask = 31;
    }
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

    uint32_t input_size = 0;
    uint32_t hidden1_size = 0;
    uint32_t hidden2_size = 0;
    uint32_t output_size = 0;
    std::vector<float> w1, b1, w2, b2, w3, b3;

    if (!parse_json_uint_field(text, "input_size", input_size) ||
        !parse_json_uint_field(text, "output_size", output_size) ||
        !parse_json_float_array_field(text, "W1", w1) ||
        !parse_json_float_array_field(text, "b1", b1) ||
        !parse_json_float_array_field(text, "W2", w2) ||
        !parse_json_float_array_field(text, "b2", b2)) {
        return false;
    }

    const bool has_hidden2 =
        parse_json_uint_field(text, "hidden1_size", hidden1_size) &&
        parse_json_uint_field(text, "hidden2_size", hidden2_size) &&
        parse_json_float_array_field(text, "W3", w3) &&
        parse_json_float_array_field(text, "b3", b3);

    if (!has_hidden2) {
        if (!parse_json_uint_field(text, "hidden_size", hidden1_size)) {
            return false;
        }
        hidden2_size = 0;
    }

    if (w1.size() != static_cast<size_t>(hidden1_size) * input_size ||
        b1.size() != hidden1_size) {
        return false;
    }

    if (has_hidden2) {
        if (w2.size() != static_cast<size_t>(hidden2_size) * hidden1_size ||
            b2.size() != hidden2_size ||
            w3.size() != static_cast<size_t>(output_size) * hidden2_size ||
            b3.size() != output_size) {
            return false;
        }
    } else {
        if (w2.size() != static_cast<size_t>(output_size) * hidden1_size ||
            b2.size() != output_size) {
            return false;
        }
    }

    for (float v : w1) if (!std::isfinite(v)) return false;
    for (float v : b1) if (!std::isfinite(v)) return false;
    for (float v : w2) if (!std::isfinite(v)) return false;
    for (float v : b2) if (!std::isfinite(v)) return false;
    for (float v : w3) if (!std::isfinite(v)) return false;
    for (float v : b3) if (!std::isfinite(v)) return false;

    g_ml_input_size = input_size;
    g_ml_hidden1_size = hidden1_size;
    g_ml_hidden2_size = hidden2_size;
    g_ml_output_size = output_size;
    g_ml_w1 = std::move(w1);
    g_ml_b1 = std::move(b1);
    g_ml_w2 = std::move(w2);
    g_ml_b2 = std::move(b2);
    g_ml_w3 = std::move(w3);
    g_ml_b3 = std::move(b3);
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

uint32_t AutoHold::auto_hold(const std::array<Card*, 5>& cards, uint32_t bet, GameVariant variant, double* out_ev) {
    if (g_engine == Engine::RULE) {
        if (out_ev) *out_ev = 0.0; // Rule engine doesn't compute EV easily
        return rule_auto_hold(cards);
    } else if (g_engine == Engine::ML) {
        if (out_ev) *out_ev = 0.0; // ML engine doesn't compute EV easily
        return ml_auto_hold(cards, bet);
    }
    return solver_auto_hold(cards, bet, variant, out_ev);
}

std::string AutoHold::explain_hold_label(const std::array<Card*, 5>& cards, uint32_t hold_mask) {
    return rule_style_label_for_mask(cards, static_cast<uint8_t>(hold_mask & 31u));
}

std::string AutoHold::explain_hold_summary(const std::array<Card*, 5>& cards, uint32_t hold_mask) {
    const std::string label = explain_hold_label(cards, hold_mask);
    return explanation_summary_for_label(label);
}

bool AutoHold::solver_top_two(const std::array<Card*, 5>& cards, uint32_t bet, GameVariant variant, uint32_t& best_mask, double& best_ev, uint32_t& second_mask, double& second_ev) {
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

    bool have_best = false;
    bool have_second = false;
    uint64_t best_total_payout = 0;
    uint32_t best_ways = 1;
    uint64_t second_total_payout = 0;
    uint32_t second_ways = 1;
    best_mask = 0;
    second_mask = 0;

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
        evaluate_mask_ev(remaining, discard_slots, discard_count, base_cards, bet, variant, total_payout, ways);

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
            second_mask = best_mask;
            second_total_payout = best_total_payout;
            second_ways = best_ways;
            have_second = true;

            best_mask = mask;
            best_total_payout = total_payout;
            best_ways = ways;
            continue;
        }

        if (!have_second) {
            second_mask = mask;
            second_total_payout = total_payout;
            second_ways = ways;
            have_second = true;
            continue;
        }

        lhs = static_cast<__uint128_t>(total_payout) * second_ways;
        rhs = static_cast<__uint128_t>(second_total_payout) * ways;
        if (lhs > rhs) {
            second_mask = mask;
            second_total_payout = total_payout;
            second_ways = ways;
        }
    }

    best_ev = static_cast<double>(best_total_payout) / static_cast<double>(best_ways);
    second_ev = have_second ? (static_cast<double>(second_total_payout) / static_cast<double>(second_ways)) : best_ev;
    return have_best;
}
