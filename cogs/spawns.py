from typing import Dict
import discord
from discord.ext import commands
import asyncio
import random

from utils import calc
from bot import Pokecord
from wrapper.pokemons import Pokemon

class Spawns(commands.Cog):
    def __init__(self, bot: Pokecord) -> None:
        self.bot = bot

        self.spawns: Dict[int, Pokemon] = {}

    async def _sleep(self):
        await asyncio.sleep(30.0)

    async def _wait(self, message: discord.Message, waiter: asyncio.Task[None]):
        def check(m):
            return m.channel == message.channel and m.author == message.author

        while not waiter.done():
            message = await self.bot.wait_for('message', check=check)
            context = await self.bot.get_context(message)

        self.spawns.pop(message.channel.id, None)

    @commands.command()
    async def catch(self, ctx: commands.Context, *, name: str):
        if not self.spawns.get(ctx.channel.id):
            return await ctx.send('No pokémons available')
        
        pokemon = self.spawns.get(ctx.channel.id)

        if name.lower() == pokemon.name:
            level = random.randint(1, 50)
            await ctx.reply(f'You caught a level {level} {name.lower()}!!')

            await self.bot.pool.add_pokemon(ctx.author.id, name, level)

            self.spawns.pop(ctx.channel.id)
            return

        await ctx.send('Wrong pokémon!')

    @commands.command(name='set')
    async def _set(self, ctx: commands.Context, *, channel: discord.TextChannel):
        guild = await self.bot.pool.get_guild(ctx.guild.id)

        if guild:
            await self.bot.pool.update_spawn_channel(
                guild_id=ctx.guild.id,
                channel_id=channel.id
            )

            return await ctx.send(
                content=f'Successfully updated the spawn channel to {channel.mention}'
            )

        await self.bot.pool.add_guild(ctx.guild.id, channel.id)
        await ctx.send(f'Successfully set the spawn channel to {channel.mention}')
    
    @commands.command(name='spawn')
    @commands.is_owner()
    async def __spawn(self, ctx: commands.Context, *, name: str):
        def check(m):
            return m.channel == ctx.channel and m.author == ctx.author

        pokemon, _ = await self.bot.fetch_pokemon(name)
        pokemon.name = self.bot._parse_pokemon(pokemon.name)

        if pokemon is None:
            return await ctx.send('Not found.')

        embed = discord.Embed()
        embed.title = 'Use p!catch <pokémon name> to catch the following pokémon.'

        embed.set_image(url=pokemon.sprite.front)

        waiter = self.bot.loop.create_task(coro=self._sleep())
        message = await ctx.send(embed=embed)

        self.spawns[ctx.channel.id] = pokemon
        await self._wait(message, waiter)

    async def should_spawn(self, message: discord.Message):
        guild = await self.bot.pool.get_guild(message.guild.id)

        conditions = [
            message.guild is not None,
            calc.chance(self.bot.global_spawn_chance),
            guild is not None,
            not message.author.bot
        ]
        return all(conditions)

    def check_rarity(self):
        rarity = 'common'

        if calc.chance(self.bot.mythical_spawn_rate):
            rarity = 'mythical'

        if calc.chance(self.bot.legendary_spawn_rate):
            rarity = 'legendary'

        return rarity

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        should = await self.should_spawn(message)

        if should is True:
            rarity = self.check_rarity()

            if rarity == 'common':
                name = random.choice(self.bot.names)

            if rarity == 'legendary':
                name = random.choice(self.bot.legendaries)

            if rarity == 'mythical':
                name = random.choice(self.bot.mythicals)

            pokemon, _ = await self.bot.fetch_pokemon(name)
            pokemon.name = self.bot._parse_pokemon(pokemon.name)

            embed = discord.Embed(title='Use p!catch <pokémon name> to catch the following pokémon.')
            embed.set_image(url=pokemon.sprite.front)

            message = await message.channel.send(embed=embed)
            waiter = self.bot.loop.create_task(self._sleep())

            self.spawns[message.channel.id] = pokemon
            await self._wait(message, waiter)

def setup(bot: Pokecord):
    bot.add_cog(Spawns(bot))