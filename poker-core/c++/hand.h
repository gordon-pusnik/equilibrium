#ifndef __HAND_H__
#define __HAND_H__

#include <array>
#include <cstdint>

class Deck;
class Card;

class Hand {
public:
    Hand(){};

    void new_hand(Deck *deck);
    void draw_cards(Deck *deck);
    void to_console() const;
    void auto_hold(uint32_t bet) const;
    uint32_t check_for_win(uint32_t bet) const;
    std::array<Card*, 5> cards() const { return m_cards; }

private:
    std::array<Card*, 5> m_cards;
};

enum WinningHand {
    NONE = 0,
    HIGHPAIR,
    TWOPAIR,
    THREEOFAKIND,
    STRAIGHT,
    FLUSH,
    FULLHOUSE,
    FOUROFAKIND,
    STRAIGHTFLUSH,
    ROYALFLUSH
};

#endif // __HAND_H__
