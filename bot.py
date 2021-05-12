import asyncio
import typing
import json
import aiohttp
from discord.ext import commands
import discord
from dataclasses import dataclass
import importlib
import sys

import wrapper
from utils.context import Context
from utils import database

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
 
URL = 'postgres://postgres:adamelkan@localhost:5432/postgres'

@dataclass
class ParseResult:
    name: str
    shiny: bool
    mega: bool
    primal: bool
    x: bool
    y: bool
    black: bool
    white: bool
    alolan: bool
    galarian: bool
    ultra: bool

class Pokemons(typing.Dict[str, wrapper.Pokemon]):
    def getall(self):
        return list(self.values())

class Pokedex(typing.Dict[int, wrapper.Pokemon]):
    def getall(self):
        return list(self.values())

class Pokecord(commands.Bot):
    def __init__(self, *args, **options):
        self.load_data()

        self.loaded_once = False
        self.session = aiohttp.ClientSession()

        super().__init__(*args, **options, intents=discord.Intents.all())

        self.all_extensions = [
            'cogs.pokemons',
            'cogs.owner',
            'cogs.pokedex',
            'cogs.spawns',
            'cogs.shop',
            'cogs.events',
            'cogs.duels'
        ]

        self.global_spawn_chance = 100000
        self.shiny_spawn_rate = 8192
        self.legendary_spawn_rate = 4000
        self.mythical_spawn_rate = 2000
        self.ub_spawn_rate = 1200

        self.pokemons = Pokemons()
        self.pokedex = Pokedex()

        for cog in self.all_extensions:
            self.load_extension(cog)

        self.ignored_commands = (
            'moves',
            'pokedex',
            'dex',
            'starter'
        )

        self.add_check(self.starter_check, call_once=True)

    def get_commons(self):
        commons = []

        for name in self.names:
            if name in self.legendaries:
                continue
                
            if name in self.mythicals:
                continue

            if name in self.ultrabeasts:
                continue

            commons.append(name)

        with open('data/commons.json', 'w') as file:
            json.dump(commons, file, indent=4)
        
    async def get_prefix(self, message: discord.Message):
        guild = await self.pool.get_guild(message.guild.id)
        return (guild.prefix, self.user.mention + ' ', '<@!%s> ' % self.user.id)

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
                content='A spawn channel has not been set. Please set it using `p!set <channel>`.'
            )

        if ctx.command.name in self.ignored_commands:
            return True

        user = await self.pool.get_user(ctx.author.id)
        if not user:
            await ctx.send('This operation requires you to have a stater. Please start by inputing `p!starter`.')
            return False

        return True

    async def _load_pokemon(self, name: str):
        try:
            pokemon = await wrapper.get_pokemon(name, session=self.session)
        except:
            return None

        self.pokemons[pokemon.name] = pokemon
        self.pokedex[pokemon.dex] = pokemon

        return pokemon

    async def load_pokemon(self, dex: typing.Union[str, int]):
        if isinstance(dex, str):
            dex = dex.lower()
            dex = self.parse_pokemon(dex).name

        return await self._load_pokemon(dex)

    async def load_all_pokemons(self):
        coros = []

        for name in self.names:
            coro = self._load_pokemon(name)
            coros.append(coro)

        return await asyncio.gather(*coros)

    async def fetch_pokemon(self, dex: typing.Union[str, int]):
        shiny = False

        if isinstance(dex, str) and not dex.isdigit():
            parsed = self.parse_pokemon(dex)
            pokemon = self.pokemons.get(parsed.name)

            search = parsed.name
            shiny = parsed.shiny

        else:
            pokemon = self.pokedex.get(dex)
            search = dex
        
        if not pokemon:
            pokemon = await self.load_pokemon(search)

        return pokemon, shiny

    async def get_moves(self, pokemon: wrapper.Pokemon):
        moves = await pokemon.get_moves()
        actual = []

        for move in moves:
            if move.damage_class == 'status':
                continue
            
            actual.append(move)

        return actual

    def _parse_name(self, parts):
        if len(parts) == 2:
            name = parts[1]

        elif len(parts) == 3:
            name = parts[1]
        
        elif len(parts) == 4:
            name = parts[2]

        else:
            name = parts[0]
        
        return name

    def parse_pokemon(self, name: str):
        is_mega = False
        is_primal = False
        is_black = False
        is_white = False
        is_shiny = False
        is_alolan = False
        is_galarian = False
        is_ultra = False
        is_dusk = False
        is_dawn = False
        is_origin = False
        is_eternamax = False
        is_altered = False
        is_unbound = False
        is_gmax = False
        is_x = False
        is_y = False

        name = name.lower()
        original = name

        parts = name.split(' ')
        name = self._parse_name(parts)

        if original == 'dusk mane necrozma' or original == 'dawn wings necrozma':
            name = 'necrozma'

        if parts[0] == 'shiny':
            is_shiny = True

        if parts[-1] == 'origin':
            is_origin = True
        else:
            is_altered = True

        if parts[-1] == 'x':
            is_x = True

        if parts[-1] == 'y':
            is_y = True

        if len(parts) == 3 or len(parts) == 2:
            if parts[0] == 'mega' or parts[1] == 'mega':
                is_mega = True

            if parts[0] == 'primal' or parts[1] == 'primal':
                is_primal = True

            if parts[0] == 'black' or parts[1] == 'black':
                is_black = True

            if parts[0] == 'white' or parts[1] == 'white':
                is_white = True      

            if parts[0] == 'alolan' or parts[1] == 'alolan':
                is_alolan = True  

            if parts[0] == 'galarian' or parts[1] == 'galarian':
                is_galarian = True 

            if parts[0] == 'ultra' or parts[1] == 'ultra':
                is_ultra = True

            if parts[0] == 'unbound' or parts[1] == 'unbound':
                is_unbound = True

            if parts[0] == 'eternamax' or parts[1] == 'eternamax':
                is_eternamax = True

            if parts[0] == 'gigantamax' or parts[1] == 'gigantamax':
                is_gmax = True

        if len(parts) == 3:
            if parts[0] == 'dusk' and parts[1] == 'mane':
                is_dusk = True  

            if parts[0] == 'dawn' and parts[1] == 'wings':
                is_dawn = True  

        if len(parts) == 4:
            if parts[1] == 'mega':
                is_mega = True

        parsed = self._get_parsed_name(
            name=name,
            mega=is_mega,
            x=is_x,
            y=is_y,
            primal=is_primal,
            black=is_black,
            white=is_white,
            ultra=is_ultra,
            dawn=is_dawn,
            dusk=is_dusk,
            origin=is_origin,
            unbound=is_unbound,
            etenermax=is_eternamax,
            gmax=is_gmax
        )

        if parts[0] == 'deoxys':
            idx = parts.index('deoxys')
            name = parts[idx]

            parsed = name + '-' + parts[1]

        if parts[0] == 'giratina':
            idx = parts.index('giratina')
            name = parts[idx]

            if is_altered:
                parsed = name + '-altered'

            if is_origin:
                parsed = name + '-origin'

        return ParseResult(
            name=parsed,
            shiny=is_shiny,
            mega=is_shiny,
            primal=is_primal,
            x=is_x,
            y=is_y,
            black=is_black,
            white=is_white,
            alolan=is_alolan,
            galarian=is_galarian,
            ultra=is_ultra
        ) 

    def _get_parsed_name(self, 
                        name: str,
                        mega: bool,
                        x: bool,
                        y: bool,
                        primal: bool,
                        black: bool,
                        white: bool,
                        ultra: bool,
                        dawn: bool,
                        dusk: bool,
                        origin: bool,
                        unbound: bool,
                        etenermax: bool,
                        gmax: bool,):

        parsed = name

        if mega:
            parsed += '-mega'
            if x:
                parsed += '-x'

            if y:
                parsed += '-y'

        if primal:
            parsed += '-primal'

        if black:
            parsed += '-black'

        if white:
            parsed += '-white'

        if ultra:
            parsed += '-ultra'

        if dawn:
            parsed += '-dawn'

        if dusk:
            parsed += '-dusk'

        if origin:
            parsed += '-origin'

        if unbound:
            parsed += '-unbound'

        if etenermax:
            parsed += '-eternamax'

        if gmax:
            parsed += '-gmax'

        return parsed

    def _parse_pokemon(self, name: str):
        parts = name.split('-')
        
        if len(parts) == 3:
            name = parts[1] + ' ' + parts[0] + ' ' + parts[-1]

        if len(parts) == 2:
            name = parts[1] + ' ' + parts[0]

        else:
            name = parts[0]

        return name

    def _get_ivs(self, data):
        rounded = data['rounded']

        hp = data['hp']
        attack = data['attack']
        defense = data['defense']
        spatk = data['spatk']
        spdef = data['spdef']
        speed = data['speed']

        return rounded, hp, attack, defense, spatk, spdef, speed
    
    def load_module(self, module: str):
        try:
            return self.load_extension(module)
        except commands.ExtensionNotFound:
            pass
            
        mod = importlib.import_module(module)
        return mod

    def reload_module(self, module: str):
        try:
            return self.reload_extension(module)
        except (commands.ExtensionNotFound, commands.ExtensionNotLoaded):
            pass

        try:
            mod = sys.modules[module]
        except KeyError:
            mod = importlib.import_module(module)

        return importlib.reload(mod)

    async def start(self, *args, **kwargs):
        # waiter = self.loop.create_task(self.load_all_pokemons())
        self.pool = await database.connect(URL, bot=self)
        
        async with self.pool.acquire() as conn:
            version = await conn.fetchval('SELECT version()')
            print(version)

        await super().start(*args, **kwargs)

    async def close(self) -> None:
        await self.pool.close()
        return await super().close()

    async def get_context(self, message):
        return await super().get_context(message, cls=Context)

bot = Pokecord('p!')

@bot.event
async def on_ready():
    if not bot.loaded_once:
        for guild in bot.guilds:
            await bot.pool.add_guild(guild.id)

        bot.loaded_once = True

    print('Bot is ready.')

@bot.event
async def on_guild_join(guild: discord.Guild):
    await bot.pool.add_guild(guild.id)

bot.run('NzYzNzc0NDgxNTU0NDczMDAx.X38mag.b8tNypJfVchkXQjk9cUi37EuZTw')