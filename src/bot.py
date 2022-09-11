from __future__ import annotations

from typing import ClassVar, Dict, List, NamedTuple
from discord.ext import commands, tasks
import json
import aiohttp
import enum
import discord
import importlib
import difflib
import sys
import random
import functools
import datetime
import logging

from .utils import Pokedex, Context, ContextPool, TTLDict
from .consts import DATA
from . import database

class SpawnRates(enum.IntEnum):
    Global = 10000
    Shiny = 8192
    Legendary = 4000
    UltraBeast = 2000
    Mythical = 1200

class Nature(NamedTuple):
    name: str
    hp: int
    atk: int
    defense: int
    spatk: int
    spdef: int
    speed: int
    summary: str

class LevelInformation(NamedTuple):
    needed: int
    total: int

class Pokecord(commands.Bot):
    CHANNEL_SPAWN_TIMEOUT: ClassVar[float] = 60.0
    TRADE_TIMEOUT: ClassVar[float] = 75.0
    REDEEM_CREDIT_AMOUNT: ClassVar[int] = 30000

    pool: database.Pool
    session: aiohttp.ClientSession
    levels: Dict[int, LevelInformation]

    def __init__(self, logger: logging.Logger):
        super().__init__(command_prefix='p!', intents=discord.Intents.all())
        
        self.logger = logger
        self.messages: TTLDict[str, discord.Message] = TTLDict(expiry=datetime.timedelta(seconds=60))
        self.ignored_commands = ('starter',)

        self._is_day = False

        self.load_data()
        self.add_check(self.starter_check, call_once=True)


    @functools.lru_cache(maxsize=256)
    def get_close_matches(self, name: str):
        attrs = ('en', 'ja', 'ja_t', 'ja_t', 'fr')
        for attr in attrs:
            pokemons = self.pokedex.with_language(attr)
            matches = difflib.get_close_matches(name, pokemons.keys(), n=5, cutoff=0.5)

            if matches:
                return matches

        return []

    @tasks.loop(minutes=1)
    async def update_time(self) -> None:
        now = datetime.datetime.utcnow()
        self._is_day = 23 > now.hour > 7

    def is_daytime(self) -> bool:
        return self._is_day

    def add_message(self, key: str, message: discord.Message) -> None:
        self.messages[key] = message

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
        with (DATA / 'evolutions.json').open('r') as evolutions:
            self.evolutions = json.load(evolutions)

        with (DATA / 'starters.json').open('r') as starters:
            self.starters: List[str] = json.load(starters)

        with (DATA / 'levels.json').open('r') as levels:
            levels = json.load(levels)
            self.levels = {
                int(key): LevelInformation(value['needed'], value['total']) for key, value in levels.items()
            }

        with (DATA / 'natures.json').open('r') as natures:
            natures = json.load(natures)
            self.natures = {name: Nature(name, **nature) for name, nature in natures.items()}

        self.pokedex = Pokedex()
        self.logger.info('Loaded pokedex data.')

    def get_needed_exp(self, level: int) -> int:
        return self.levels[level].needed

    async def starter_check(self, ctx: Context):
        assert ctx.command and ctx.guild
        if ctx.command.name == 'set':
            return True

        guild = await self.pool.add_guild(ctx.guild.id)
        if ctx.command.name in self.ignored_commands:
            return True

        user = await self.pool.get_user(ctx.author.id)
        if not user:
            await ctx.send(
                f'This command requires you to have a pokémon. Please start by invoking `{guild.prefix}starter`.'
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

    async def start(self, token: str, *, reconnect: bool = True) -> None:
        self.update_time.start()
        return await super().start(token, reconnect=reconnect)

    async def get_context(self, message: discord.Message):
        return await super().get_context(message, cls=Context)

    async def on_command_error(self, context: Context, exception: commands.CommandError, /):
        if isinstance(exception, (commands.CheckFailure, commands.CommandNotFound)):
            return

        if isinstance(exception, commands.BadArgument):
            return await context.send(''.join(exception.args))

        raise getattr(exception, 'original', exception)
    
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        await self.process_commands(after)
    