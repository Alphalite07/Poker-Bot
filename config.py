import os
from dotenv import load_dotenv
from pathlib import Path

# Force the exact absolute path to the .env file in this directory
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

# --- Bot Security & Setup ---
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
COMMAND_PREFIX = "!"

# --- Poker Game Balance Constants ---
STARTING_CHIPS = 1000
STRIP_MODE_ITEMS = 5
TURN_TIMEOUT_SECONDS = 30