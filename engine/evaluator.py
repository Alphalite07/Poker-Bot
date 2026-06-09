from itertools import combinations

HAND_RANKS = {
    "ROYAL_FLUSH": 10, "STRAIGHT_FLUSH": 9, "FOUR_OF_A_KIND": 8,
    "FULL_HOUSE": 7, "FLUSH": 6, "STRAIGHT": 5, "THREE_OF_A_KIND": 4,
    "TWO_PAIR": 3, "PAIR": 2, "HIGH_CARD": 1
}

class PokerEvaluator:
    @staticmethod
    def evaluate_5_cards(cards):
        ranks = sorted(['2345678910JQKA'.index(c.rank) for c in cards], reverse=True)
        suits = [c.suit for c in cards]
        is_flush = len(set(suits)) == 1
        
        unique_ranks = sorted(list(set(ranks)), reverse=True)
        is_straight = False
        if len(unique_ranks) >= 5:
            if unique_ranks[0] - unique_ranks[4] == 4: is_straight = True
            elif unique_ranks == [12, 3, 2, 1, 0]: 
                is_straight = True
                ranks = [3, 2, 1, 0, -1] 
                
        counts = {r: ranks.count(r) for r in ranks}
        count_values = sorted(counts.values(), reverse=True)
        
        if is_flush and is_straight:
            if ranks[0] == 12 and ranks[4] == 8: return (HAND_RANKS["ROYAL_FLUSH"], ranks)
            return (HAND_RANKS["STRAIGHT_FLUSH"], ranks)
        if count_values == [4, 1]: return (HAND_RANKS["FOUR_OF_A_KIND"], [[r for r, c in counts.items() if c == 4][0]])
        if count_values == [3, 2]: return (HAND_RANKS["FULL_HOUSE"], [[r for r, c in counts.items() if c == 3][0]])
        if is_flush: return (HAND_RANKS["FLUSH"], ranks)
        if is_straight: return (HAND_RANKS["STRAIGHT"], ranks)
        if count_values == [3, 1, 1]: return (HAND_RANKS["THREE_OF_A_KIND"], [[r for r, c in counts.items() if c == 3][0]])
        if count_values == [2, 2, 1]:
            pairs = sorted([r for r, c in counts.items() if c == 2], reverse=True)
            kicker = [r for r, c in counts.items() if c == 1][0]
            return (HAND_RANKS["TWO_PAIR"], pairs + [kicker])
        if count_values == [2, 1, 1, 1]:
            pair = [r for r, c in counts.items() if c == 2][0]
            kickers = sorted([r for r, c in counts.items() if c == 1], reverse=True)
            return (HAND_RANKS["PAIR"], [pair] + kickers)
        return (HAND_RANKS["HIGH_CARD"], ranks)

    @classmethod
    def find_best_hand(cls, hole_cards, community_cards, mode="texas_holdem"):
        all_cards = hole_cards + community_cards
        best_rank = (0, [])
        if mode in ["texas_holdem", "strip"]:
            for combo in combinations(all_cards, 5):
                rank = cls.evaluate_5_cards(combo)
                if rank > best_rank: best_rank = rank
        elif mode == "omaha":
            for hole_combo in combinations(hole_cards, 2):
                for comm_combo in combinations(community_cards, 3):
                    rank = cls.evaluate_5_cards(list(hole_combo) + list(comm_combo))
                    if rank > best_rank: best_rank = rank
        return best_rank