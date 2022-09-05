from __future__ import annotations
import functools

from typing import ClassVar, List, NamedTuple
from discord.ext import commands
import json
import aiohttp
import enum
import discord
import importlib
import difflib
import sys
import random

from .utils import Pokedex, Context, ContextPool, print_with_color
from . import database

EVOLUTIONS = 'src/data/evolutions.json'
STARTERS = 'src/data/starters.json'
LEVELS = 'src/data/levels.json'
ULTRA_BEASTS = 'src/data/ultrabeasts.json'
NATURES = 'src/data/natures.json'
MEGAS = 'src/data/megas.json'
GIGAS = 'src/data/gigantamaxes.json'

class SpawnRates(enum.IntEnum):
    Global = 10000
    Shiny = 8192
    Legendary = 4000
    Mythical = 2000
    UltraBeast = 1200

class Nature(NamedTuple):
    name: str
    hp: int
    atk: int
    defense: int
    spatk: int
    spdef: int
    speed: int
    summary: str

class PosixFlags(commands.FlagConverter, prefix='--', delimiter=' '):
    pass

class Pokecord(commands.Bot):
    CHANNEL_SPAWN_TIMEOUT: ClassVar[float] = 60.0

    pool: database.Pool
    session: aiohttp.ClientSession

    def __init__(self):
        super().__init__(command_prefix='p!', intents=discord.Intents.all())

        self.load_data()

        self.ignored_commands = ('moves', 'pokedex', 'dex', 'starter')
        self.add_check(self.starter_check, call_once=True)

    @functools.lru_cache(maxsize=256)
    def get_close_matches(self, name: str):
        attrs = ('en', 'ja', 'ja_t', 'ja_t', 'fr')
        name = name.title()

        for attr in attrs:
            pokemons = self.pokedex.with_language(attr)
            matches = difflib.get_close_matches(name, pokemons.keys(), n=5, cutoff=0.5)

            if matches:
                return matches

        return []

    def generate_nature(self) -> str:
        return random.choice(list(self.natures.keys()))

    def get_nature(self, name: str):
        return self.natures.get(name)
        
    async def get_prefix(self, message: discord.Message):
        if not message.guild:
            return 'p!'

        assert self.user

        guild = await self.pool.add_guild(message.guild.id)
        return guild.prefix, self.user.mention

    def load_data(self):
        with open(EVOLUTIONS, 'r') as evolutions:
            self.evolutions = json.load(evolutions)

        with open(STARTERS, 'r') as starters:
            self.starters: List[str] = json.load(starters)

        with open(LEVELS, 'r') as levels:
            self.levels = json.load(levels)

        with open(NATURES, 'r') as natures:
            data = json.load(natures)
            self.natures = {
                name: Nature(name, **nature)
                for name, nature in data.items()
            }

        self.pokedex = Pokedex()
        print_with_color('{green}[INFO]{reset} Loaded pokedex data.')

    async def starter_check(self, ctx: Context):
        assert ctx.command and ctx.guild
        if ctx.command.name == 'set':
            return True

        guild = await self.pool.add_guild(ctx.guild.id)
        if not guild.spawn_channel_id:
            # await ctx.send(
            #     content=f'A spawn channel has not been set. Please set it using `{guild.prefix}set <channel>`.'
            # )
            ...

        if ctx.command.name in self.ignored_commands:
            return True

        user = await self.pool.get_user(ctx.author.id)
        if not user:
            await ctx.send(
                f'This command requires you to have a starter. Please start by inputing `{guild.prefix}starter`.'
            )
            return False

        ctx.pool = ContextPool(user, guild)
        return True

    def load_module(self, module: str):
        return importlib.import_module(module)

    def reload_module(self, module: str):
        try:
            mod = sys.modules[module]
        except KeyError:
            mod = importlib.import_module(module)

        return importlib.reload(mod)

    async def close(self) -> None:
        await self.pool.close()
        await self.session.close()

        return await super().close()

    async def get_context(self, message: discord.Message):
        return await super().get_context(message, cls=Context)
    