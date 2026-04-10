#include "game_variant.h"

#include <cstring>

#include "hand.h"

namespace {
const GameVariantInfo kJacksOrBetter96 = {
    "jacks_or_better_9_6",
    "Jacks or Better 9/6",
    0.995439,
    false,
    1,
    2,
    3,
    4,
    6,
    9,
    25,
    50,
    250,
    4000
};

const GameVariantInfo kJacksOrBetter85 = {
    "jacks_or_better_8_5",
    "Jacks or Better 8/5",
    0.972985,
    false,
    1,
    2,
    3,
    4,
    5,
    8,
    25,
    50,
    250,
    4000
};
}

const GameVariantInfo& game_variant_info(GameVariant variant) {
    switch (variant) {
        case GameVariant::JACKS_OR_BETTER_8_5:
            return kJacksOrBetter85;
        case GameVariant::JACKS_OR_BETTER_9_6:
        default:
            return kJacksOrBetter96;
    }
}

bool parse_game_variant_id(const char* variant_id, GameVariant& out_variant) {
    if (variant_id == nullptr) {
        return false;
    }
    if (std::strcmp(variant_id, kJacksOrBetter96.id) == 0) {
        out_variant = GameVariant::JACKS_OR_BETTER_9_6;
        return true;
    }
    if (std::strcmp(variant_id, kJacksOrBetter85.id) == 0) {
        out_variant = GameVariant::JACKS_OR_BETTER_8_5;
        return true;
    }
    return false;
}

uint32_t payout_for_result(uint32_t result, uint32_t bet, GameVariant variant) {
    const GameVariantInfo& info = game_variant_info(variant);
    switch (result) {
        case NONE: return 0;
        case HIGHPAIR: return bet * info.high_pair;
        case TWOPAIR: return bet * info.two_pair;
        case THREEOFAKIND: return bet * info.three_of_a_kind;
        case STRAIGHT: return bet * info.straight;
        case FLUSH: return bet * info.flush;
        case FULLHOUSE: return bet * info.full_house;
        case FOUROFAKIND: return bet * info.four_of_a_kind;
        case STRAIGHTFLUSH: return bet * info.straight_flush;
        case ROYALFLUSH: return bet == 5 ? info.royal_flush_max_bet : bet * info.royal_flush;
        default: return 0;
    }
}
