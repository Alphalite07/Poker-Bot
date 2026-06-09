import discord
from discord.ext import commands
import asyncio
from engine.game_state import AdvancedPokerGame
from engine.card import CardArt
from engine.database import DatabaseManager

class RaiseModal(discord.ui.Modal, title='Raise Amount'):
    amount = discord.ui.TextInput(
        label='Enter chips to raise',
        style=discord.TextStyle.short,
        placeholder='e.g., 100',
        required=True
    )

    def __init__(self, view):
        super().__init__()
        self.view = view

    async def on_submit(self, interaction: discord.Interaction):
        try:
            val = int(self.amount.value)
            player = self.view.game.current_player
            if val > player.chips:
                return await interaction.response.send_message("Not enough chips!", ephemeral=True)
            
            player.chips -= val
            player.current_bet += val
            self.view.game.total_pot_visual += val
            self.view.game.current_bet_level = max(self.view.game.current_bet_level, player.current_bet)
            player.has_acted = True
            
            self.view.game.next_turn()
            await interaction.response.defer()
            await self.view.render_table(interaction)
        except ValueError:
            await interaction.response.send_message("Invalid number.", ephemeral=True)

class HelpDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label='Commands', description='List of all bot commands', emoji='⌨️'),
            discord.SelectOption(label='Game Modes', description='Texas Holdem, Omaha, Strip', emoji='🕹️'),
            discord.SelectOption(label='Hand Rankings', description='What beats what at showdown?', emoji='🏆')
        ]
        super().__init__(placeholder='Choose a help category...', min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        embed = discord.Embed(color=0x1f8b4c)
        
        if self.values[0] == 'Commands':
            embed.title = "⌨️ Bot Commands"
            embed.description = (
                "`!poker_create [mode]` - Initializes a new lobby.\n"
                "`!join` - Take a seat at the active table.\n"
                "`!start` - Deals the hole cards and starts the loop.\n"
                "`!help` - Opens this interactive menu."
            )
        elif self.values[0] == 'Game Modes':
            embed.title = "🕹️ Game Modes"
            embed.description = (
                "**texas_holdem:** The classic. 2 hole cards, 5 community cards.\n\n"
                "**omaha:** 4 hole cards. You MUST use exactly 2 of your hole cards and 3 community cards to make a hand.\n\n"
                "**strip:** (18+) Losers remove an item from their visual wardrobe. Requires an age-restricted NSFW channel."
            )
        elif self.values[0] == 'Hand Rankings':
            embed.title = "🏆 Poker Hand Rankings"
            embed.description = (
                "**1.** Royal Flush\n"
                "**2.** Straight Flush\n"
                "**3.** Four of a Kind\n"
                "**4.** Full House\n"
                "**5.** Flush\n"
                "**6.** Straight\n"
                "**7.** Three of a Kind\n"
                "**8.** Two Pair\n"
                "**9.** One Pair\n"
                "**10.** High Card"
            )
            
        # Edit the message with the new selected category
        await interaction.response.edit_message(embed=embed)

class HelpView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)
        self.add_item(HelpDropdown())

