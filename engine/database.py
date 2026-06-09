import sqlite3

class DatabaseManager:
    def __init__(self, db_path="poker_data.db"):
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self._build_tables()

    def _build_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS players (
                user_id TEXT PRIMARY KEY,
                chips INTEGER,
                wardrobe_items INTEGER
            )
        ''')
        # Safely upgrade the existing database to include daily tracking without data loss
        try:
            self.cursor.execute('ALTER TABLE players ADD COLUMN last_daily REAL DEFAULT 0.0')
        except sqlite3.OperationalError:
            pass # Column already exists, safe to ignore
        self.conn.commit()

    def load_player(self, user_id, starting_chips=1000):
        self.cursor.execute('SELECT chips, wardrobe_items FROM players WHERE user_id = ?', (str(user_id),))
        result = self.cursor.fetchone()
        if result:
            return result[0], result[1] 
        else:
            self.cursor.execute(
                'INSERT INTO players (user_id, chips, wardrobe_items, last_daily) VALUES (?, ?, ?, 0.0)',
                (str(user_id), starting_chips, 5)
            )
            self.conn.commit()
            return starting_chips, 5

    def save_player(self, user_id, chips, wardrobe_items):
        self.cursor.execute(
            'UPDATE players SET chips = ?, wardrobe_items = ? WHERE user_id = ?',
            (chips, wardrobe_items, str(user_id))
        )
        self.conn.commit()

    def claim_daily(self, user_id, current_time):
        # Ensure player exists in DB first
        self.load_player(user_id)
        
        self.cursor.execute('SELECT last_daily FROM players WHERE user_id = ?', (str(user_id),))
        last_daily = self.cursor.fetchone()[0] or 0.0
        
        time_since = current_time - last_daily
        if time_since >= 86400: # 86400 seconds = 24 hours
            self.cursor.execute(
                'UPDATE players SET chips = chips + 500, last_daily = ? WHERE user_id = ?',
                (current_time, str(user_id))
            )
            self.conn.commit()
            return True, 0
        else:
            return False, 86400 - time_since