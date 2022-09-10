from typing import Callable, Dict, Tuple
import discord
from discord.ext import commands
import asyncio
import random

from src.utils.pokedex import PokedexEntry, Rarity, EvolutionCondition, EvolutionTime
from src.database.user import UserPokemon
from src.utils import Context, chance
from src.bot import Pokecord, SpawnRates

ChannelSpawn = Tuple[PokedexEntry, asyncio.Event, bool]

CATCH_REWARDS: Dict[int, Tuple[int, Callable[[PokedexEntry], str]]] = {
    0: (100, lambda _: 'Added to the pokédex, received 100 credits.'),
    9: (1000, lambda entry: f'This is your 10th {entry.default_name}, received 1000 credits.'),
    99: (10000, lambda entry: f'This is your 100th {entry.default_name}, received 10000 credits.')
}

class Spawns(commands.Cog):
    def __init__(self, bot: Pokecord) -> None:
        self.bot = bot
        self.spawns: Dict[int, ChannelSpawn] = {}

    def store_spawn(self, channel_id: int, pokemon: PokedexEntry, is_shiny: bool) -> asyncio.Event:
        event = asyncio.Event()
        self.spawns[channel_id] = (pokemon, event, is_shiny)

        return event

    async def wait(self, channel_id: int, pokemon: PokedexEntry, is_shiny: bool) -> None:
        event = self.store_spawn(channel_id, pokemon, is_shiny)

        try:
            await asyncio.wait_for(event.wait(), timeout=Pokecord.CHANNEL_SPAWN_TIMEOUT)
        except asyncio.TimeoutError:
            pass

        self.spawns.pop(channel_id, None)

    @commands.command(aliases=['c'])
    async def catch(self, ctx: Context, *, name: str):
        if not self.spawns.get(ctx.channel.id):
            return await ctx.send('No pokémons available in this channel.')
        
        pokemon, event, is_shiny = self.spawns[ctx.channel.id]
        names = (n.casefold() for n in pokemon.names if n is not None)

        if name.casefold() in names:
            self.spawns.pop(ctx.channel.id, None)
            level = random.randint(1, 50)

            fmt = f'Congratulations! You caught a level {level} {pokemon.default_name}. '
            count = await ctx.pool.user.get_catch_count_for(pokemon.id)
        
            amount, func = CATCH_REWARDS.get(count, (0, lambda _: ''))
            fmt += func(pokemon)
            
            if amount:
                await ctx.pool.user.add_credits(amount)

            if is_shiny:
                fmt += '\n\nThese colors seem unusual... ✨'

            await ctx.reply(fmt)
            await ctx.pool.user.add_pokemon(pokemon.id, level, 0, is_shiny)
        
            return event.set()

        await ctx.send('Wrong pokémon!')
    
    @commands.command()
    @commands.is_owner()
    async def spawn(self, ctx: Context, *, name: str):
        embed = discord.Embed(title='Use p!catch <pokémon name> to catch the following pokémon.', color=0x36E3DD)
        embed.set_image(url='attachment://pokemon.png')

        is_shiny = False
        if name.startswith('shiny'):
            name = name.removeprefix('shiny').strip()
            is_shiny = True

        entries = ctx.bot.pokedex.find(lambda entry: entry.default_name.casefold() == name.casefold())
        if not entries:
            return await ctx.send('Pokémon not found.')

        pokemon = entries[0]
        
        file = discord.File(pokemon.images.default, filename='pokemon.png')
        await ctx.send(embed=embed, file=file)

        await self.wait(ctx.channel.id, pokemon, is_shiny)

    async def should_spawn(self, message: discord.Message):
        if not message.guild:
            return False

        if message.author.bot:
            return False

        guild = await self.bot.pool.get_guild(message.guild.id)
        if not guild:
            return False

        if not guild.spawn_channel_ids:
            return False

        if not chance(SpawnRates.Global):
            return False
        
        return True

    def generate_rarity(self) -> Tuple[Rarity, bool]:
        if chance(SpawnRates.UltraBeast):
            return Rarity.UltraBeast, chance(SpawnRates.Shiny)
        elif chance(SpawnRates.Mythical):
            return Rarity.Mythical, chance(SpawnRates.Shiny)
        elif chance(SpawnRates.Legendary):
            return Rarity.Legendary, chance(SpawnRates.Shiny)

        return Rarity.Common, chance(SpawnRates.Shiny)

    def satisfies_all_evolution_conditions(
        self, pokemon: UserPokemon, level: int, entry: PokedexEntry
    ) -> bool:
        if entry.evolutions.at is not None:
            if level < entry.evolutions.at:
                return False

        cond = False
        for condition in entry.evolutions.conditions:
            if condition is EvolutionCondition.Time:
                assert entry.evolutions.time

                time = entry.evolutions.time
                if time is EvolutionTime.Day and self.bot.is_daytime():
                    cond = True
                elif time is EvolutionTime.Night and not self.bot.is_daytime():
                    cond = True
                else:
                    cond = False
            else:
                assert False, "Not Implemeneted"

        return cond

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.guild is None:
            return

        guild = await self.bot.pool.get_guild(message.guild.id)
        if await self.should_spawn(message):
            rarity, is_shiny = self.generate_rarity()

            pokemon = self.bot.pokedex.random(rarity=rarity)
            if not pokemon.enabled:
                return

            embed = discord.Embed(title='Use p!catch <pokémon name> to catch the following pokémon.', color=0x36E3DD)
           
            embed.set_image(url='attachment://pokemon.png')
            file = discord.File(pokemon.images.default, filename='pokemon.png')

            assert guild
            channel_id = random.choice(guild.spawn_channel_ids)

            channel = message.guild.get_channel(channel_id)
            assert isinstance(channel, discord.TextChannel)

            await channel.send(embed=embed, file=file)
            return await self.wait(channel.id, pokemon, is_shiny)

        user = await self.bot.pool.get_user(message.author.id)
        if not user:
            return

        assert guild
        if message.channel.id not in guild.exp_channel_ids:
            return

        selected = user.get_selected()
        if selected.level == 100:
            return

        increment = random.randint(1, 60)
        if (selected.exp + increment) >= self.bot.get_needed_exp(selected.level):
            level = selected.level + 1

            if selected.dex.evolutions.to:
                for evolution in selected.dex.evolutions.to:
                    entry = self.bot.pokedex.get_pokemon(evolution)
                    assert entry

                    if self.satisfies_all_evolution_conditions(
                        pokemon=selected,
                        level=level,
                        entry=entry
                    ):
                        return await selected.edit(level=level, exp=0, dex_id=entry.id)

            await selected.edit(level=level, exp=0)
        else:
            await selected.add_exp(increment)
        
            
async def setup(bot: Pokecord):
    await bot.add_cog(Spawns(bot))