from typing import Dict, Tuple
import discord
from discord.ext import commands
import asyncio
import random

from src.utils.pokedex import PokedexEntry, Rarity
from src.utils import Context, chance
from src.bot import Pokecord, SpawnRates

ChannelSpawn = Tuple[PokedexEntry, asyncio.Event]

class Spawns(commands.Cog):
    def __init__(self, bot: Pokecord) -> None:
        self.bot = bot
        self.spawns: Dict[int, ChannelSpawn] = {}

    def store_spawn(self, channel_id: int, pokemon: PokedexEntry) -> asyncio.Event:
        event = asyncio.Event()
        self.spawns[channel_id] = (pokemon, event)

        return event

    async def wait(self, channel_id: int, pokemon: PokedexEntry) -> None:
        event = self.store_spawn(channel_id, pokemon)

        try:
            await asyncio.wait_for(event.wait(), timeout=Pokecord.CHANNEL_SPAWN_TIMEOUT)
        except asyncio.TimeoutError:
            pass

        self.spawns.pop(channel_id)

    @commands.command()
    async def catch(self, ctx: Context, *, name: str):
        if not self.spawns.get(ctx.channel.id):
            return await ctx.send('No pokémons available in this channel.')
        
        pokemon, event = self.spawns[ctx.channel.id]
        names = (n.casefold() for n in pokemon.names if n is not None)

        if name.casefold() in names:
            level = random.randint(1, 50)
            await ctx.reply(f'You caught a level {level} {pokemon.default_name.title()}!!')

            await ctx.pool.user.add_pokemon(pokemon.id, level, 0)
            event.set()

            return self.spawns.pop(ctx.channel.id, None)

        await ctx.send('Wrong pokémon!')
    
    @commands.command()
    @commands.is_owner()
    async def spawn(self, ctx: Context, *, dex: int):
        pokemon = self.bot.pokedex.get_pokemon(dex)
        if pokemon is None:
            return await ctx.send('Not found.')

        embed = discord.Embed(title='Use p!catch <pokémon name> to catch the following pokémon.')
        embed.set_image(url='attachment://pokemon.png')
        
        file = discord.File(pokemon.image, filename='pokemon.png')
        await ctx.send(embed=embed, file=file)

        await self.wait(ctx.channel.id, pokemon)

    async def should_spawn(self, message: discord.Message):
        if not message.guild:
            return False

        if message.author.bot:
            return False

        guild = await self.bot.pool.get_guild(message.guild.id)
        if not guild:
            return False

        if guild.spawn_channel_id is not None:
            if guild.spawn_channel_id != message.channel.id:
                return False

        if not chance(SpawnRates.Global):
            return False
        
        return True

    def generate_rarity(self):
        if chance(SpawnRates.UltraBeast):
            return Rarity.UltraBeast
        elif chance(SpawnRates.Mythical):
            return Rarity.Mythical
        elif chance(SpawnRates.Legendary):
            return Rarity.Legendary

        return Rarity.Common

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if await self.should_spawn(message):
            rarity = self.generate_rarity()
            pokemon = self.bot.pokedex.random(rarity=rarity)

            embed = discord.Embed(title='Use p!catch <pokémon name> to catch the following pokémon.')
            embed.set_image(url=pokemon.image)

            await message.channel.send(embed=embed)
            await self.wait(message.channel.id, pokemon)
            
async def setup(bot: Pokecord):
    await bot.add_cog(Spawns(bot))