class AnimatedPokerView(discord.ui.View):
    def __init__(self, game):
        super().__init__(timeout=300)
        self.game = game

    async def render_table(self, ctx_or_interaction):
        if self.game.round_phase == "SHOWDOWN":
            result = self.game.process_showdown()
            embed = discord.Embed(title="🏁 SHOWDOWN 🏁", description=result, color=0xffd700)
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.message.edit(embed=embed, view=None)
            else:
                await ctx_or_interaction.send(embed=embed)
            return

        is_interaction = isinstance(ctx_or_interaction, discord.Interaction)
        table_art = CardArt.render(self.game.community_cards)
        
        stack_count = min(max(1, self.game.total_pot_visual // 100), 10) if self.game.total_pot_visual > 0 else 0
        pot_visual = "🪙" * stack_count
        
        embed = discord.Embed(title=f"🟩 {self.game.mode.upper()} - {self.game.round_phase} 🟩", color=0x1f8b4c)
        embed.add_field(name="Community Felt", value=table_art, inline=False)
        embed.add_field(name="Total Pot", value=f"{pot_visual} `{self.game.total_pot_visual}`", inline=True)
        embed.add_field(name="Call Amount", value=f"💰 `{self.game.current_bet_level}`", inline=True)
        
        player_status = []
        for p in self.game.players:
            asset = f"👕 x{p.clothing_items}" if self.game.mode == "strip" else f"🪙 {p.chips}"
            marker = "➡️ 🟢" if p == self.game.current_player else "⚪"
            if p.has_folded: marker = "❌"
            player_status.append(f"{marker} **{p.name}** | {asset} | Bet: `{p.current_bet}`")
            
        embed.add_field(name="Table Roster", value="\n".join(player_status), inline=False)
        
        if is_interaction:
            await ctx_or_interaction.message.edit(embed=embed, view=self)
        else:
            await ctx_or_interaction.send(embed=embed, view=self)

    @discord.ui.button(label="Call / Check", style=discord.ButtonStyle.success)
    async def call_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.game.current_player.user_id:
            return await interaction.response.send_message("Not your turn!", ephemeral=True)
        
        p = self.game.current_player
        to_call = self.game.current_bet_level - p.current_bet
        actual_call = min(to_call, p.chips) 
        
        p.chips -= actual_call
        p.current_bet += actual_call
        self.game.total_pot_visual += actual_call
        p.has_acted = True
        
        self.game.next_turn()
        await interaction.response.defer()
        await self.render_table(interaction)

    @discord.ui.button(label="Raise", style=discord.ButtonStyle.primary)
    async def raise_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.game.current_player.user_id:
            return await interaction.response.send_message("Not your turn!", ephemeral=True)
        await interaction.response.send_modal(RaiseModal(self))

    @discord.ui.button(label="Fold", style=discord.ButtonStyle.danger)
    async def fold_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.game.current_player.user_id:
            return await interaction.response.send_message("Not your turn!", ephemeral=True)
        
        self.game.current_player.has_folded = True
        self.game.next_turn()
        active = [p for p in self.game.players if not p.has_folded]
        if len(active) == 1:
            self.game.round_phase = "SHOWDOWN"
            
        await interaction.response.defer()
        await self.render_table(interaction)

class PokerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.games = {}
        self.db = DatabaseManager()

    @commands.command(name="balance", aliases=["bal", "stats", "chips"])
    async def balance(self, ctx):
        # 1. Pull their permanent stats from SQLite
        chips, wardrobe = self.db.load_player(ctx.author.id)
        
        # 2. Build a polished player ID card
        embed = discord.Embed(
            title=f"🏦 Casino Vault",
            description=f"Player record for **{ctx.author.display_name}**",
            color=0xffd700 # Shiny gold
        )
        
        # Grab the user's profile picture dynamically
        if ctx.author.display_avatar:
            embed.set_thumbnail(url=ctx.author.display_avatar.url)
            
        embed.add_field(name="Total Chips", value=f"🪙 `{chips}`", inline=True)
        embed.add_field(name="Wardrobe Items", value=f"👕 `{wardrobe} / 5`", inline=True)
        
        await ctx.send(embed=embed)

    @commands.command(name="help")
    async def custom_help(self, ctx):
        embed = discord.Embed(
            title="🃏 Advanced Poker Engine Help",
            description="Welcome to the high-stakes table! Use the dropdown menu below to navigate the rules, modes, and commands.",
            color=0x2b2d31
        )
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/186/186323.png")
        
        view = HelpView()
        await ctx.send(embed=embed, view=view)

    @commands.command(name="poker_create")
    async def poker_create(self, ctx, mode="texas_holdem"):
        if mode == "strip" and not ctx.channel.is_nsfw():
            return await ctx.send("❌ Mature modes can only be initialized in NSFW channels.")
        if mode not in ["texas_holdem", "omaha", "strip"]:
            return await ctx.send("Modes: `texas_holdem`, `omaha`, `strip`")
        
        self.games[ctx.channel.id] = AdvancedPokerGame(ctx.channel.id, mode)
        await ctx.send(f"♣️ A new game of **{mode}** is open! Type `!join` to sit down.")

    @commands.command(name="join")
    async def join(self, ctx):
        game = self.games.get(ctx.channel.id)
        if not game: return await ctx.send("No game running here. Use `!poker_create`.")
        if game.add_player(ctx.author.id, ctx.author.display_name):
            await ctx.send(f"🎟️ **{ctx.author.display_name}** joined the table.")
        else:
            await ctx.send("You are already seated!")

    @commands.command(name="start")
    async def start(self, ctx):
        game = self.games.get(ctx.channel.id)
        if not game or not game.start_game():
            return await ctx.send("Cannot start. Need at least 2 players.")
        
        for p in game.players:
            user = await self.bot.fetch_user(p.user_id)
            hand_str = " ".join([str(c) for c in p.hand])
            try:
                await user.send(f"🎴 Your hole cards in #{ctx.channel.name}: {hand_str}")
            except discord.Forbidden:
                await ctx.send(f"⚠️ Could not DM {p.name}. Ensure DMs are open!")
        
        anim_msg = await ctx.send("🪙 **Shuffling the deck...**")
        await asyncio.sleep(1)
        frames = ["| 🎴          |", "|   🎴        |", "|     🎴      |", "|       🎴    |", "|         🎴  |"]
        for _ in range(2): 
            for frame in frames:
                await anim_msg.edit(content=f"🃏 **Pitching hole cards...**\n`{frame}`")
                await asyncio.sleep(0.2) 
                
        await anim_msg.delete()
        
        view = AnimatedPokerView(game)
        await view.render_table(ctx)

    @commands.command(name="daily")
    async def daily(self, ctx):
        import time
        current_time = time.time()
        success, time_left = self.db.claim_daily(ctx.author.id, current_time)
        
        if success:
            embed = discord.Embed(
                title="🎁 Daily Reward Claimed!",
                description="The casino has fronted you **500 chips**! Use `!balance` to check your vault.",
                color=0x2ecc71
            )
            await ctx.send(embed=embed)
        else:
            hours, remainder = divmod(int(time_left), 3600)
            minutes, _ = divmod(remainder, 60)
            embed = discord.Embed(
                title="⏳ Not so fast!",
                description=f"You've already claimed your daily bailout. Come back in **{hours}h {minutes}m**.",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
            
async def setup(bot):
    await bot.add_cog(PokerCog(bot))