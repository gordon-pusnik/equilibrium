from enum import IntEnum

class HandType(IntEnum):
    NONE = 0
    HIGHPAIR = 1
    TWOPAIR = 2
    THREEOFAKIND = 3
    STRAIGHT = 4
    FLUSH = 5
    FULLHOUSE = 6
    FOUROFAKIND = 7
    STRAIGHTFLUSH = 8
    ROYALFLUSH = 9
