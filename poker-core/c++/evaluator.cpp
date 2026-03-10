#include "evaluator.h"
#include "card.h"
#include <algorithm>
#include <map>
#include <vector>

namespace PokerEvaluator {

static std::string rank_to_name(uint32_t rank, bool plural = false) {
    std::string name;
    switch(rank) {
        case 14: name = "Ace"; break;
        case 13: name = "King"; break;
        case 12: name = "Queen"; break;
        case 11: name = "Jack"; break;
        case 10: name = "Ten"; break;
        case 9: name = "Nine"; break;
        case 8: name = "Eight"; break;
        case 7: name = "Seven"; break;
        case 6: name = "Six"; break;
        case 5: name = "Five"; break;
        case 4: name = "Four"; break;
        case 3: name = "Three"; break;
        case 2: name = "Two"; break;
        default: name = "Unknown"; break;
    }
    if (plural) {
        if (rank == 6) return name + "es";
        return name + "s";
    }
    return name;
}

Evaluation evaluate_hand(const std::array<Card*, 5>& cards) {
    std::array<uint32_t, 5> ranks;
    std::array<uint32_t, 5> suits;
    
    for (int i = 0; i < 5; i++) {
        ranks[i] = cards[i]->rank();
        suits[i] = cards[i]->suit();
    }

    std::sort(ranks.begin(), ranks.end(), std::greater<uint32_t>());

    bool flush = true;
    for (int i = 1; i < 5; i++) if (suits[i] != suits[0]) flush = false;

    bool straight = false;
    std::array<uint32_t, 5> unique_ranks = ranks;
    auto last = std::unique(unique_ranks.begin(), unique_ranks.end());
    if (last - unique_ranks.begin() == 5) {
        if (ranks[0] - ranks[4] == 4) straight = true;
        if (ranks[0] == 14 && ranks[1] == 5 && ranks[4] == 2) straight = true; // Wheel
    }

    std::map<uint32_t, int> counts;
    for (uint32_t r : ranks) counts[r]++;

    std::vector<std::pair<int, uint32_t>> freq;
    for (auto const& [rank, count] : counts) freq.push_back({count, rank});
    std::sort(freq.begin(), freq.end(), std::greater<std::pair<int, uint32_t>>());

    Evaluation ev;
    
    if (straight && flush) {
        if (ranks[0] == 14 && ranks[1] == 13) {
            ev.hand_name = "Royal Flush";
            ev.rank_value = 1;
        } else {
            ev.hand_name = "Straight Flush";
            ev.rank_value = 11 - (ranks[0] == 14 && ranks[1] == 5 ? 5 : ranks[0]); 
        }
    } else if (freq[0].first == 4) {
        ev.hand_name = "Four of a Kind";
        ev.rank_value = 11 + (14 - freq[0].second) * 12;
    } else if (freq[0].first == 3 && freq[1].first == 2) {
        ev.hand_name = "Full House";
        ev.rank_value = 167 + (14 - freq[0].second) * 12;
    } else if (flush) {
        ev.hand_name = "Flush";
        ev.rank_value = 323 + (14 - ranks[0]);
    } else if (straight) {
        ev.hand_name = "Straight";
        ev.rank_value = 1600 + (14 - (ranks[0] == 14 && ranks[1] == 5 ? 5 : ranks[0]));
    } else if (freq[0].first == 3) {
        ev.hand_name = "Three of a Kind";
        ev.rank_value = 1611 + (14 - freq[0].second) * 100;
    } else if (freq[0].first == 2 && freq[1].first == 2) {
        ev.hand_name = "Two Pair";
        ev.rank_value = 2470 + (14 - freq[0].second) * 50 + (14 - freq[1].second);
    } else if (freq[0].first == 2) {
        ev.hand_name = "Pair of " + rank_to_name(freq[0].second, true);
        if (freq[0].second == 14) ev.rank_value = 3325;
        else if (freq[0].second == 13) ev.rank_value = 3540;
        else ev.rank_value = 3325 + (14 - freq[0].second) * 215;
    } else {
        ev.hand_name = "High Card";
        ev.rank_value = 6186 + (14 - ranks[0]) * 100;
    }

    return ev;
}

} // namespace PokerEvaluator
