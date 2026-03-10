#ifndef __CHECKFORWIN_H__
#define __CHECKFORWIN_H__

#include <cstdint>
#include <array>

class Card;

namespace CheckForWin {
    uint32_t check_for_win(const std::array<Card*, 5>& cards);
    uint32_t check_high_or_better(const std::array<Card*, 5>& cards, uint32_t high);
}

#endif // __CHECKFORWIN_H__
