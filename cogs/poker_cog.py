import discord
from discord.ext import commands
from discord.ext import tasks  # <-- Make sure this is here!
import config
import random
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
            discord.SelectOption(label='Table Controls', description='Master the poker loops', emoji='🕹️'),
            discord.SelectOption(label='Game Modes', description='Texas Holdem, Omaha & VIP Strip', emoji='🎴'),
            discord.SelectOption(label='Hand Rankings', description='What beats what at showdown?', emoji='🏆'),
            discord.SelectOption(label='Casino MMO Economy', description='Shop, Slots, Inventories & Barter', emoji='🏦'),
            discord.SelectOption(label='Polymarket Predictions', description='Server match prediction pools', emoji='🔮')
        ]
        super().__init__(placeholder='Choose a help category...', min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        embed = discord.Embed(color=0x1f8b4c)
        
        if self.values[0] == 'Table Controls':
            embed.title = "🕹️ Poker Table Controls"
            embed.description = (
                " Use these commands to coordinate your game lobbies:\n\n"
                "🟢 `!poker_create [mode]` — Open a new lobby. Modes: `texas_holdem`, `omaha`, `strip`.\n"
                "🟢 `!join` — Sit down at the open table (Max 8 players to prevent deck exhaustion).\n"
                "🟢 `!start` — Close the lobby, deal the hole cards, and start the turn loops."
            )
        elif self.values[0] == 'Game Modes':
            embed.title = "🎴 Game Variants Explained"
            embed.description = (
                "🤠 **Texas Hold'em (`texas_holdem`)**\n"
                "The gold standard. 2 private hole cards, 5 shared community cards. Form the strongest 5-card combination.\n\n"
                "🌪 Honor **Omaha (`omaha`)**\n"
                "High variance. 4 private hole cards. You **must** utilize exactly 2 cards from your hand and 3 from the community board to qualify at showdown.\n\n"
                "👙 **Strip Poker (`strip`)**\n"
                "*(Age-Restricted NSFW Channels Only)*. Players start with 5 clothing assets instead of cash. Lose the hand, lose an item (`🧥`, `👔`, `👖`). Last one dressed claims the table."
            )
        elif self.values[0] == 'Hand Rankings':
            embed.title = "🏆 Official Hand Rankings"
            embed.description = (
                "**1. Royal Flush** 👑 (`A♠ K♠ Q♠ J♠ 10♠`)\n"
                "**2. Straight Flush** 🌟 (5 consecutive cards, matching suit)\n"
                "**3. Four of a Kind** 🍀 (4 cards of identical mathematical rank)\n"
                "**4. Full House** 🏠 (Three of a kind blended with a pair)\n"
                "**5. Flush** 💧 (5 cards holding identical suit structures)\n"
                "**6. Straight** 🛤️ (5 numerical sequential ranks across different suits)\n"
                "**7. Three of a Kind** 🎲 (3 matching cards of identical rank)\n"
                "**8. Two Pair** ✌️ (Two distinct ranking pairs)\n"
                "**9. One Pair** 🍒 (Two cards sharing an identical rank)\n"
                "**10. High Card** 🃏 (Highest card on deck breaks the tie)"
            )
        elif self.values[0] == 'Casino MMO Economy':
            embed.title = "🏦 Casino MMO & Vault System"
            embed.description = (
                "**Assets & Gambles**\n"
                "💰 `!balance` (or `!bal`, `!inv`) — View your active chip stacks, inventory items, and pets.\n"
                "🎁 `!daily` — Claim a 500 chip emergency bank injection once every 24 hours.\n"
                "🎰 `!slots [wager]` — Roll the reel slot machine solo while waiting for a lobby.\n"
                "🏆 `!richest` — Display the server-wide top 5 high-roller leaderboard rankings.\n\n"
                "**Transactions & Trade**\n"
                "🛍️ `!shop` — Browse and buy active companions (**Casino Cat**, **Poker Hound**) or the **Luck Ring**.\n"
                "💸 `!pay [@user] [amount]` — Send a secure wire transfer of raw chips directly to another user.\n"
                "⚖️ `!barter [@user] [chips] [item]` — Propose a trade to buy a physical item/pet from another player's vault."
            )
        elif self.values[0] == 'Polymarket Predictions':
            embed.title = "🔮 Polymarket Prediction Engine"
            embed.description = (
                "Any server member can host peer-to-peer prediction markets for custom matches, events, or server lore:\n\n"
                "📣 **`!match_create \"Question\" \"Option A\" \"Option B\"`**\n"
                "Deploys a server-wide open pool frame for spectators to weigh in on.\n\n"
                "🪙 **`!match_bet [Match ID] [A/B] [Amount]`**\n"
                "Locks chips into the designated outcome pool. Odds adjust dynamically based on aggregate share size.\n\n"
                "🏁 **`!match_resolve [Match ID] [A/B]`**\n"
                "Triggers the resolution calculation script. Winners divide the entire combined pool proportionally."
            )
            
        await interaction.response.edit_message(embed=embed)

class HelpView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)
        self.add_item(HelpDropdown())


