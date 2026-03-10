from card import Rank
from hand_type import HandType

def check_for_win(card1, card2, card3, card4, card5):
    return check_win_high_or_better(card1, card2, card3, card4, card5, Rank.JACK)

def check_win_high_or_better(card1, card2, card3, card4, card5, high):
    cards = [card1, card2, card3, card4, card5]
    cards = sorted(cards, key=lambda card: card.rank)

    for card in cards:
        card.set_kept(False)

    # Check for flush
    if cards[0].suit == cards[1].suit and \
       cards[1].suit == cards[2].suit and \
       cards[2].suit == cards[3].suit and \
       cards[3].suit == cards[4].suit:
        cards[0].set_kept(True)
        cards[1].set_kept(True)
        cards[2].set_kept(True)
        cards[3].set_kept(True)
        cards[4].set_kept(True)

        # What kind of flush
        if cards[0].rank == Rank.TEN and \
           cards[1].rank == Rank.JACK and \
           cards[2].rank == Rank.QUEEN and \
           cards[3].rank == Rank.KING and \
           cards[4].rank == Rank.ACE:
           return HandType.ROYALFLUSH
        elif cards[0].rank + 1 == cards[1].rank and \
             cards[1].rank + 1 == cards[2].rank and \
             cards[2].rank + 1 == cards[3].rank and \
             cards[3].rank + 1 == cards[4].rank:
                return HandType.STRAIGHTFLUSH
        elif cards[0].rank == Rank.TWO and \
             cards[1].rank == Rank.THREE and \
             cards[2].rank == Rank.FOUR and \
             cards[3].rank == Rank.FIVE and \
             cards[4].rank == Rank.ACE:
                return HandType.STRAIGHTFLUSH
        else:
            return HandType.FLUSH

    # Four of a kind
    if cards[0].rank == cards[1].rank and \
       cards[1].rank == cards[2].rank and \
       cards[2].rank == cards[3].rank:
        cards[0].set_kept(True)
        cards[1].set_kept(True)
        cards[2].set_kept(True)
        cards[3].set_kept(True)
        return HandType.FOUROFAKIND
    elif cards[1].rank == cards[2].rank and \
         cards[2].rank == cards[3].rank and \
         cards[3].rank == cards[4].rank:
        cards[1].set_kept(True)
        cards[2].set_kept(True)
        cards[3].set_kept(True)
        cards[4].set_kept(True)
        return HandType.FOUROFAKIND

    # Full house
    if cards[0].rank == cards[1].rank and \
       cards[1].rank == cards[2].rank and \
       cards[3].rank == cards[4].rank:
        cards[0].set_kept(True)
        cards[1].set_kept(True)
        cards[2].set_kept(True)
        cards[3].set_kept(True)
        cards[4].set_kept(True)
        return HandType.FULLHOUSE
    elif cards[0].rank == cards[1].rank and \
         cards[2].rank == cards[3].rank and \
         cards[3].rank == cards[4].rank:
        cards[0].set_kept(True)
        cards[1].set_kept(True)
        cards[2].set_kept(True)
        cards[3].set_kept(True)
        cards[4].set_kept(True)
        return HandType.FULLHOUSE

    # Straight
    if cards[0].rank + 1 == cards[1].rank and \
       cards[1].rank + 1 == cards[2].rank and \
       cards[2].rank + 1 == cards[3].rank and \
       cards[3].rank + 1 == cards[4].rank:
        cards[0].set_kept(True)
        cards[1].set_kept(True)
        cards[2].set_kept(True)
        cards[3].set_kept(True)
        cards[4].set_kept(True)
        return HandType.STRAIGHT
    elif cards[0].rank == Rank.TWO and \
         cards[1].rank == Rank.THREE and \
         cards[2].rank == Rank.FOUR and \
         cards[3].rank == Rank.FIVE and \
         cards[4].rank == Rank.ACE:
        cards[0].set_kept(True)
        cards[1].set_kept(True)
        cards[2].set_kept(True)
        cards[3].set_kept(True)
        cards[4].set_kept(True)
        return HandType.STRAIGHT

    # Three of a kind
    if cards[0].rank == cards[1].rank and \
       cards[1].rank == cards[2].rank:
        cards[0].set_kept(True)
        cards[1].set_kept(True)
        cards[2].set_kept(True)
        return HandType.THREEOFAKIND
    elif cards[1].rank == cards[2].rank and \
         cards[2].rank == cards[3].rank:
        cards[1].set_kept(True)
        cards[2].set_kept(True)
        cards[3].set_kept(True)
        return HandType.THREEOFAKIND
    elif cards[2].rank == cards[3].rank and \
         cards[3].rank == cards[4].rank:
        cards[2].set_kept(True)
        cards[3].set_kept(True)
        cards[4].set_kept(True)
        return HandType.THREEOFAKIND

    # Two pair
    if cards[0].rank == cards[1].rank and \
       cards[2].rank == cards[3].rank:
        cards[0].set_kept(True)
        cards[1].set_kept(True)
        cards[2].set_kept(True)
        cards[3].set_kept(True)
        return HandType.TWOPAIR
    elif cards[0].rank == cards[1].rank and \
         cards[2].rank == cards[4].rank:
        cards[0].set_kept(True)
        cards[1].set_kept(True)
        cards[2].set_kept(True)
        cards[4].set_kept(True)
        return HandType.TWOPAIR
    elif cards[0].rank == cards[1].rank and \
         cards[3].rank == cards[4].rank:
        cards[0].set_kept(True)
        cards[1].set_kept(True)
        cards[3].set_kept(True)
        cards[4].set_kept(True)
        return HandType.TWOPAIR
    elif cards[1].rank == cards[2].rank and \
         cards[3].rank == cards[4].rank:
        cards[1].set_kept(True)
        cards[2].set_kept(True)
        cards[3].set_kept(True)
        cards[4].set_kept(True)
        return HandType.TWOPAIR

    # High pair
    if cards[0].rank == cards[1].rank and \
       cards[0].rank >= high:
        cards[0].set_kept(True)
        cards[1].set_kept(True)
        return HandType.HIGHPAIR
    if cards[1].rank == cards[2].rank and \
       cards[1].rank >= high:
        cards[1].set_kept(True)
        cards[2].set_kept(True)
        return HandType.HIGHPAIR
    if cards[2].rank == cards[3].rank and \
       cards[2].rank >= high:
        cards[2].set_kept(True)
        cards[3].set_kept(True)
        return HandType.HIGHPAIR
    if cards[3].rank == cards[4].rank and \
       cards[3].rank >= high:
        cards[3].set_kept(True)
        cards[4].set_kept(True)
        return HandType.HIGHPAIR

    return HandType.NONE
