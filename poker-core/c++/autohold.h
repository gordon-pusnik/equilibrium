#ifndef __AUTOHOLD_H__
#define __AUTOHOLD_H__

#include <cstdint>
#include <array>
#include <string>
#include "game_variant.h"

class Card;

namespace AutoHold {
    enum class Engine {
        SOLVER,
        RULE,
        ML
    };

    void set_verbose(bool verbose);
    bool set_engine(const char* engine_name);
    bool set_ml_model(const char* model_path);
    Engine engine();
    void print_rule_strategy();
    uint32_t auto_hold(const std::array<Card*, 5>& cards, uint32_t bet, GameVariant variant, double* out_ev = nullptr);
    std::string explain_hold_label(const std::array<Card*, 5>& cards, uint32_t hold_mask);
    std::string explain_hold_summary(const std::array<Card*, 5>& cards, uint32_t hold_mask);
    bool solver_top_two(const std::array<Card*, 5>& cards, uint32_t bet, GameVariant variant, uint32_t& best_mask, double& best_ev, uint32_t& second_mask, double& second_ev);
}

#endif //__AUTOHOLD_H__
