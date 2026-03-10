#include "checkforwin.h"
#include "hand.h"
#include "card.h"
#include <algorithm>
#include <vector>

uint32_t CheckForWin::check_for_win(const std::array<Card*, 5>& cards) {
    return check_high_or_better(cards, JACK);
}

uint32_t CheckForWin::check_high_or_better(const std::array<Card*, 5>& input_cards, uint32_t high) {
    std::array<Card*, 5> cards = input_cards;

    std::sort(cards.begin(), cards.end(),
        [](Card *a, Card *b) {
            return a->rank() < b->rank();
        }
    );

    // Check for flush
    bool flush = (input_cards[0]->suit() == input_cards[1]->suit()) &&
                 (input_cards[1]->suit() == input_cards[2]->suit()) &&
                 (input_cards[2]->suit() == input_cards[3]->suit()) &&
                 (input_cards[3]->suit() == input_cards[4]->suit());

    if (flush) {
        for (auto* card : cards) card->set_kept(true);

        // Have flush, check for what kind of flush
        if (cards[0]->rank() == TEN &&
            cards[1]->rank() == JACK &&
            cards[2]->rank() == QUEEN &&
            cards[3]->rank() == KING &&
            cards[4]->rank() == ACE) {
            return ROYALFLUSH;
        } else if (((cards[0]->rank() + 1 == cards[1]->rank()) &&
                    (cards[1]->rank() + 1 == cards[2]->rank()) &&
                    (cards[2]->rank() + 1 == cards[3]->rank()) &&
                    (cards[3]->rank() + 1 == cards[4]->rank())) ||
                  ((cards[0]->rank() == TWO) &&
                   (cards[1]->rank() == THREE) &&
                   (cards[2]->rank() == FOUR) &&
                   (cards[3]->rank() == FIVE) &&
                   (cards[4]->rank() == ACE))) {
            return STRAIGHTFLUSH;
        }
        else {
            return FLUSH;
        }
    }

    // Four of a kind
    if (cards[0]->rank() == cards[1]->rank() &&
        cards[1]->rank() == cards[2]->rank() &&
        cards[2]->rank() == cards[3]->rank()) {
        cards[0]->set_kept(true); cards[1]->set_kept(true); cards[2]->set_kept(true); cards[3]->set_kept(true);
        return FOUROFAKIND;
    } else if (cards[1]->rank() == cards[2]->rank() &&
               cards[2]->rank() == cards[3]->rank() &&
               cards[3]->rank() == cards[4]->rank()) {
        cards[1]->set_kept(true); cards[2]->set_kept(true); cards[3]->set_kept(true); cards[4]->set_kept(true);
        return FOUROFAKIND;
    }

    // Full house
    if (cards[0]->rank() == cards[1]->rank() &&
        cards[2]->rank() == cards[3]->rank() &&
        cards[3]->rank() == cards[4]->rank()) {
        for (auto* card : cards) card->set_kept(true);
        return FULLHOUSE;
    } else if (cards[0]->rank() == cards[1]->rank() &&
               cards[1]->rank() == cards[2]->rank() &&
               cards[3]->rank() == cards[4]->rank()) {
        for (auto* card : cards) card->set_kept(true);
        return FULLHOUSE;
    }

    // Straight
    if (cards[0]->rank() + 1 == cards[1]->rank() &&
         cards[1]->rank() + 1 == cards[2]->rank() &&
         cards[2]->rank() + 1 == cards[3]->rank() &&
         cards[3]->rank() + 1 == cards[4]->rank()) {
        for (auto* card : cards) card->set_kept(true);
        return STRAIGHT;
    } else if (cards[0]->rank() == TWO &&
               cards[1]->rank() == THREE &&
               cards[2]->rank() == FOUR &&
               cards[3]->rank() == FIVE &&
               cards[4]->rank() == ACE) {
        for (auto* card : cards) card->set_kept(true);
        return STRAIGHT;
    }

    // Three of a kind
    if (cards[0]->rank() == cards[1]->rank() &&
        cards[1]->rank() == cards[2]->rank()) {
        cards[0]->set_kept(true); cards[1]->set_kept(true); cards[2]->set_kept(true);
        return THREEOFAKIND;
    } else if (cards[1]->rank() == cards[2]->rank() &&
               cards[2]->rank() == cards[3]->rank()) {
        cards[1]->set_kept(true); cards[2]->set_kept(true); cards[3]->set_kept(true);
        return THREEOFAKIND;
    } else if (cards[2]->rank() == cards[3]->rank() &&
               cards[3]->rank() == cards[4]->rank()) {
        cards[2]->set_kept(true); cards[3]->set_kept(true); cards[4]->set_kept(true);
        return THREEOFAKIND;
    }

    // Two pair
    if (cards[0]->rank() == cards[1]->rank() &&
        cards[2]->rank() == cards[3]->rank()) {
        cards[0]->set_kept(true); cards[1]->set_kept(true); cards[2]->set_kept(true); cards[3]->set_kept(true);
        return TWOPAIR;
    } else if (cards[0]->rank() == cards[1]->rank() &&
               cards[2]->rank() == cards[4]->rank()) {
        cards[0]->set_kept(true); cards[1]->set_kept(true); cards[2]->set_kept(true); cards[4]->set_kept(true);
        return TWOPAIR;
    } else if (cards[0]->rank() == cards[1]->rank() &&
               cards[3]->rank() == cards[4]->rank()) {
        cards[0]->set_kept(true); cards[1]->set_kept(true); cards[3]->set_kept(true); cards[4]->set_kept(true);
        return TWOPAIR;
    } else if (cards[1]->rank() == cards[2]->rank() &&
               cards[3]->rank() == cards[4]->rank()) {
        cards[1]->set_kept(true); cards[2]->set_kept(true); cards[3]->set_kept(true); cards[4]->set_kept(true);
        return TWOPAIR;
    }

    // High pair
    if (cards[0]->rank() == cards[1]->rank() &&
        cards[0]->rank() >= high) {
        cards[0]->set_kept(true); cards[1]->set_kept(true);
        return HIGHPAIR;
    } else if (cards[1]->rank() == cards[2]->rank() &&
               cards[1]->rank() >= high) {
        cards[1]->set_kept(true); cards[2]->set_kept(true);
        return HIGHPAIR;
    } else if (cards[2]->rank() == cards[3]->rank() &&
               cards[2]->rank() >= high) {
        cards[2]->set_kept(true); cards[3]->set_kept(true);
        return HIGHPAIR;
    } else if (cards[3]->rank() == cards[4]->rank() &&
               cards[3]->rank() >= high) {
        cards[3]->set_kept(true); cards[4]->set_kept(true);
        return HIGHPAIR;
    }

    return NONE;
}
