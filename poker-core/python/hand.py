from hand_type import HandType

from autohold import auto_hold
from checkforwin import check_for_win
from card import Card

class Hand:
    def __init__(self, deck):
        self.card1 = deck.next_card()
        self.card2 = deck.next_card()
        self.card3 = deck.next_card()
        self.card4 = deck.next_card()
        self.card5 = deck.next_card()

        self.reveal()

    def to_console(self):
        print(self.card1.print_card() + self.card2.print_card() + self.card3.print_card() + self.card4.print_card() + self.card5.print_card())
        print(self.card1.print_held() + self.card2.print_held() + self.card3.print_held() + self.card4.print_held() + self.card5.print_held())

    def draw_cards(self, deck):
        if self.card1.is_held() == False:
            self.card1 = deck.next_card()

        if self.card2.is_held() == False:
            self.card2 = deck.next_card()

        if self.card3.is_held() == False:
            self.card3 = deck.next_card()

        if self.card4.is_held() == False:
            self.card4 = deck.next_card()

        if self.card5.is_held() == False:
            self.card5 = deck.next_card()

        self.reveal()

    def auto_hold(self, bet, engine="solver"):
        auto_hold(self.card1, self.card2, self.card3, self.card4, self.card5, bet, engine)

    def check_for_win(self, bet):
        winnings = 0
        match (check_for_win(self.card1, self.card2, self.card3, self.card4, self.card5)):
            case HandType.NONE:
                print("Win nothing")
            case HandType.HIGHPAIR:
                winnings = bet * 1
                print("Win high pair -", winnings)
            case HandType.TWOPAIR:
                winnings = bet * 2
                print("Win two pair -", winnings)
            case HandType.THREEOFAKIND:
                winnings = bet * 3
                print("Win three of a kind -", winnings)
            case HandType.STRAIGHT:
                winnings = bet * 4
                print("Win straight -", winnings)
            case HandType.FLUSH:
                winnings = bet * 6
                print("Win flush -", winnings)
            case HandType.FULLHOUSE:
                winnings = bet * 9
                print("Win full house -", winnings)
            case HandType.FOUROFAKIND:
                winnings = bet * 25
                print("Win four of a kind -", winnings)
            case HandType.STRAIGHTFLUSH:
                winnings = bet * 50
                print("Win straight flush -", winnings)
            case HandType.ROYALFLUSH:
                if bet == 5:
                    winnings = bet * 800
                else:
                    winnings = bet * 250
                print("Win royal flush -", winnings)

        return winnings

    def reveal(self):
        self.reset_held()
        self.card1.set_flipped(True)
        self.card2.set_flipped(True)
        self.card3.set_flipped(True)
        self.card4.set_flipped(True)
        self.card5.set_flipped(True)

    def reset_held(self):
        self.card1.set_held(False)
        self.card2.set_held(False)
        self.card3.set_held(False)
        self.card4.set_held(False)
        self.card5.set_held(False)

    def toggle_hold(self, card_num):
        if card_num == 1:
            self.card1.set_held(not self.card1.is_held())
        if card_num == 2:
            self.card2.set_held(not self.card2.is_held())
        if card_num == 3:
            self.card3.set_held(not self.card3.is_held())
        if card_num == 4:
            self.card4.set_held(not self.card4.is_held())
        if card_num == 5:
            self.card5.set_held(not self.card5.is_held())
