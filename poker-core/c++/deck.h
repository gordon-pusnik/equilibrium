#ifndef __DECK_H__
#define __DECK_H__

#include <cstdint>
#include <random>
#include <vector>
#include <memory>
#include <array>

class Hand;
class Card;

#define DECK_SIZE 52

class Deck {
public:
    Deck();
    ~Deck() = default;

    void init(uint32_t seed);
    Card* next_card();
    void shuffle();
    void new_hand();
    void draw_cards();
    Hand* hand() {return m_hand.get();};
    void verify();

private:
    uint32_t m_index;
    std::vector<Card> m_cards;
    std::array<uint32_t, DECK_SIZE> m_sequence;
    std::mt19937_64 m_rng;
    std::unique_ptr<Hand> m_hand;
};

#endif //__DECK_H__
