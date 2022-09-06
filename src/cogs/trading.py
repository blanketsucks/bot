from __future__ import annotations
import asyncio

from typing import Dict, List, NamedTuple, Tuple

import discord
from discord.ext import commands

from src.bot import Pokecord
from src.database import User
from src.utils import Context, title
from src.database.user import UserPokemon
from src.database.pokemons import IVs, EVs, Moves

class TradedPokemon(NamedTuple):
    level: int
    exp: int
    ivs: IVs
    evs: EVs
    moves: Moves
    id: int
    nickname: str
    shiny: bool

class UserTrade:
    def __init__(self, user: User) -> None:
        self.user = user

        self.credits = 0
        self.pokemons: List[UserPokemon] = []

        self.confirmed = False

    def empty(self) -> bool:
        return self.credits == 0 and len(self.pokemons) == 0
    
    async def finish(self) -> List[TradedPokemon]:
        if self.credits:
            await self.user.balance.decrement(self.credits)
        
        traded: List[TradedPokemon] = []
        for pokemon in self.pokemons:
            trade = TradedPokemon(
                level=pokemon.level,
                exp=pokemon.exp,
                ivs=pokemon.ivs,
                evs=pokemon.evs,
                moves=pokemon.moves,
                id=pokemon.id,
                nickname=pokemon.nickname,
                shiny=pokemon.shiny
            )

            traded.append(trade)

            await pokemon.release()
            # self.user.pokemons.pop(pokemon.catch_id)

        return traded

    def add_credits(self, amount: int) -> None:
        self.credits += amount

    def add_pokemon(self, pokemon: UserPokemon) -> bool:
        if discord.utils.find(lambda poke: poke.catch_id == pokemon.catch_id, self.pokemons):
            return False

        self.pokemons.append(pokemon)
        return True

class Trade:
    def __init__(self, p1: User, p2: User) -> None:
        self.p1 = UserTrade(p1)
        self.p2 = UserTrade(p2)

    @property
    def user1(self) -> User:
        return self.p1.user

    @property
    def user2(self) -> User:
        return self.p2.user
    
    def add_credits_for(self, user_id: int, amount: int) -> None:
        if self.user1.id == user_id:
            self.p1.add_credits(amount)
        else:
            self.p2.add_credits(amount)

    def add_pokemon_for(self, user_id: int, pokemon: UserPokemon) -> bool:
        if self.user1.id == user_id:
            return self.p1.add_pokemon(pokemon)
        else:
            return self.p2.add_pokemon(pokemon)

    def set_confirm_for(self, user_id: int) -> None:
        if self.user1.id == user_id:
            self.p1.confirmed = True
        else:
            self.p2.confirmed = True

    async def finish(self) -> None:
        traded1 = await self.p1.finish()
        if self.p1.credits:
            await self.user2.balance.increment(self.p1.credits)

        traded2 = await self.p2.finish()
        if self.p2.credits:
            await self.user1.balance.increment(self.p2.credits)

        for trade in traded1:
            await self.user2.add_pokemon(
                pokemon_id=trade.id,
                level=trade.level,
                exp=trade.exp,
                is_shiny=trade.shiny,
                ivs=trade.ivs,
                evs=trade.evs,
                moves=trade.moves,
                nickname=trade.nickname
            )

        for trade in traded2:
            await self.user1.add_pokemon(
                pokemon_id=trade.id,
                level=trade.level,
                exp=trade.exp,
                is_shiny=trade.shiny,
                ivs=trade.ivs,
                evs=trade.evs,
                moves=trade.moves,
                nickname=trade.nickname
            )

        if traded1:
            await self.user1.reindex()
        if traded2:
            await self.user2.reindex()

class StoredTrade(NamedTuple):
    trade: Trade
    message: discord.Message
    user1: discord.Member
    user2: discord.Member
    lock: asyncio.Lock
    event: asyncio.Event

