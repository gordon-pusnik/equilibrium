#ifndef __CARD_H__
#define __CARD_H__

#include <cstdint>
#include <string>

class Card {
public:
    Card(uint32_t suit, uint32_t rank);

    uint32_t suit() const {return m_suit;};
    uint32_t rank() const {return m_rank;};
    void set_rank(uint32_t i) {m_rank = i;};
    void set_suit(uint32_t i) {m_suit = i;};
    bool is_held() const {return m_held;};
    bool is_kept() const {return m_kept;};
    void set_held(bool b) {m_held = b;};
    void set_kept(bool b) {m_kept = b;};
    void reset() {set_held(false); set_kept(false);};
    void print_card() const;
    void print_held() const;

    std::string to_string() const;
    std::string to_string_wild() const;
    std::string to_string_rank() const;

private:
    uint32_t m_suit;
    uint32_t m_rank;
    bool m_held;
    bool m_kept;
};

enum Suit {
    JOKER_SUIT,
    SPADES,
    CLUBS,
    HEARTS,
    DIAMONDS
};

enum Rank {
    JOKER = 1,
    TWO,
    THREE,
    FOUR,
    FIVE,
    SIX,
    SEVEN,
    EIGHT,
    NINE,
    TEN,
    JACK,
    QUEEN,
    KING,
    ACE
};

#endif // __CARD_H__
