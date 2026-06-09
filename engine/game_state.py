from .card import Deck
from .evaluator import PokerEvaluator
from .pot_manager import PotManager

class PokerPlayer:
    def __init__(self, user_id, name, chips=1000):
        self.user_id = user_id
        self.name = name
        self.chips = chips
        self.clothing_items = 5
        self.hand = []
        self.current_bet = 0
        self.has_folded = False
        self.has_acted = False

class AdvancedPokerGame:
    def __init__(self, channel_id, mode="texas_holdem"):
        self.channel_id = channel_id
        self.mode = mode
        self.players = []
        self.deck = Deck()
        self.community_cards = []
        self.active_pots = []
        self.total_pot_visual = 0
        self.current_bet_level = 0
        self.current_player_idx = 0
        self.round_phase = "PREFLOP"

    def add_player(self, user_id, name):
        if any(p.user_id == user_id for p in self.players): return False
        self.players.append(PokerPlayer(user_id, name))
        return True

    def start_game(self):
        if len(self.players) < 2: return False
        self.deck = Deck()
        self.community_cards = []
        self.active_pots = []
        self.total_pot_visual = 0
        cards_to_deal = 4 if self.mode == "omaha" else 2
        for p in self.players:
            p.hand = self.deck.deal(cards_to_deal)
            p.has_folded = False
            p.current_bet = 0
            p.has_acted = False
        self.round_phase = "PREFLOP"
        self.current_player_idx = 0
        return True

    @property
    def current_player(self):
        return self.players[self.current_player_idx]

    def check_phase_complete(self):
        active_players = [p for p in self.players if not p.has_folded]
        if len(active_players) == 1: return True # Everyone else folded
        for p in active_players:
            if not p.has_acted or p.current_bet < self.current_bet_level:
                if p.chips > 0: return False # Still needs to act
        return True

    def advance_phase(self):
        pots = PotManager.calculate_pots(self.players)
        self.active_pots.extend(pots)
        for p in self.players:
            p.current_bet = 0
            p.has_acted = False
        self.current_bet_level = 0

        phases = ["PREFLOP", "FLOP", "TURN", "RIVER", "SHOWDOWN"]
        idx = phases.index(self.round_phase)
        
        if idx < len(phases) - 1:
            self.round_phase = phases[idx + 1]
            if self.round_phase == "FLOP": self.community_cards.extend(self.deck.deal(3))
            elif self.round_phase in ["TURN", "RIVER"]: self.community_cards.extend(self.deck.deal(1))

        self.current_player_idx = 0
        while self.players[self.current_player_idx].has_folded:
            self.current_player_idx = (self.current_player_idx + 1) % len(self.players)

    def next_turn(self):
        if self.check_phase_complete():
            self.advance_phase()
            return None
        while True:
            self.current_player_idx = (self.current_player_idx + 1) % len(self.players)
            if not self.players[self.current_player_idx].has_folded:
                break
        return self.current_player

    def process_showdown(self):
        active = [p for p in self.players if not p.has_folded]
        if len(active) == 1:
            winner = active[0]
            winner.chips += self.total_pot_visual
            return f"🏆 **{winner.name}** wins {self.total_pot_visual} by default (everyone folded)!"

        player_scores = [(p, PokerEvaluator.find_best_hand(p.hand, self.community_cards, self.mode)) for p in active]
        player_scores.sort(key=lambda x: (x[1][0], x[1][1]), reverse=True)
        winner = player_scores[0][0]
        
        winner.chips += self.total_pot_visual
        result = f"🏆 **{winner.name}** wins a total of **{self.total_pot_visual} chips** at showdown!"
        
        if self.mode == "strip":
            for p in active:
                if p != winner:
                    p.clothing_items -= 1
                    result += f"\n📉 👙 **{p.name}** lost the hand and removed an item! ({p.clothing_items} items left)"
                    if p.clothing_items <= 0: result += f"\n🚨 **{p.name}** is entirely stripped!"
        return result