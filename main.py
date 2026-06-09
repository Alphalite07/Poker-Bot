import config
import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

# Load environment variables securely
load_dotenv()

class PokerBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        print("⚙️ Loading Poker Cog...")
        await self.load_extension("cogs.poker_cog")
        print("✅ Core systems online.")

bot = PokerBot()

@bot.event
async def on_ready():
    print(f"🔥 Real-time Poker Core Online. Authenticated as: {bot.user}")

if __name__ == "__main__":
    # Update these two lines to include 'TOKEN'
    if not config.DISCORD_TOKEN:
        print("❌ ERROR: DISCORD_TOKEN not found in .env file.")
    else:
        bot.run(config.DISCORD_TOKEN)