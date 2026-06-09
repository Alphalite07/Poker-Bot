class PotManager:
    @staticmethod
    def calculate_pots(players):
        invested_players = [p for p in players if p.current_bet > 0]
        if not invested_players: return []
        invested_players.sort(key=lambda p: p.current_bet)
        pots = []
        current_baseline = 0
        for i, player in enumerate(invested_players):
            contribution = player.current_bet - current_baseline
            if contribution > 0:
                pot_amount = contribution * len(invested_players[i:])
                eligible_players = [p for p in invested_players[i:] if not p.has_folded]
                if pot_amount > 0:
                    pots.append({"amount": pot_amount, "eligible": eligible_players})
                current_baseline += contribution
        return pots