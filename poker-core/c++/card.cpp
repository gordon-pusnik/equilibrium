#include "card.h"
#include <iostream>

Card::Card(uint32_t suit, uint32_t rank) {
    m_suit = suit;
    m_rank = rank;
    m_held = false;
    m_kept = false;
}

std::string Card::to_string() const {
    std::string name;

    switch(m_rank) {
        case TWO:
            name = "two";
            break;
        case THREE:
            name = "three";
            break;
        case FOUR:
            name = "four";
            break;
        case FIVE:
            name = "five";
            break;
        case SIX:
            name = "six";
            break;
        case SEVEN:
            name = "seven";
            break;
        case EIGHT:
            name = "eight";
            break;
        case NINE:
            name = "nine";
            break;
        case TEN:
            name = "ten";
            break;
        case JACK:
            name = "jack";
            break;
        case QUEEN:
            name = "queen";
            break;
        case KING:
            name = "king";
            break;
        case ACE:
            name = "ace";
            break;
        case JOKER:
            name = "joker";
            break;
    };

    switch(m_suit) {
        case SPADES:
            name += "_spades";
            break;
        case CLUBS:
            name += "_clubs";
            break;
        case HEARTS:
            name += "_hearts";
            break;
        case DIAMONDS:
            name += "_diamonds";
            break;
    };

    return name;
}

std::string Card::to_string_wild() const {
    std::string name;

    switch(m_rank) {
        case TWO:
            name = "two";
            break;
        case THREE:
            name = "three";
            break;
        case FOUR:
            name = "four";
            break;
        case FIVE:
            name = "five";
            break;
        case SIX:
            name = "six";
            break;
        case SEVEN:
            name = "seven";
            break;
        case EIGHT:
            name = "eight";
            break;
        case NINE:
            name = "nine";
            break;
        case TEN:
            name = "ten";
            break;
        case JACK:
            name = "jack";
            break;
        case QUEEN:
            name = "queen";
            break;
        case KING:
            name = "king";
            break;
        case ACE:
            name = "ace";
            break;
        case JOKER:
            name = "joker";
            break;
    };

    switch(m_suit) {
        case SPADES:
            name += "_spades";
            break;
        case CLUBS:
            name += "_clubs";
            break;
        case HEARTS:
            name += "_hearts";
            break;
        case DIAMONDS:
            name += "_diamonds";
            break;
    };

    if (m_rank == TWO) {
        name += "_wild";
    }

    return name;
}

const uint8_t heart[] = {
    0b10111101,
    0b00011000,
    0b00000000,
    0b00000000,
    0b10000001,
    0b11000011,
    0b11100111,
    0b11111111,
};

const uint8_t diamond[] = {
    0b11100111,
    0b11000011,
    0b10000001,
    0b00000000,
    0b00000000,
    0b10000001,
    0b11000011,
    0b11100111,
};

const uint8_t spade[] = {
    0b11100111,
    0b11000011,
    0b10000001,
    0b00000000,
    0b00000000,
    0b10000001,
    0b11100111,
    0b10000001,
};

const uint8_t club[] = {
    0b11100111,
    0b11000011,
    0b11000011,
    0b00100100,
    0b00000000,
    0b00000000,
    0b11100111,
    0b10000001,
};

std::string Card::to_string_rank() const {
    std::string rank;
    if (m_rank >= JACK && m_rank <= ACE) {
        switch (m_rank) {
            case JACK:
                rank = "J";
                return std::string(rank);
            case QUEEN:
                rank = "Q";
                return std::string(rank);
            case KING:
                rank = "K";
                return std::string(rank);
            case ACE:
                rank = "A";
                return std::string(rank);
        };
    }

    return std::to_string(m_rank);
}

void Card::print_card() const {
    std::string rank = this->to_string_rank();
    std::string suit;

    switch(m_suit) {
        case SPADES:
            suit = u8"\u2660";
            break;
        case CLUBS:
            suit = u8"\u2663";
            break;
        case HEARTS:
            suit = u8"\u2665";
            break;
        case DIAMONDS:
            suit = u8"\u2666";;
            break;
    };

    std::cout << rank << suit << " ";

}

void Card::print_held() const {
    if (m_rank == TEN) {
        if (m_held || m_kept)
            std::cout << "*   ";

        else
            std::cout << "    ";

    } else {
        if (m_held || m_kept)
            std::cout << "*  ";

        else
            std::cout << "   ";

    }
}
