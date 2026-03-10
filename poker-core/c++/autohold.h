#ifndef __AUTOHOLD_H__
#define __AUTOHOLD_H__

#include <cstdint>
#include <array>

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
    uint32_t auto_hold(const std::array<Card*, 5>& cards, uint32_t bet, double* out_ev = nullptr);
}

#endif //__AUTOHOLD_H__
