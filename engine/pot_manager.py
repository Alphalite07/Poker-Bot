class PotManager:
    @staticmethod
    def calculate_pots(players):
        """
        Calculates main and side pots based on player investments.
        Returns a list of dicts: [{'amount': int, 'eligible': [Player]}]
        """
        # Isolate players who actually put chips in this round
        invested_players = [p for p in players if p.current_bet > 0]
        if not invested_players:
            return []

        # Sort from lowest bet to highest bet to find all-in thresholds
        invested_players.sort(key=lambda p: p.current_bet)
        
        pots = []
        current_baseline = 0
        
        for i, player in enumerate(invested_players):
            # Calculate the marginal difference this player added
            contribution = player.current_bet - current_baseline
            
            if contribution > 0:
                # Multiply this contribution by everyone who matched it
                pot_amount = contribution * len(invested_players[i:])
                
                # Only players who haven't folded can win this specific sub-pot
                eligible_players = [p for p in invested_players[i:] if not p.has_folded]
                
                if pot_amount > 0:
                    pots.append({
                        "amount": pot_amount,
                        "eligible": eligible_players
                    })
                    
                # Raise the baseline for the next side pot calculation
                current_baseline += contribution
                
        return pots

    @staticmethod
    def distribute_winnings(pots, evaluated_players):
        """
        evaluated_players: list of tuples (Player, rank_score) sorted highest to lowest
        """
        payout_log = []
        
        for pot in pots:
            if not pot['eligible']:
                continue # If everyone eligible folded, logic passes to remainder
                
            # Find the highest score among players eligible for *this specific pot*
            eligible_winners = [p for p, score in evaluated_players if p in pot['eligible']]
            
            if eligible_winners:
                # Handle split pots if hands tie
                winner = eligible_winners[0] 
                winner.chips += pot['amount']
                payout_log.append(f"💰 {winner.name} takes a side pot of {pot['amount']} chips!")
                
        return payout_log