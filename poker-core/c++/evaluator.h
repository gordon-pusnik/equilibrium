#ifndef __EVALUATOR_H__
#define __EVALUATOR_H__

#include <cstdint>
#include <string>
#include <array>

class Card;

namespace PokerEvaluator {
    struct Evaluation {
        std::string hand_name;
        uint32_t rank_value; // 1 (Best) to 7462 (Worst)
    };

    Evaluation evaluate_hand(const std::array<Card*, 5>& cards);
}

#endif // __EVALUATOR_H__
