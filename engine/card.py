import random

SUITS = {'♠': 'spades', '♥': 'hearts', '♦': 'diamonds', '♣': 'clubs'}
SUIT_EMOJIS = {'♠': '♠️', '♥': '♥️', '♦': '♦️', '♣': '♣️'}
RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']

class Card:
    def __init__(self, rank, suit):
        self.rank = rank
        self.suit = suit
    def __str__(self):
        return f"{self.rank}{SUIT_EMOJIS[self.suit]}"

class Deck:
    def __init__(self):
        self.cards = [Card(r, s) for r in RANKS for s in SUITS]
        random.shuffle(self.cards)
    def deal(self, num):
        return [self.cards.pop() for _ in range(num)]

class CardArt:
    @staticmethod
    def render(cards):
        if not cards: return "```\n[ No Cards Dealt ]\n```"
        ascii_art = ["", "", "", "", ""]
        for c in cards:
            r_top = c.rank.ljust(2) 
            r_bot = c.rank.rjust(2)
            s = SUIT_EMOJIS.get(c.suit, c.suit)
            ascii_art[0] += " ╭──────╮ "
            ascii_art[1] += f" │ {r_top}   │ "
            ascii_art[2] += f" │   {s}  │ "
            ascii_art[3] += f" │   {r_bot} │ "
            ascii_art[4] += " ╰──────╯ "
        return "```text\n" + "\n".join(ascii_art) + "\n```"