class Trades(commands.Cog):
    def __init__(self, bot: Pokecord):
        self.bot = bot

        self.trades: Dict[int, StoredTrade] = {}
    
    def format_trade_list(self, user: UserTrade) -> str:
        fmt = '```\n'
        if user.credits:
            fmt += f'{user.credits} Credits\n'

        for pokemon in user.pokemons:
            fmt += f'Level {pokemon.level} '
            if pokemon.shiny:
                fmt += '✨ ' 
            
            fmt += title(pokemon.dex.default_name)
            if pokemon.has_nickname():
                fmt += f' "{pokemon.nickname}"'

            fmt += '\n'

        fmt += '```\n'
        return fmt

    async def refresh(self, trade: StoredTrade) -> None:
        async with trade.lock:
            embed = discord.Embed(title=f'Trade between {trade.user1} and {trade.user2}', color=0x36E3DD)
            embed.description = ''

            if not trade.trade.p1.empty():
                embed.description += f'**{trade.user1}\'s items**: '
                if trade.trade.p1.confirmed:
                    embed.description += '✅\n'
                else:
                    embed.description += '\n'

                embed.description += self.format_trade_list(trade.trade.p1)

                embed.description += '\n\n'
            
            if not trade.trade.p2.empty():
                embed.description += f'**{trade.user2}\'s items**: '
                if trade.trade.p2.confirmed:
                    embed.description += '✅\n'
                else:
                    embed.description += '\n'

                embed.description += self.format_trade_list(trade.trade.p2)

            embed.set_footer(text='Add items using `p!trade add credits <credits>` or p!trade add pokemon <pokemon>`')
            await trade.message.edit(embed=embed, content=None)

    @commands.group(invoke_without_command=True, aliases=['tr'])
    async def trade(self, ctx: Context, user: discord.Member):
        assert isinstance(ctx.author, discord.Member)

        user1 = await self.bot.pool.get_user(user.id)
        if not user1:
            return await ctx.send('That user does not have a starter yet.')

        if user.id in self.trades:
            return await ctx.send('That user is already inside a trade.')

        msg = await ctx.send(f'{user.mention}, {ctx.author.mention} wants to trade with you. Type `accept` to accept the trade.')

        try:
            def check(m: discord.Message):
                return (m.author == user and m.channel == ctx.channel and m.content.casefold() == 'accept'.casefold())

            await self.bot.wait_for('message', check=check, timeout=30)
        except asyncio.TimeoutError:
            return await ctx.send('Aborted.')

        await msg.delete()
        message = await ctx.send('Starting trade...')

        lock = asyncio.Lock()
        event = asyncio.Event()

        trade = StoredTrade(Trade(ctx.pool.user, user1), message, ctx.author, user, lock, event)

        self.trades[user.id] = trade
        self.trades[ctx.author.id] = trade

        await asyncio.sleep(1)
        await self.refresh(trade)

        await event.wait()

        self.trades.pop(ctx.author.id); self.trades.pop(user.id)

        await trade.trade.finish()
        await ctx.send(f'Successfully traded with {user}.')

    @trade.command(aliases=['c'])
    async def confirm(self, ctx: Context):
        if ctx.author.id not in self.trades:
            return await ctx.send('You are not in a trade.')

        await ctx.send(f'{ctx.author.mention} Type `confirm` to confirm the trade.')
        try:
            def check(m: discord.Message):
                return (m.author == ctx.author and m.channel == ctx.channel and m.content.casefold() == 'confirm'.casefold())

            await self.bot.wait_for('message', check=check, timeout=30)
        except asyncio.TimeoutError:
            return await ctx.send('Aborted.')

        trade = self.trades[ctx.author.id]
        trade.trade.set_confirm_for(ctx.author.id)

        await self.refresh(trade)
        if trade.trade.p1.confirmed and trade.trade.p2.confirmed:
            trade.event.set()

    @trade.group(invoke_without_command=True, aliases=['a'])
    async def add(self, ctx: Context): ...

    @add.command(aliases=['c'])
    async def credits(self, ctx: Context, amount: int):
        if ctx.author.id not in self.trades:
            return await ctx.send('You are not in a trade.')

        trade = self.trades[ctx.author.id]

        trade.trade.p1.confirmed = False
        trade.trade.p2.confirmed = False

        trade.trade.add_credits_for(ctx.author.id, amount)

        await self.refresh(trade)

    @add.command(aliases=['p'])
    async def pokemon(self, ctx: Context, pokemon: UserPokemon):
        if ctx.author.id not in self.trades:
            return await ctx.send('You are not in a trade.')

        trade = self.trades[ctx.author.id]
    
        trade.trade.p1.confirmed = False
        trade.trade.p2.confirmed = False

        added = trade.trade.add_pokemon_for(ctx.author.id, pokemon)
        if not added:
            await ctx.send('That pokemon is already added to the trade.')
        else:
            await self.refresh(trade)

async def setup(bot: Pokecord):
    await bot.add_cog(Trades(bot))