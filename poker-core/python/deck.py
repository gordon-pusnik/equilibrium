from random import choice
from card import Card
from hand import Hand

class Deck:
    def __init__(self, command_line = False):
        self.command_line = command_line
        self.faces = ("ace", "king", "queen", "jack", "ten", "nine", "eight", "seven", "six", "five", "four", "three", "two")
        self.suits = ("spades", "clubs", "hearts", "diamonds")
        self.shuffle()
        self.new_hand()

    def random_card(self):
        return choice(self.faces) + "_" + choice(self.suits)

    def shuffle(self):
        self.cards = []
        self.index = 0
        while len(self.cards) < 52:
            card = self.random_card()
            if card not in self.cards:
                self.cards.append(card)

        #self.verify()

    def next_card(self):
        card_name = self.cards[self.index]
        card = Card(card_name, self.command_line)
        self.index += 1
        return card

    def new_hand(self):
        self.hand = Hand(self)

    def draw_cards(self):
        self.hand.draw_cards(self)

    def verify(self):
        h2 = False
        d2 = False
        s2 = False
        c2 = False

        h3 = False
        d3 = False
        s3 = False
        c3 = False

        h4 = False
        d4 = False
        s4 = False
        c4 = False

        h5 = False
        d5 = False
        s5 = False
        c5 = False

        h6 = False
        d6 = False
        s6 = False
        c6 = False

        h7 = False
        d7 = False
        s7 = False
        c7 = False

        h8 = False
        d8 = False
        s8 = False
        c8 = False

        h9 = False
        d9 = False
        s9 = False
        c9 = False

        h10 = False
        d10 = False
        s10 = False
        c10 = False

        hj = False
        dj = False
        sj = False
        cj = False

        hq = False
        dq = False
        sq = False
        cq = False

        hk = False
        dk = False
        sk = False
        ck = False

        ha = False
        da = False
        sa = False
        ca = False

        for card in self.cards:
            print(card)

            if card == "two_hearts":
                if h2:
                    print("Duplicate - two_hearts")
                h2 = True
            elif card == "two_diamonds":
                if d2:
                    print("Duplicate - two_diamonds")
                d2 = True
            elif card == "two_spades":
                if s2:
                    print("Duplicate - two_spades")
                s2 = True
            elif card == "two_clubs":
                if c2:
                    print("Duplicate - two_clubs")
                c2 = True
            elif card == "three_hearts":
                if h3:
                    print("Duplicate - three_hearts")
                h3 = True
            elif card == "three_diamonds":
                if d3:
                    print("Duplicate - three_diamonds")
                d3 = True
            elif card == "three_spades":
                if s3:
                    print("Duplicate - three_spades")
                s3 = True
            elif card == "three_clubs":
                if c3:
                    print("Duplicate - three_clubs")
                c3 = True
            elif card == "four_hearts":
                if h4:
                    print("Duplicate - four_hearts")
                h4 = True
            elif card == "four_diamonds":
                if d4:
                    print("Duplicate - four_diamonds")
                d4 = True
            elif card == "four_spades":
                if s4:
                    print("Duplicate - four_spades")
                s4 = True
            elif card == "four_clubs":
                if c4:
                    print("Duplicate - four_clubs")
                c4 = True
            elif card == "five_hearts":
                if h5:
                    print("Duplicate - five_hearts")
                h5 = True
            elif card == "five_diamonds":
                if d5:
                    print("Duplicate - five_diamonds")
                d5 = True
            elif card == "five_spades":
                if s5:
                    print("Duplicate - five_spades")
                s5 = True
            elif card == "five_clubs":
                if c5:
                    print("Duplicate - five_clubs")
                c5 = True
            elif card == "six_hearts":
                if h6:
                    print("Duplicate - six_hearts")
                h6 = True
            elif card == "six_diamonds":
                if d6:
                    print("Duplicate - six_diamonds")
                d6 = True
            elif card == "six_spades":
                if s6:
                    print("Duplicate - six_spades")
                s6 = True
            elif card == "six_clubs":
                if c6:
                    print("Duplicate - six_clubs")
                c6 = True
            elif card == "seven_hearts":
                if h7:
                    print("Duplicate - seven_hearts")
                h7 = True
            elif card == "seven_diamonds":
                if d7:
                    print("Duplicate - seven_diamonds")
                d7 = True
            elif card == "seven_spades":
                if s7:
                    print("Duplicate - seven_spades")
                s7 = True
            elif card == "seven_clubs":
                if c7:
                    print("Duplicate - seven_clubs")
                c7 = True
            elif card == "eight_hearts":
                if h8:
                    print("Duplicate - eight_hearts")
                h8 = True
            elif card == "eight_diamonds":
                if d8:
                    print("Duplicate - eight_diamonds")
                d8 = True
            elif card == "eight_spades":
                if s8:
                    print("Duplicate - eight_spades")
                s8 = True
            elif card == "eight_clubs":
                if c8:
                    print("Duplicate - eight_clubs")
                c8 = True
            elif card == "nine_hearts":
                if h9:
                    print("Duplicate - nine_hearts")
                h9 = True
            elif card == "nine_diamonds":
                if d9:
                    print("Duplicate - nine_diamonds")
                d9 = True
            elif card == "nine_spades":
                if s9:
                    print("Duplicate - nine_spades")
                s9 = True
            elif card == "nine_clubs":
                if c9:
                    print("Duplicate - nine_clubs")
                c9 = True
            elif card == "ten_hearts":
                if h10:
                    print("Duplicate - ten_hearts")
                h10 = True
            elif card == "ten_diamonds":
                if d10:
                    print("Duplicate - ten_diamonds")
                d10 = True
            elif card == "ten_spades":
                if s10:
                    print("Duplicate - ten_spades")
                s10 = True
            elif card == "ten_clubs":
                if c10:
                    print("Duplicate - ten_clubs")
                c10 = True
            elif card == "jack_hearts":
                if hj:
                    print("Duplicate - jack_hearts")
                hj = True
            elif card == "jack_diamonds":
                if dj:
                    print("Duplicate - jack_diamonds")
                dj = True
            elif card == "jack_spades":
                if sj:
                    print("Duplicate - jack_spades")
                sj = True
            elif card == "jack_clubs":
                if cj:
                    print("Duplicate - jack_clubs")
                cj = True
            elif card == "queen_hearts":
                if hq:
                    print("Duplicate - queen_hearts")
                hq = True
            elif card == "queen_diamonds":
                if dq:
                    print("Duplicate - queen_diamonds")
                dq = True
            elif card == "queen_spades":
                if sq:
                    print("Duplicate - queen_spades")
                sq = True
            elif card == "queen_clubs":
                if cq:
                    print("Duplicate - queen_clubs")
                cq = True
            elif card == "king_hearts":
                if hk:
                    print("Duplicate - king_hearts")
                hk = True
            elif card == "king_diamonds":
                if dk:
                    print("Duplicate - king_diamonds")
                dk = True
            elif card == "king_spades":
                if sk:
                    print("Duplicate - king_spades")
                sk = True
            elif card == "king_clubs":
                if ck:
                    print("Duplicate - king_clubs")
                ck = True
            elif card == "ace_hearts":
                if ha:
                    print("Duplicate - ace_hearts")
                ha = True
            elif card == "ace_diamonds":
                if da:
                    print("Duplicate - ace_diamonds")
                da = True
            elif card == "ace_spades":
                if sa:
                    print("Duplicate - ace_spades")
                sa = True
            elif card == "ace_clubs":
                if ca:
                    print("Duplicate - ace_clubs")
                ca = True

        twos = False
        threes = False
        fours = False
        fives = False
        sixes = False
        sevens = False
        eights = False
        nines = False
        tens = False
        jacks = False
        queens = False
        kings = False
        aces = False

        if h2 and d2 and s2 and c2:
            twos = True
            print("Have twos")

        if h3 and d3 and s3 and c3:
            threes = True
            print("Have threes")

        if h4 and d4 and s4 and c4:
            fours = True
            print("Have fours")

        if h5 and d5 and s5 and c5:
            fives = True
            print("Have fives")

        if h6 and d6 and s6 and c6:
            sixes = True
            print("Have sixes")

        if h7 and d7 and s7 and c7:
            sevens = True
            print("Have sevens")

        if h8 and d8 and s8 and c8:
            eights = True
            print("Have eights")

        if h9 and d9 and s9 and c9:
            nines = True
            print("Have nines")

        if h10 and d10 and s10 and c10:
            tens = True
            print("Have tens")

        if hj and dj and sj and cj:
            jacks = True
            print("Have jacks")

        if hq and dq and sq and cq:
            queens = True
            print("Have queens")

        if hk and dk and sk and ck:
            kings = True
            print("Have kings")

        if ha and da and sa and ca:
            aces = True
            print("Have aces")

        if twos and threes and fours and fives and sixes and sevens and eights and nines and tens and jacks and queens and kings and aces:
            print("Deck verified complete")
