from enum import IntEnum

class Suit(IntEnum):
    SPADES = 1
    CLUBS = 2
    HEARTS = 3
    DIAMONDS = 4

class Rank(IntEnum):
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5
    SIX = 6
    SEVEN = 7
    EIGHT = 8
    NINE = 9
    TEN = 10
    JACK= 11
    QUEEN = 12
    KING = 13
    ACE = 14

class Card:
    def __init__(self, name, command_line):
        #print("Card init", name)
        self.command_line = command_line
        self.name = name
        self.flipped = False
        self.held = False
        self.kept = False
        self.width = 0
        self.height = 0
        self.held_alpha_up = False

        name_lower = self.name.lower()
        if "hearts" in name_lower:
            self.suit = Suit.HEARTS
            suit_str = "hearts"
        elif "diamonds" in name_lower:
            self.suit = Suit.DIAMONDS
            suit_str = "diamonds"
        elif "spades" in name_lower:
            self.suit = Suit.SPADES
            suit_str = "spades"
        elif "clubs" in name_lower:
            self.suit = Suit.CLUBS
            suit_str = "clubs"

        # Split by underscore or just take the prefix before the suit
        if "_" in name_lower:
            self.rank = name_lower.split("_")[0]
        else:
            pos = name_lower.find(suit_str)
            if pos != -1:
                self.rank = name_lower[0:pos]

        rank_map = {
            "two": Rank.TWO, "three": Rank.THREE, "four": Rank.FOUR, "five": Rank.FIVE,
            "six": Rank.SIX, "seven": Rank.SEVEN, "eight": Rank.EIGHT, "nine": Rank.NINE,
            "ten": Rank.TEN, "jack": Rank.JACK, "queen": Rank.QUEEN, "king": Rank.KING,
            "ace": Rank.ACE
        }
        
        # Handle original CamelCase as well if passed
        self.rank = rank_map.get(self.rank.lower(), self.rank)

    def get_name(self):
        return self.name

    def set_flipped(self, flipped):
        self.flipped = flipped

    def set_held(self, held):
        self.held = held

    def set_kept(self, kept):
        self.kept = kept

    def is_held(self):
        return self.held

    def is_kept(self):
        return self.kept

    def print_card(self):
        rank = '0'
        suit = '0'
        match (self.rank):
            case Rank.TWO:
                rank = '2'
            case Rank.THREE:
                rank = '3'
            case Rank.FOUR:
                rank = '4'
            case Rank.FIVE:
                rank = '5'
            case Rank.SIX:
                rank = '6'
            case Rank.SEVEN:
                rank = '7'
            case Rank.EIGHT:
                rank = '8'
            case Rank.NINE:
                rank = '9'
            case Rank.TEN:
                rank = '10'
            case Rank.JACK:
                rank = 'J'
            case Rank.QUEEN:
                rank = 'Q'
            case Rank.KING:
                rank = 'K'
            case Rank.ACE:
                rank = 'A'

        match (self.suit):
            case Suit.HEARTS:
                suit = '\u2665'
            case Suit.DIAMONDS:
                suit = '\u2666'
            case Suit.SPADES:
                suit = '\u2660'
            case Suit.CLUBS:
                suit = '\u2663'

        return rank + suit + ' '

    def print_held(self):
        if self.rank == Rank.TEN:
            if self.held or self.kept:
                return '*   '
            else:
                return '    '
        else:
            if self.held or self.kept:
                return '*  '
            else:
                return '   '
