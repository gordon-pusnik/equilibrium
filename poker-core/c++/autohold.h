#ifndef __AUTOHOLD_H__
#define __AUTOHOLD_H__

#include <cstdint>
#include <array>
#include <string>
#include "game_variant.h"

class Card;

namespace AutoHold {
    struct HoldExplanation {
        std::string category;
        std::string headline;
        std::string summary;
        std::string pattern_tip;
    };

    struct MistakeAnalysis {
        uint32_t best_mask;
        double best_ev;
        double player_ev;
        double ev_delta;
        std::string severity;
    };

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
    HoldExplanation explain_hold(const std::array<Card*, 5>& cards, uint32_t hold_mask);
    std::string explain_hold_label(const std::array<Card*, 5>& cards, uint32_t hold_mask);
    std::string explain_hold_summary(const std::array<Card*, 5>& cards, uint32_t hold_mask);
    std::string classify_mistake_severity(double ev_delta, bool exact_match = false);
    bool analyze_player_hold(const std::array<Card*, 5>& cards, uint32_t bet, GameVariant variant, uint32_t player_mask, MistakeAnalysis& out_analysis);
    bool solver_top_two(const std::array<Card*, 5>& cards, uint32_t bet, GameVariant variant, uint32_t& best_mask, double& best_ev, uint32_t& second_mask, double& second_ev);
}

#endif //__AUTOHOLD_H__
