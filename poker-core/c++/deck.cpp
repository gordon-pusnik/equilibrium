#include <algorithm>
#include <iostream>
#include <set>
#include "deck.h"
#include "hand.h"
#include "card.h"

Deck::Deck() {
    m_cards.reserve(DECK_SIZE);
    for (uint32_t suit = SPADES; suit <= DIAMONDS; suit++) {
        for (uint32_t rank = TWO; rank <= ACE; rank++) {
            m_cards.emplace_back(suit, rank);
        }
    }

    m_hand = std::make_unique<Hand>();
    m_index = 0;
}

void Deck::init(uint32_t seed) {
    m_rng.seed(seed);
    shuffle();
    new_hand();
}

Card* Deck::next_card() {
    if (m_index >= DECK_SIZE) {
        shuffle();
    }
    return &m_cards[m_sequence[m_index++]];
}

void Deck::new_hand() {
    for (auto& card : m_cards) {
        card.reset();
    }
    m_hand->new_hand(this);
}

void Deck::draw_cards() {
    m_hand->draw_cards(this);
}

void Deck::shuffle() {
    m_index = 0;
    for (uint32_t i = 0; i < DECK_SIZE; i++) {
        m_sequence[i] = i;
    }
    std::shuffle(m_sequence.begin(), m_sequence.end(), m_rng);
    verify();
}

void Deck::verify() {
    std::set<std::pair<uint32_t, uint32_t>> seen_cards;
    for (const auto& card : m_cards) {
        seen_cards.insert({card.suit(), card.rank()});
    }

    if (seen_cards.size() != DECK_SIZE) {
        std::cerr << "Deck verification failed! Expected 52 unique cards, found " << seen_cards.size() << std::endl;
    }
}
