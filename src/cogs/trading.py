from __future__ import annotations

from typing import Dict, List, NamedTuple

import discord
import asyncio
from discord.ext import commands

from src.bot import Pokecord
from src.database import User
from src.utils import Context, ConfirmationView
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
        self.redeems = 0
        self.pokemons: List[UserPokemon] = []

        self.confirmed = False

    def empty(self) -> bool:
        return self.credits == 0 and len(self.pokemons) == 0 and self.redeems == 0
    
    async def finish(self) -> List[UserPokemon]:
        if self.credits:
            await self.user.remove_credits(self.credits)

        if self.redeems:
            await self.user.remove_redeems(self.redeems)

        return self.pokemons

    def add_credits(self, amount: int) -> None:
        self.credits += amount
    
    def add_redeems(self, amount: int) -> None:
        self.redeems += amount

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

    def add_redeems_for(self, user_id: int, amount: int) -> None:
        if self.user1.id == user_id:
            self.p1.add_redeems(amount)
        else:
            self.p2.add_redeems(amount)

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
            await self.user2.add_credits(self.p1.credits)
        if self.p1.redeems:
            await self.user2.add_redeems(self.p1.redeems)

        traded2 = await self.p2.finish()
        if self.p2.credits:
            await self.user1.add_credits(self.p2.credits)
        if self.p2.redeems:
            await self.user1.add_redeems(self.p2.redeems)

        for trade in traded1:
            await trade.transfer(self.user2)

        for trade in traded2:
            await trade.transfer(self.user1)

class StoredTrade(NamedTuple):
    trade: Trade
    message: discord.Message
    user1: discord.Member
    user2: discord.Member
    lock: asyncio.Lock
    future: asyncio.Future[bool]

class Trades(commands.Cog):
    def __init__(self, bot: Pokecord):
        self.bot = bot

        self.trades: Dict[int, StoredTrade] = {}
    
    def format_trade_list(self, user: UserTrade) -> str:
        fmt = '```\n'
        if user.credits:
            fmt += f'{user.credits} Credits\n'
        if user.redeems:
            fmt += f'{user.redeems} Redeems\n'

        for pokemon in user.pokemons:
            fmt += f'Level {pokemon.level} '
            if pokemon.shiny:
                fmt += '✨ ' 
            
            fmt += pokemon.dex.default_name
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

                embed.description += '\n'
            
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

        view = ConfirmationView(user)
        view.message = await ctx.send(
            f'{user.mention}, {ctx.author.mention} wants to trade with you. Click on `Confirm` to accept the trade.',
            view=view
        )

        await view.wait()
        if not view.value:
            return await ctx.send('Aborted.')

        await view.message.delete()
        message = await ctx.send('Starting trade...')

        lock = asyncio.Lock()
        future = self.bot.loop.create_future()

        trade = StoredTrade(Trade(ctx.pool.user, user1), message, ctx.author, user, lock, future)

        self.trades[user.id] = trade
        self.trades[ctx.author.id] = trade

        await asyncio.sleep(1)
        await self.refresh(trade)

        try:
            await asyncio.wait_for(future, timeout=Pokecord.TRADE_TIMEOUT)
        except asyncio.TimeoutError:
            return await ctx.send('Trade timeout.')

        self.trades.pop(ctx.author.id); self.trades.pop(user.id)

        result = future.result()
        if not result:
            return await ctx.send('Aborted.')

        await trade.trade.finish()

        await ctx.pool.user.reindex()
        await user1.reindex()

        await ctx.send(f'Successfully traded with {user}.')

    @trade.command(aliases=['c'])
    async def confirm(self, ctx: Context):
        if ctx.author.id not in self.trades:
            return await ctx.send('You are not in a trade.')

        trade = self.trades[ctx.author.id]
        trade.trade.set_confirm_for(ctx.author.id)

        await self.refresh(trade)
        if trade.trade.p1.confirmed and trade.trade.p2.confirmed:
            trade.future.set_result(True)
    
    @trade.command()
    async def cancel(self, ctx: Context):
        if ctx.author.id not in self.trades:
            return await ctx.send('You are not in a trade.')

        trade = self.trades[ctx.author.id]
        trade.future.set_result(False)

    @trade.group(invoke_without_command=True, aliases=['a'])
    async def add(self, ctx: Context): ...

    @add.command(aliases=['c'])
    async def credits(self, ctx: Context, amount: int):
        if ctx.author.id not in self.trades:
            return await ctx.send('You are not in a trade.')

        if amount > ctx.pool.user.credits:
            return await ctx.send('You do not have enough credits.')

        trade = self.trades[ctx.author.id]

        trade.trade.p1.confirmed = False
        trade.trade.p2.confirmed = False

        trade.trade.add_credits_for(ctx.author.id, amount)

        await self.refresh(trade)

    @add.command(aliases=['p'])
    async def pokemon(self, ctx: Context, pokemon: UserPokemon):
        if ctx.author.id not in self.trades:
            return await ctx.send('You are not in a trade.')

        if pokemon.is_starter():
            return await ctx.send('You cannot add your starter to a trade.')

        trade = self.trades[ctx.author.id]
    
        trade.trade.p1.confirmed = False
        trade.trade.p2.confirmed = False

        added = trade.trade.add_pokemon_for(ctx.author.id, pokemon)
        if not added:
            await ctx.send('That pokemon is already added to the trade.')
        else:
            await self.refresh(trade)

    @add.command(aliases=['r'])
    async def redeem(self, ctx: Context, amount: int = 1):
        if ctx.author.id not in self.trades:
            return await ctx.send('You are not in a trade.')

        if amount > ctx.pool.user.redeems:
            return await ctx.send('You do not have enough redeems.')

        trade = self.trades[ctx.author.id]
    
        trade.trade.p1.confirmed = False
        trade.trade.p2.confirmed = False

        trade.trade.add_redeems_for(ctx.author.id, amount)

async def setup(bot: Pokecord):
    await bot.add_cog(Trades(bot))