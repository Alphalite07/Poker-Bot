import sqlite3
import json

class DatabaseManager:
    def __init__(self, db_path="poker_data.db"):
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self._build_tables()

    def _build_tables(self):
        # 1. Base Players Table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS players (
                user_id TEXT PRIMARY KEY,
                chips INTEGER,
                wardrobe_items INTEGER,
                last_daily REAL DEFAULT 0.0,
                inventory TEXT DEFAULT '[]'
            )
        ''')
        
        # 2. Custom Match Predictions Table (Polymarket type)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS custom_predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                creator_id TEXT,
                question TEXT,
                option_a TEXT,
                option_b TEXT,
                pool_a INTEGER DEFAULT 0,
                pool_b INTEGER DEFAULT 0,
                status TEXT DEFAULT 'OPEN'
            )
        ''')

        # 3. User Prediction Wagers Table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS prediction_wagers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prediction_id INTEGER,
                user_id TEXT,
                user_name TEXT,
                chosen_option TEXT,
                amount INTEGER
            )
        ''')
        self.conn.commit()

    def load_player(self, user_id, starting_chips=1000):
        self.cursor.execute('SELECT chips, wardrobe_items, inventory FROM players WHERE user_id = ?', (str(user_id),))
        result = self.cursor.fetchone()
        if result:
            return result[0], result[1], json.loads(result[2])
        else:
            self.cursor.execute(
                'INSERT INTO players (user_id, chips, wardrobe_items, last_daily, inventory) VALUES (?, ?, ?, 0.0, "[]")',
                (str(user_id), starting_chips, 5)
            )
            self.conn.commit()
            return starting_chips, 5, []

    def save_inventory(self, user_id, inventory_list):
        self.cursor.execute('UPDATE players SET inventory = ? WHERE user_id = ?', (json.dumps(inventory_list), str(user_id)))
        self.conn.commit()

    # --- Custom Prediction Market Core ---
    def create_match(self, creator_id, question, opt_a, opt_b):
        self.cursor.execute(
            'INSERT INTO custom_predictions (creator_id, question, option_a, option_b) VALUES (?, ?, ?, ?)',
            (str(creator_id), question, opt_a, opt_b)
        )
        self.conn.commit()
        return self.cursor.lastrowid

    def place_match_wager(self, user_id, user_name, match_id, option, amount):
        # Verify match is open
        self.cursor.execute('SELECT status, option_a, option_b FROM custom_predictions WHERE id = ?', (match_id,))
        match = self.cursor.fetchone()
        if not match or match[0] != 'OPEN': return "CLOSED"
        
        chosen_clean = "A" if option.lower() in [match[1].lower(), 'a'] else "B"
        
        # Verify chips
        self.load_player(user_id)
        self.cursor.execute('SELECT chips FROM players WHERE user_id = ?', (str(user_id),))
        chips = self.cursor.fetchone()[0]
        if chips < amount: return "NO_CHIPS"

        # Deduct chips and log wager
        self.cursor.execute('UPDATE players SET chips = chips - ? WHERE user_id = ?', (amount, str(user_id)))
        if chosen_clean == "A":
            self.cursor.execute('UPDATE custom_predictions SET pool_a = pool_a + ? WHERE id = ?', (amount, match_id))
        else:
            self.cursor.execute('UPDATE custom_predictions SET pool_b = pool_b + ? WHERE id = ?', (amount, match_id))
            
        self.cursor.execute(
            'INSERT INTO prediction_wagers (prediction_id, user_id, user_name, chosen_option, amount) VALUES (?, ?, ?, ?, ?)',
            (match_id, str(user_id), user_name, chosen_clean, amount)
        )
        self.conn.commit()
        return "SUCCESS"

    def resolve_match(self, match_id, winning_letter):
        self.cursor.execute('SELECT status, pool_a, pool_b, question, option_a, option_b FROM custom_predictions WHERE id = ?', (match_id,))
        match = self.cursor.fetchone()
        if not match or match[0] != 'OPEN': return None

        pool_a, pool_b, question, opt_a, opt_b = match[1], match[2], match[3], match[4], match[5]
        total_pool = pool_a + pool_b
        winning_letter = winning_letter.upper()
        winning_pool = pool_a if winning_letter == "A" else pool_b
        winning_text = opt_a if winning_letter == "A" else opt_b

        if total_pool == 0:
            self.cursor.execute('UPDATE custom_predictions SET status = "RESOLVED" WHERE id = ?', (match_id,))
            self.conn.commit()
            return f"🏁 Market `{question}` resolved. No wagers were placed."

        # Payout report assembly
        report = f"🏁 **Prediction Market Resolved!**\nMatch: **{question}**\nWinner: 🎉 **{winning_text}**\nTotal Pool: 🪙 `{total_pool}`\n\n"
        
        self.cursor.execute('SELECT user_id, user_name, amount, chosen_option FROM prediction_wagers WHERE prediction_id = ?', (match_id,))
        wagers = self.cursor.fetchall()

        if winning_pool == 0:
            report += "No users guessed correctly. The house keeps the pool!"
        else:
            for u_id, name, amount, chosen in wagers:
                if chosen == winning_letter:
                    share_ratio = amount / winning_pool
                    payout = int(share_ratio * total_pool)
                    self.cursor.execute('UPDATE players SET chips = chips + ? WHERE user_id = ?', (payout, str(u_id)))
                    report += f"💰 **{name}** collected 🪙 `{payout}` chips! (Bet `{amount}`)\n"

        self.cursor.execute('UPDATE custom_predictions SET status = "RESOLVED" WHERE id = ?', (match_id,))
        self.conn.commit()
        return report