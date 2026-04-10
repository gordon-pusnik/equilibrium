#ifndef GAME_VARIANT_H
#define GAME_VARIANT_H

#include <cstdint>

enum class GameVariant {
    JACKS_OR_BETTER_9_6 = 0,
    JACKS_OR_BETTER_8_5 = 1,
};

struct GameVariantInfo {
    const char* id;
    const char* display_name;
    double optimal_rtp;
    bool is_premium;
    uint32_t high_pair;
    uint32_t two_pair;
    uint32_t three_of_a_kind;
    uint32_t straight;
    uint32_t flush;
    uint32_t full_house;
    uint32_t four_of_a_kind;
    uint32_t straight_flush;
    uint32_t royal_flush;
    uint32_t royal_flush_max_bet;
};

const GameVariantInfo& game_variant_info(GameVariant variant);
bool parse_game_variant_id(const char* variant_id, GameVariant& out_variant);
uint32_t payout_for_result(uint32_t result, uint32_t bet, GameVariant variant);

#endif
