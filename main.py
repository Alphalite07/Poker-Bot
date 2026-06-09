import discord
from discord.ext import commands
import config

class PokerBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix=config.COMMAND_PREFIX, intents=intents)

    async def setup_hook(self):
        print("⚙️ Loading Poker Cog...")
        await self.load_extension("cogs.poker_cog")
        print("✅ Core systems online.")

bot = PokerBot()

@bot.event
async def on_ready():
    print(f"🔥 Real-time Poker Core Online. Authenticated as: {bot.user}")

if __name__ == "__main__":
    if not config.DISCORD_TOKEN:
        print("❌ ERROR: DISCORD_TOKEN not found in .env file.")
    else:
        bot.run(config.DISCORD_TOKEN)