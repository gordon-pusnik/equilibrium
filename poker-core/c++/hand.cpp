#include "hand.h"
#include "deck.h"
#include "card.h"
#include "checkforwin.h"
#include "autohold.h"
#include "game_variant.h"
#include <iostream>

void Hand::new_hand(Deck *deck) {
    for (auto& card : m_cards) {
        card = deck->next_card();
    }
}

void Hand::draw_cards(Deck *deck) {
    for (auto& card : m_cards) {
        if (!card->is_held()) {
            card = deck->next_card();
        }
    }
}

void Hand::to_console() const {
    for (const auto* card : m_cards) {
        card->print_card();
    }
    std::cout << std::endl;

    for (const auto* card : m_cards) {
        card->print_held();
    }
    std::cout << std::endl;
}

void Hand::auto_hold(uint32_t bet, GameVariant variant) const {
    AutoHold::auto_hold(m_cards, bet, variant);
}

uint32_t Hand::check_for_win(uint32_t bet, GameVariant variant) const {
    uint32_t winnings = 0;
    const GameVariantInfo& info = game_variant_info(variant);

    switch(CheckForWin::check_for_win(m_cards)) {
        case NONE:
            std::cout << "Win nothing" << std::endl;
            break;
        case HIGHPAIR:
            winnings = bet * info.high_pair;
            std::cout << "Win high pair = " << winnings << std::endl;
            break;
        case TWOPAIR:
            winnings = bet * info.two_pair;
            std::cout << "Win two pair = " << winnings << std::endl;
            break;
        case THREEOFAKIND:
            winnings = bet * info.three_of_a_kind;
            std::cout << "Win three of a kind = " << winnings << std::endl;
            break;
        case STRAIGHT:
            winnings = bet * info.straight;
            std::cout << "Win straight = " << winnings << std::endl;
            break;
        case FLUSH:
            winnings = bet * info.flush;
            std::cout << "Win flush = " << winnings << std::endl;
            break;
        case FULLHOUSE:
            winnings = bet * info.full_house;
            std::cout << "Win full house = " << winnings << std::endl;
            break;
        case FOUROFAKIND:
            winnings = bet * info.four_of_a_kind;
            std::cout << "Win four of a kind = " << winnings << std::endl;
            break;
        case STRAIGHTFLUSH:
            winnings = bet * info.straight_flush;
            std::cout << "Win straight flush = " << winnings << std::endl;
            break;
        case ROYALFLUSH:
            winnings = (bet == 5) ? info.royal_flush_max_bet : (bet * info.royal_flush);
            std::cout << "Win royal flush = " << winnings << std::endl;
            break;
    }

    return winnings;
}