class ShopDropdown(discord.ui.Select):
    def __init__(self, db, user_id):
        self.db = db
        self.user_id = user_id
        options = [
            discord.SelectOption(label='🍸 Martini', description='Buy a drink (100 chips)', value='martini_100'),
            discord.SelectOption(label='🃏 Golden Deck', description='Fancy cards (1,000 chips)', value='deck_1000'),
            discord.SelectOption(label='👑 VIP Casino Badge', description='Ultimate flex (5,000 chips)', value='vip_5000')
        ]
        super().__init__(placeholder='Browse the Casino Shop...', min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("This isn't your shopping cart!", ephemeral=True)
            
        item_id, cost_str = self.values[0].split('_')
        cost = int(cost_str)
        
        chips, _ = self.db.load_player(self.user_id)
        if chips < cost:
            return await interaction.response.send_message(f"❌ You need {cost} chips to buy this. You only have {chips}.", ephemeral=True)
            
        # Deduct chips (We will expand inventory saving later, but this charges them)
        self.db.cursor.execute('UPDATE players SET chips = chips - ? WHERE user_id = ?', (cost, str(self.user_id)))
        self.db.conn.commit()
        
        await interaction.response.send_message(f"🛒 **Purchase successful!** You bought the `{item_id}` for {cost} chips.", ephemeral=False)

class ShopView(discord.ui.View):
    def __init__(self, db, user_id):
        super().__init__(timeout=120)
        self.add_item(ShopDropdown(db, user_id))

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

# Insert this near the other View classes inside cogs/poker_cog.py

class AdvancedShopDropdown(discord.ui.Select):
    def __init__(self, db, user_id):
        self.db = db
        self.user_id = user_id
        options = [
            discord.SelectOption(label='💍 Luck Ring', description='Boosts slots/luck parameters slightly (500 chips)', value='Luck Ring_500'),
            discord.SelectOption(label='🐱 Casino Cat', description='A cute companion pet for your profile (1500 chips)', value='Casino Cat_1500'),
            discord.SelectOption(label='🐶 Poker Hound', description='The ultimate card-playing companion pet (3000 chips)', value='Poker Hound_3000')
        ]
        super().__init__(placeholder='Browse Items & Companions...', min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("This isn't your transaction window!", ephemeral=True)
            
        item_name, cost = self.values[0].split('_')
        cost = int(cost)
        
        chips, wardrobe, inventory = self.db.load_player(self.user_id)
        if chips < cost:
            return await interaction.response.send_message(f"❌ Transaction declined. You need `{cost}` chips.", ephemeral=True)
            
        if item_name in inventory:
            return await interaction.response.send_message(f"⚠️ You already own a `{item_name}`!", ephemeral=True)

        # Deduct currency and append asset item to array storage
        self.db.cursor.execute('UPDATE players SET chips = chips - ? WHERE user_id = ?', (cost, str(self.user_id)))
        inventory.append(item_name)
        self.db.save_inventory(self.user_id, inventory)
        
        await interaction.response.send_message(f"🛍️ **Purchased!** Added **`{item_name}`** to your vault inventory.", ephemeral=False)

class AdvancedShopView(discord.ui.View):
    def __init__(self, db, user_id):
        super().__init__(timeout=60)
        self.add_item(AdvancedShopDropdown(db, user_id))

class RealItemTradeView(discord.ui.View):
    def __init__(self, db, sender, receiver, chips_offered, item_requested):
        super().__init__(timeout=60)
        self.db = db
        self.sender = sender
        self.receiver = receiver
        self.chips = chips_offered
        self.item = item_requested

    @discord.ui.button(label="Accept Swap", style=discord.ButtonStyle.success, emoji="🤝")
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.receiver.id:
            return await interaction.response.send_message("You are not the recipient of this barter offer.", ephemeral=True)
            
        # Verify absolute storage constraints for both users
        s_chips, _, s_inv = self.db.load_player(self.sender.id)
        _, _, r_inv = self.db.load_player(self.receiver.id)

        if s_chips < self.chips:
            return await interaction.response.edit_message(content="❌ Trade failed: Sender no longer has enough chips.", view=None)
        if self.item not in r_inv:
            return await interaction.response.edit_message(content=f"❌ Trade failed: {self.receiver.display_name} no longer owns the requested item.", view=None)

        # Atomic item swap inside SQLite array configurations
        self.db.cursor.execute('UPDATE players SET chips = chips - ? WHERE user_id = ?', (self.chips, str(self.sender.id)))
        self.db.cursor.execute('UPDATE players SET chips = chips + ? WHERE user_id = ?', (self.chips, str(self.receiver.id)))
        
        r_inv.remove(self.item)
        s_inv.append(self.item)
        
        self.db.save_inventory(self.sender.id, s_inv)
        self.db.save_inventory(self.receiver.id, r_inv)

        await interaction.response.edit_message(content=f"📦 **Trade Executed!** {self.sender.mention} bartered `{self.chips}` chips to {self.receiver.mention} in exchange for **`{self.item}`**!", view=None)

class PokerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.games = {}
        self.db = DatabaseManager()

    @commands.command(name="balance", aliases=["bal", "cash"])
    async def balance(self, ctx):
        # Catch all 3 values from the updated database method
        chips, wardrobe, inventory = self.db.load_player(ctx.author.id)
        
        embed = discord.Embed(
            title=f"💰 {ctx.author.display_name}'s Casino Profile", 
            color=0x2ecc71
        )
        
        # Display Bankroll
        embed.add_field(name="Wallet Vault", value=f"🪙 `{chips}` chips", inline=False)
        
        # Display Strip Mode Wardrobe Status
        embed.add_field(name="Wardrobe Items Remaining", value=f"👔 `{wardrobe}/5` items left", inline=False)
        
        # Display Inventory & Companions
        items_display = "\n".join([f"• `{item}`" for item in inventory]) if inventory else "*No pets or items held*"
        embed.add_field(name="🎒 Vault Inventory", value=items_display, inline=False)
        
        if ctx.author.display_avatar:
            embed.set_thumbnail(url=ctx.author.display_avatar.url)
            
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
        if not game: 
            return await ctx.send("No game running here. Use `!poker_create`.")
            
        status = game.add_player(ctx.author.id, ctx.author.display_name)
        
        if status == "SUCCESS":
            await ctx.send(f"🎟️ **{ctx.author.display_name}** joined the table. (`{len(game.players)}/8`)")
        elif status == "FULL":
            await ctx.send("❌ This table is full! Max 8 players can play at once.")
        elif status == "EXISTS":
            await ctx.send("⚠️ You are already seated at this table!")

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
    
    @commands.command(name="shop", aliases=["store", "market", "buy"])
    async def open_mmo_shop(self, ctx):
        embed = discord.Embed(
            title="🐾 Casino Vault & Pet Emporium",
            description=(
                "Welcome to the high-roller lounge! Spend your hard-earned chips on "
                "boosters, cosmetics, and companion pets here.\n\n"
                "ℹ️ *Use the dropdown menu below to select and buy your item.*"
            ),
            color=0x9b59b6
        )
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/879/879757.png")
        
        view = AdvancedShopView(self.db, ctx.author.id)
        await ctx.send(embed=embed, view=view)

    @commands.command(name="richest", aliases=["leaderboard", "top"])
    async def richest(self, ctx):
        top_players = self.db.get_top_players(limit=5)
        
        embed = discord.Embed(title="🏆 High Roller Leaderboard", color=0xffd700)
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/3135/3135715.png")
        
        description = ""
        medals = ["🥇", "🥈", "🥉", "🏅", "🏅"]
        
        for idx, (user_id, chips) in enumerate(top_players):
            # Fetch the discord user object to get their display name
            try:
                user = await self.bot.fetch_user(int(user_id))
                name = user.display_name
            except:
                name = f"Unknown User ({user_id})"
                
            description += f"{medals[idx]} **{name}** — 🪙 `{chips}`\n\n"
            
        embed.description = description if description else "The vault is empty!"
        await ctx.send(embed=embed)

    @commands.command(name="pay", aliases=["tip", "give"])
    async def pay(self, ctx, target: discord.Member, amount: int):
        if amount <= 0:
            return await ctx.send("❌ You must send a positive amount of chips.")
        if target.id == ctx.author.id:
            return await ctx.send("❌ You can't pay yourself!")
            
        success = self.db.transfer_chips(ctx.author.id, target.id, amount)
        
        if success:
            await ctx.send(f"💸 **Transaction Complete!** {ctx.author.mention} transferred **{amount} chips** to {target.mention}.")
        else:
            await ctx.send("❌ **Transaction Failed.** You don't have enough chips!")

    @commands.command(name="slots")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def slots(self, ctx, bet: int):
        if bet <= 0:
            return await ctx.send("❌ Place a valid bet.")
            
        chips, _, inventory = self.db.load_player(ctx.author.id)
        if chips < bet:
            return await ctx.send(f"❌ You only have {chips} chips.")
            
        import random
        import asyncio
        
        emojis = ["🍒", "🍋", "🍉", "⭐", "💎"]
        
        # Divert 2% to the global jackpot pool frame
        tax = max(1, int(bet * 0.02))
        self.db.cursor.execute('UPDATE players SET chips = chips - ? WHERE user_id = ?', (bet, str(ctx.author.id)))
        self.db.add_to_jackpot(tax)
        self.db.conn.commit()
        
        msg = await ctx.send(f"🎰 **Spinning...** (Global Jackpot: 🪙 `{self.db.get_jackpot()}`)\n### `[ 🔄 | 🔄 | 🔄 ]`")
        await asyncio.sleep(0.5)
        
        r1 = random.choice(emojis)
        await msg.edit(content=f"🎰 **Reel 1 Locked!**\n### `[ {r1} | 🔄 | 🔄 ]`")
        await asyncio.sleep(0.5)
        
        r2 = random.choice(emojis)
        await msg.edit(content=f"🎰 **Reel 2 Locked!**\n### `[ {r1} | {r2} | 🔄 ]`")
        await asyncio.sleep(0.5)
        
        r3 = random.choice(emojis)
        result = [r1, r2, r3]
        
        has_luck_ring = "Luck Ring" in inventory
        jackpot_won = False
        winnings = 0
        
        # Check Progressive Mega Jackpot
        if result[0] == result[1] == result[2] == "💎":
            progressive_pool = self.db.get_jackpot()
            winnings = bet * 10 + progressive_pool
            self.db.reset_jackpot()
            jackpot_won = True
            status = f"👑 **MEGA PROGRESSIVE JACKPOT!!!** You won **🪙 {winnings} chips** and cleared the server vault!"
        elif result[0] == result[1] == result[2]:
            multiplier = 12 if has_luck_ring else 10
            winnings = bet * multiplier
            status = f"🔥 **JACKPOT!** You won **{winnings} chips!**"
        elif result[0] == result[1] or result[1] == result[2] or result[0] == result[2]:
            winnings = bet * 2
            status = f"✨ **Minor Win!** You collected **{winnings} chips!**"
        else:
            status = f"💀 **Bust!** Lost `{bet}` chips. (+`{tax}` funneled to Server Jackpot)"
            
        if winnings > 0:
            self.db.cursor.execute('UPDATE players SET chips = chips + ? WHERE user_id = ?', (winnings, str(ctx.author.id)))
            self.db.conn.commit()
            
        embed = discord.Embed(
            title="🎰 Casino Slots", 
            description=f"**{ctx.author.display_name}** spin roster:\n\n# [ {result[0]} | {result[1]} | {result[2]} ]\n\n{status}", 
            color=0xffd700 if jackpot_won else 0xe67e22
        )
        await msg.edit(content=None, embed=embed)
    # --- Upgraded MMO Interactions & Systems ---

    @commands.command(name="open", aliases=["lootbox", "crate"])
    async def open_box(self, ctx):
        cost = 500
        chips, _, inventory = self.db.load_player(ctx.author.id)
        
        if chips < cost:
            return await ctx.send(f"❌ A Mystery Lootbox costs `🪙 {cost}` chips. You only have `{chips}`.")
            
        import random
        import asyncio
        
        # Deduct entry price configuration
        self.db.cursor.execute('UPDATE players SET chips = chips - ? WHERE user_id = ?', (cost, str(ctx.author.id)))
        self.db.conn.commit()
        
        # Frame Animation Data
        box_msg = await ctx.send("📦 **Placing Mystery Crate on the table...**")
        await asyncio.sleep(0.6)
        await box_msg.edit(content="🔓 **Popping the locking hinges...**\n`[ ░░░░░░░░░░ ] 0%`")
        await asyncio.sleep(0.5)
        await box_msg.edit(content="✨ **Unboxing data payload structure...**\n`[ ████░░░░░░ ] 40%`")
        await asyncio.sleep(0.5)
        await box_msg.edit(content="⚡ **Revealing structural asset rarity...**\n`[ ████████░░ ] 80%`")
        await asyncio.sleep(0.4)
        
        # Loot drop allocations
        roll = random.randint(1, 100)
        if roll <= 70:  # Common Tier
            dropped_item = random.choice(["🍸 Martini", "👔 Designer Shirt", "🧥 Luxury Coat"])
            color = 0x95a5a6
            tier = "COMMON"
        elif roll <= 95: # Rare Tier
            dropped_item = random.choice(["💍 Luck Ring", "🐱 Casino Cat"])
            color = 0x3498db
            tier = "RARE"
        else:           # Legendary Tier
            dropped_item = random.choice(["静态 Display Skin", "🐶 Poker Hound", "🦊 Cyber Dragon"])
            color = 0x9b59b6
            tier = "✨ LEGENDARY ✨"
            
        inventory.append(dropped_item)
        self.db.save_inventory(ctx.author.id, inventory)
        
        embed = discord.Embed(
            title=f"🎁 Box Rarity Unboxed: {tier}",
            description=f"🏆 {ctx.author.mention} unboxed a **`{dropped_item}`**!\n\n*Item added into your persistent vault profile container storage.*",
            color=color
        )
        await box_msg.edit(content=None, embed=embed)

    @commands.command(name="inventory", aliases=["inv", "items"])
    async def view_inventory(self, ctx):
        chips, _, inventory = self.db.load_player(ctx.author.id)
        
        # Adjust game parameters dynamically based on possession of the Luck Ring
        luck_boost = "Active (+0.00000001% Placebo Boost)" if "Luck Ring" in inventory else "None"
        
        embed = discord.Embed(title=f"🎒 {ctx.author.display_name}'s Inventory", color=0x34495e)
        
        items_display = "\n".join([f"• ✨ `{item}`" for item in inventory]) if inventory else "*Empty Vault*"
        embed.add_field(name="Collected Items & Pets", value=items_display, inline=False)
        embed.add_field(name="Current Luck Value Modifier", value=f"🔹 `{luck_boost}`", inline=True)
        
        if ctx.author.display_avatar:
            embed.set_thumbnail(url=ctx.author.display_avatar.url)
            
        await ctx.send(embed=embed)

    @commands.command(name="barter")
    async def barter_swap(self, ctx, target: discord.Member, chips_offered: int, *, item_to_request: str):
        if target.id == ctx.author.id: return await ctx.send("You cannot item barter with yourself.")
        
        _, _, r_inv = self.db.load_player(target.id)
        if item_to_request not in r_inv:
            return await ctx.send(f"❌ {target.display_name} does not have a `{item_to_request}` in their inventory vector.")

        view = RealItemTradeView(self.db, ctx.author, target, chips_offered, item_to_request)
        await ctx.send(
            content=f"⚖️ **Barter Offer Raised!** {ctx.author.mention} wants to swap **🪙 {chips_offered} chips** for {target.mention}'s **`{item_to_request}`**.", 
            view=view
        )

    # --- Decentralized Prediction Engine Modules (Polymarket Framework) ---

    @commands.command(name="match_create", aliases=["mc"])
    async def custom_match_build(self, ctx, question: str, option_a: str, option_b: str):
        match_id = self.db.create_match(ctx.author.id, question, option_a, option_b)
        
        embed = discord.Embed(
            title=f"🔮 New Polymarket Window Opened! (Match #{match_id})",
            description=f"### {question}\n\n🅰️ **{option_a}**\n🅱️ **{option_b}**\n\n*Use `!match_bet {match_id} [A/B] [wager]` to back a outcome.*",
            color=0xe74c3c
        )
        await ctx.send(embed=embed)

    @commands.command(name="match_bet", aliases=["mb"])
    async def wager_custom_match(self, ctx, match_id: int, choice: str, amount: int):
        if amount <= 0: return await ctx.send("Wager value must be positive.")
        
        status = self.db.place_match_wager(ctx.author.id, ctx.author.display_name, match_id, choice, amount)
        if status == "SUCCESS":
            await ctx.send(f"✅ Wager registered! **{ctx.author.display_name}** dropped `🪙 {amount}` into choice **{choice.upper()}** for Match `#{match_id}`.")
        elif status == "CLOSED":
            await ctx.send("❌ This prediction market has already locked or been resolved.")
        elif status == "NO_CHIPS":
            await ctx.send("❌ Insufficient vault funds to clear this market wager.")

    @commands.command(name="match_resolve", aliases=["mr"])
    async def execute_resolution(self, ctx, match_id: int, winning_option: str):
        # Secure endpoint check: Only the match creator can close out the prediction vector
        ctx.value_cursor = self.db.cursor
        ctx.value_cursor.execute('SELECT creator_id FROM custom_predictions WHERE id = ?', (match_id,))
        match = ctx.value_cursor.fetchone()
        
        if not match: return await ctx.send("Match market context missing.")
        if match[0] != str(ctx.author.id):
            return await ctx.send("❌ Access Denied. Only the match organizer can resolve this outcome.")

        resolution_report = self.db.resolve_match(match_id, winning_option)
        await ctx.send(content=resolution_report)

    
    

    # Add inside your PokerCog __init__ setup method:
    # self.voice_passive_income_loop.start()

    @tasks.loop(minutes=1)
    async def voice_passive_income_loop(self):
        """Monitors all server voice channels and credits passive dividends for active companions"""
        for guild in self.bot.guilds:
            for vc in guild.voice_channels:
                for member in vc.members:
                    if member.bot: 
                        continue
                        
                    chips, wardrobe, inventory = self.db.load_player(member.id)
                    payout = 0
                    
                    if "Casino Cat" in inventory: 
                        payout += 5
                    if "Poker Hound" in inventory: 
                        payout += 10
                    if "Cyber Dragon" in inventory:
                        payout += 25

                    if payout > 0:
                        self.db.cursor.execute('UPDATE players SET chips = chips + ? WHERE user_id = ?', (payout, str(member.id)))
        self.db.conn.commit()

    def cog_unload(self):
        self.voice_passive_income_loop.cancel()

    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏳ **Hold your horses, {ctx.author.display_name}!** You can spin again in **{error.retry_after:.1f} seconds**.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ **Missing Parameter!** Syntax requirement: `{ctx.prefix}{ctx.command.name} [amount/wager]`")
        else:
            raise error

async def setup(bot):
    await bot.add_cog(PokerCog(bot))