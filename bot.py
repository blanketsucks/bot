import asyncio
from inspect import isclass
from types import ModuleType
import typing
import json
import aiohttp
import enum
from discord.ext import commands
import discord
import importlib
import difflib
import sys

import wrapper
import config
from cogs.help import HelpCommand
from utils.context import Context
from utils.models import get_pokemons
import database

EVOLUTIONS = 'data/evolutions.json'
LEGENDARIES = 'data/legendaries.json'
MYTHICALS = 'data/mythicals.json'
NAMES = 'data/names.json'
STARTERS = 'data/starters.json'
LEVELS = 'data/levels.json'
COMMONS = 'data/commons.json'
ULTRA_BEASTS = 'data/ultrabeasts.json'
NATURES = 'data/natures.json'
MEGAS = 'data/megas.json'
GIGAS = 'data/gigantamaxes.json'

def get_event_loop():
    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.get_event_loop()

class SpawnRates(enum.IntEnum):
    GLOBAL = 10000
    SHINY = 8192
    LEGENDARY = 4000
    MYTHICAL = 2000
    ULTRA_BEAST = 1200

class Rarity(enum.IntEnum):
    COMMON = 3
    ULTRA_BEAST = 2
    MYTHICAL = 1
    LEGENDARY = 0

class Pokecord(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix='p!',
            help_command=HelpCommand(),
            loop=get_event_loop(),
            intents=discord.Intents.all()
        )

        self.load_data()
        self.session = aiohttp.ClientSession()

        self.all_extensions = [
            'cogs.pokemons',
            'cogs.owner',
            'cogs.pokedex',
            'cogs.spawns',
            'cogs.shop',
            'cogs.events',
            'cogs.duels',
            'cogs.market'
        ]

        for cog in self.all_extensions:
            self.load_extension(cog)

        self.ignored_commands = (
            'moves',
            'pokedex',
            'dex',
            'starter'
        )

        self.add_check(self.starter_check, call_once=True)
        self.loop.create_task(
            coro=self.load_guilds()
        )

    async def load_guilds(self):
        await self.wait_until_ready()

        for guild in self.guilds:
            await self.pool.add_guild(guild.id)

    def get_close_matches(self, name: str):
        attrs = ('en', 'ja', 'ja_t', 'ja_t', 'fr')

        for attr in attrs:
            keys = getattr(self.pokedex, attr).keys()
            matches = difflib.get_close_matches(name, keys)
            if matches:
                return matches

        return []
        
    async def get_prefix(self, message: discord.Message):
        guild = await self.pool.get_guild(message.guild.id)
        return (guild.prefix, self.user.mention + ' ', '<@!%s> ' % self.user.id)

    def increment_market_id(self):
        with open('market.json', 'r') as f:
            data = json.load(f)

        current_id = data['current_id'] + 1
        data['current_id'] = current_id

        with open('market.json', 'w') as f:
            json.dump(data, f)

        self.current_market_id = current_id

    def load_data(self):
        with open(EVOLUTIONS, 'r') as evolutions:
            self.evolutions = json.load(evolutions)

        with open(LEGENDARIES, 'r') as legendaries:
            self.legendaries = json.load(legendaries)

        with open(MYTHICALS, 'r') as mythicals:
            self.mythicals = json.load(mythicals)

        with open(NAMES, 'r') as names:
            self.names = json.load(names)

        with open(STARTERS, 'r') as starters:
            self.starters = json.load(starters)

        with open(LEVELS, 'r') as levels:
            self.levels = json.load(levels)

        with open(ULTRA_BEASTS, 'r') as ubs:
            self.ultrabeasts = json.load(ubs)

        with open(COMMONS, 'r') as commons:
            self.commons = json.load(commons)

        with open(NATURES, 'r') as natures:
            self.natures = json.load(natures)

        with open(MEGAS, 'r') as megas:
            self.megas = json.load(megas)

        with open(GIGAS) as gigas:
            self.gigas = json.load(gigas)

        self.pokedex = get_pokemons()

        with open('market.json', 'r') as f:
            self.current_market_id: int = json.load(f)['current_id']

    def get_nature_name(self, data: typing.Mapping[str, str]) -> typing.Optional[str]:
        for key, item in self.natures.items():
            if item == data:
                return key

        return None

    async def starter_check(self, ctx: commands.Context):
        if ctx.command.name == 'set':
            return True

        guild = await self.pool.get_guild(ctx.guild.id)
        if not guild.spawn_channel_id:
            await ctx.send(
                content=f'A spawn channel has not been set. Please set it using `{guild.prefix}set <channel>`.'
            )

        if ctx.command.name in self.ignored_commands:
            return True

        user = await self.pool.get_user(ctx.author.id)
        if not user:
            await ctx.send(
                f'This operation requires you to have a stater. Please start by inputing `{guild.prefix}starter`.'
            )
            return False

        return True

    async def get_moves(self, pokemon: wrapper.Pokemon):
        moves = await pokemon.get_moves()
        actual = []

        for move in moves:
            if move.damage_class == 'status':
                continue
            
            actual.append(move)

        return actual

    async def parse_pokemon_argument(self, ctx: Context, argument: str):
        user = await ctx.bot.pool.get_user(ctx.author.id)

        if not argument:
            pokemon, _ = user.get_selected()
            return pokemon, _

        if argument.isdigit() or isinstance(argument, int):
            id = int(argument)
            pokemon, _ = user.get_pokemon_by_id(id)

            return pokemon, _

        if argument.lower() in ('l', 'latest'):
            id = user.get_last_pokemon_id()
            pokemon, _ = user.get_pokemon_by_id(id)

            return pokemon, _

        pokemon, _ = user.get_pokemon_by_name(argument)
        return pokemon, _

    def find_cog(self, module: ModuleType) -> typing.Type[commands.Cog]:
        for item, value in module.__dict__.items():
            if isclass(value):
                if issubclass(value, commands.Cog):
                    return value

    def load_extension(self, name: str):
        try:
            return super().load_extension(name)
        except commands.NoEntryPointError:
            pass
        
        module = self.load_module(name)
        cog = self.find_cog(module)

        self.add_cog(cog(self))
        return cog
    
    def load_module(self, module: str):
        mod = importlib.import_module(module)
        return mod

    def reload_module(self, module: str):
        try:
            mod = sys.modules[module]
        except KeyError:
            mod = importlib.import_module(module)

        return importlib.reload(mod)

    async def start(self, *args, **kwargs):
        self.pool = await database.connect(config.PG_URL, bot=self)
        
        async with self.pool.acquire() as conn:
            version = await conn.fetchval('SELECT version()')
            print(version)

        await super().start(*args, **kwargs)

    async def close(self) -> None:
        await self.pool.close()
        return await super().close()

    async def get_context(self, message):
        context = await super().get_context(message, cls=Context)
        return context
    
    def is_in_duel(self, user: typing.Union[int, discord.User, discord.Member]):
        id = user
        if isinstance(user, (discord.User, discord.Member)):
            id = user.id

        cog = self.get_cog('duels')
        if id in cog.duels:
            return True

        return False
        
bot = Pokecord()

@bot.event
async def on_guild_join(guild: discord.Guild):
    await bot.pool.add_guild(guild.id)

bot.run(config.TOKEN)