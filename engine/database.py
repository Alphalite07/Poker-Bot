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
        self.conn.commit()

    def load_player(self, user_id, starting_chips=1000):
        self.cursor.execute('SELECT chips, wardrobe_items FROM players WHERE user_id = ?', (str(user_id),))
        result = self.cursor.fetchone()
        if result:
            return result[0], result[1] 
        else:
            self.cursor.execute(
                'INSERT INTO players (user_id, chips, wardrobe_items) VALUES (?, ?, ?)',
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