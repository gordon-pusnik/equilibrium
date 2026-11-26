#ifndef EQUILIBRIUM_CLI_HOLD_POLICY_H
#define EQUILIBRIUM_CLI_HOLD_POLICY_H

#include <array>
#include <cstdint>
#include <string>
#include <vector>

#include "game_variant.h"

class Card;

// Not registered with AutoHold: the reranker is only available to CLI tools.
class CliHoldPolicy {
public:
    bool configure(const std::string& engine, const std::string& model_path,
                   GameVariant variant, uint32_t bet, std::string& error);
    uint32_t hold(const std::array<Card*, 5>& cards) const;

private:
    GameVariant variant_ = GameVariant::JACKS_OR_BETTER_9_6;
    uint32_t bet_ = 5;
    std::vector<float> ranker_;
    std::vector<float> reranker_;
    float max_margin_ = 0;
    float min_gain_ = 0;
};

#endif
