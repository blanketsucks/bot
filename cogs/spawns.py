from typing import Any, Dict, Optional
import discord
from discord.ext import commands
import asyncio
import random

from utils import calc, Context
from bot import Pokecord, SpawnRates, Rarity

class Spawns(commands.Cog):
    def __init__(self, bot: Pokecord) -> None:
        self.bot = bot

        self.spawns: Dict[int, Any] = {}

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
        names = (n.lower() for n in pokemon.names)

        if name.lower() in names:
            level = random.randint(1, 50)
            await ctx.reply(f'You caught a level {level} {name.lower()}!!')

            user = await self.bot.pool.get_user(ctx.author.id)
            await user.add_pokemon(name, level, 0)

            self.spawns.pop(ctx.channel.id, None)
            return

        await ctx.send('Wrong pokémon!')

    @commands.command(name='set')
    @commands.has_guild_permissions(administrator=True)
    async def _set(self, ctx: commands.Context, *, channel: discord.TextChannel):
        guild = await self.bot.pool.get_guild(ctx.guild.id)

        if guild:
            await guild.update_spawn_channel(
                channel_id=channel.id
            )

            return await ctx.send(
                content=f'Successfully updated the spawn channel to {channel.mention}'
            )

        await self.bot.pool.add_guild(ctx.guild.id, channel.id)
        await ctx.send(f'Successfully set the spawn channel to {channel.mention}')

    @commands.command('prefix')
    async def _prefix(self, ctx: commands.Context, prefix: Optional[str]):
        guild = await self.bot.pool.get_guild(ctx.guild.id)
        
        if not prefix:
            return await ctx.send(f'My current prefix is `{guild.prefix}`.')

        if ctx.author.guild_permissions.administrator:
            await guild.update_prefix(prefix)
            await ctx.send(f'Changed prefix to `{prefix}`.')

        else:
            await ctx.send('Missing administrator permissions.')
    
    @commands.command(name='spawn')
    @commands.is_owner()
    async def __spawn(self, ctx: Context, *, name: str):
        def check(m):
            return m.channel == ctx.channel and m.author == ctx.author

        pokemon = self.bot.pokedex.get(name)

        if pokemon is None:
            return await ctx.send('Not found.')

        embed = discord.Embed()
        embed.title = 'Use p!catch <pokémon name> to catch the following pokémon.'

        waiter = self.bot.loop.create_task(coro=self._sleep())
        message = await ctx.send_with_image(embed=embed, pokemon=pokemon)

        self.spawns[ctx.channel.id] = pokemon
        await self._wait(message, waiter)

    async def should_spawn(self, message: discord.Message):
        if not message.guild:
            return False

        guild = await self.bot.pool.get_guild(message.guild.id)

        conditions = [
            message.guild is not None,
            calc.chance(SpawnRates.GLOBAL),
            guild is not None,
            not message.author.bot
        ]
        return all(conditions)

    def check_rarity(self):
        rarity = Rarity.COMMON

        if calc.chance(SpawnRates.ULTRA_BEAST):
            rarity = Rarity.ULTRA_BEAST

        if calc.chance(SpawnRates.MYTHICAL):
            rarity = Rarity.MYTHICAL

        if calc.chance(SpawnRates.LEGENDARY):
            rarity = Rarity.LEGENDARY

        return rarity

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if await self.should_spawn(message):
            rarity = self.check_rarity()

            if rarity is Rarity.COMMON:
                name = random.choice(self.bot.commons)

            if rarity is Rarity.ULTRA_BEAST:
                name = random.choice(self.bot.ultrabeasts)

            if rarity is Rarity.LEGENDARY:
                name = random.choice(self.bot.legendaries)

            if rarity is Rarity.MYTHICAL:
                name = random.choice(self.bot.mythicals)

            pokemon = self.bot.pokedex.get(name)
            self.bot.dispatch('pokemon_spawn', pokemon, message.channel)

            embed = discord.Embed(title='Use p!catch <pokémon name> to catch the following pokémon.')
            ctx = await self.bot.get_context(message)

            message = await ctx.send_with_image(embed=embed, pokemon=pokemon)
            waiter = asyncio.ensure_future(self._sleep())

            self.spawns[message.channel.id] = pokemon
            await self._wait(message, waiter)

def setup(bot: Pokecord):
    bot.add_cog(Spawns(bot))