import asyncio
from typing import Dict, List
import discord
from discord.ext import commands

from bot import Pokecord
import wrapper
from utils import database, calc

class Duels(commands.Cog):
    def __init__(self, bot: Pokecord) -> None:
        self.bot = bot

        self.duels: Dict[int, List[int]] = {}

    async def wait_for_user(self): ...
    async def wait_for_enemy(self): ...

    @commands.command(name='duel', aliases=['battle'])
    async def _duel(self, ctx: commands.Context, member: discord.Member):
        enemy = await self.bot.pool.get_user(member.id)
        user = await self.bot.pool.get_user(ctx.author.id)

        if not enemy:
            return await ctx.send(f'{member.mention} does not have a starter pokémon.')

        duels = self.duels.get(ctx.author.id)
        if isinstance(duels, list):
            if len(duels) == 1:
                return await ctx.send(f'You are already inside a duel. Please finish the current one to start a new one.')

        duels = self.duels.get(member.id)
        if isinstance(duels, list):
            if len(duels) == 1:
                return await ctx.send(f'{member.display_name} already inside a duel.')

        self.duels[ctx.author.id] = [member.id]
        self.duels[member.id] = [ctx.author.id]

class Duel:
    def __init__(self, user: discord.Member, enemy: discord.Member, bot: Pokecord) -> None:
        self.bot = bot
        self.user = user
        self.enemy = enemy

    async def start(self, ctx: commands.Context):
        self._user = await self.bot.pool.get_user(self.user.id)
        self._enemy = await self.bot.pool.get_user(self.enemy.id)

        self.ctx = ctx

        self.user_health = await self.get_starting_health(self._user)
        self.enemy_health = await self.get_starting_health(self._enemy)

    async def get_starting_health(self, user: database.User):
        entry, _ = user.get_selected()

        pokemon = entry['pokemon']
        name = pokemon['name']
        level = pokemon['level']

        rounded, hp, atk, defen, spatk, spdef, spd = self.bot._get_ivs(pokemon['ivs'])
        pokemon, shiny = await self.bot.fetch_pokemon(name)

        await pokemon.get_stats()

        health = calc.calculate_health(pokemon.health.base, hp, level)
        return health

    def check(self, m):
        return m.channel == self.ctx.channel and m.author == self.ctx.author

    async def turn(self, user: discord.Member, db: database.User):
        await self.embed(user, db)
        entry, _ = db.get_selected()

        level = entry['pokemon']['level']
        moves = entry['pokemon']['moves']

        try:
            message = await self.bot.wait_for('message', check=self.check, timeout=20)
        except asyncio.TimeoutError:
            return await self.ctx.send('You took too long. Duel cancelled.')

        await message.delete()
        move = message.content

        if int(move) < 0 or int(move) > 4:
            await self.ctx.send('Invalid move range.')

        choice = moves[move]
        move = await wrapper.get_move(choice.lower().replace(' ', '-'), self.bot.session)

        dmg = 0

        if calc.miss(move.accuracy):
            return dmg

        return calc.damage(level, move.power)

    async def embed(self, member: discord.Member, db: database.User):
        moves = db.get_selected_moves()

        embed = discord.Embed(title='Duel')
        embed.description = 'Please pick a move from the list below.'

        for k, v in moves.items():
            embed.add_field(name=k, value=v.title(), inline=False)

        return await member.send(embed=embed)