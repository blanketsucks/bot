from typing import Dict, List
import discord
from discord.ext import commands

from bot import Pokecord

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
            if len(duels) > 1:
                return await ctx.send(f'You are already inside a duel. Please finish the current one to start a new one.')

        duels = self.duels.get(member.id)
        if isinstance(duels, list):
            if len(duels) > 1:
                return await ctx.send(f'{member.display_name} already inside a duel.')

        