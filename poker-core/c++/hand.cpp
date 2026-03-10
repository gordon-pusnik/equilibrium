#include "hand.h"
#include "deck.h"
#include "card.h"
#include "checkforwin.h"
#include "autohold.h"
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

void Hand::auto_hold(uint32_t bet) const {
    AutoHold::auto_hold(m_cards, bet);
}

uint32_t Hand::check_for_win(uint32_t bet) const {
    uint32_t winnings = 0;

    switch(CheckForWin::check_for_win(m_cards)) {
        case NONE:
            std::cout << "Win nothing" << std::endl;
            break;
        case HIGHPAIR:
            winnings = bet * 1;
            std::cout << "Win high pair = " << winnings << std::endl;
            break;
        case TWOPAIR:
            winnings = bet * 2;
            std::cout << "Win two pair = " << winnings << std::endl;
            break;
        case THREEOFAKIND:
            winnings = bet * 3;
            std::cout << "Win three of a kind = " << winnings << std::endl;
            break;
        case STRAIGHT:
            winnings = bet * 4;
            std::cout << "Win straight = " << winnings << std::endl;
            break;
        case FLUSH:
            winnings = bet * 6;
            std::cout << "Win flush = " << winnings << std::endl;
            break;
        case FULLHOUSE:
            winnings = bet * 9;
            std::cout << "Win full house = " << winnings << std::endl;
            break;
        case FOUROFAKIND:
            winnings = bet * 25;
            std::cout << "Win four of a kind = " << winnings << std::endl;
            break;
        case STRAIGHTFLUSH:
            winnings = bet * 50;
            std::cout << "Win straight flush = " << winnings << std::endl;
            break;
        case ROYALFLUSH:
            if (bet == 5) {
                winnings = bet * 800;
            } else {
                winnings = bet * 250;
            }
            std::cout << "Win royal flush = " << winnings << std::endl;
            break;
    }

    return winnings;
}
