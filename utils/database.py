import random
import asyncpg
import asyncio
import json
from typing import (
    Any, 
    Dict, 
    Generic, 
    Mapping, 
    Optional, 
    Tuple, 
    List, 
    TypeVar, 
    Union, 
    TYPE_CHECKING,
    Generator
)
import discord

from .calc import get_ivs, _round

if TYPE_CHECKING:
    from bot import Pokecord

_T = TypeVar('_T')

class AsyncIterator(Generic[_T]):
    def __init__(self, future: asyncio.Future[List], pool: 'Pool', bot: 'Pokecord') -> None:
        self.future = future
        self.pool = pool
        self.bot = bot
        self.records = []
        self.index = 0

    def __await__(self) -> Generator[Any, None, List[_T]]:
        return self.future.__await__()

    def __aiter__(self):
        return self

    async def __anext__(self) -> _T:
        await self.future

        if self.future.done():
            self.records = self.future.result()

        try:
            record = self.records[self.index]
            return record
        except IndexError:
            raise StopAsyncIteration
        finally:
            self.index += 1

class Nature:
    def __init__(self, data: Mapping[str, Any], name: str) -> None:
        self.name = name

        self.health: int = data['hp']
        self.attack: int = data['atk']
        self.defense: int = data['def']
        self.spattack: int = data['spatk']
        self.spdefense: int = data['spdef']
        self.speed: int = data['speed']

class Ivs:
    def __init__(self, data: Mapping[str, Any]) -> None:
        self.rounded: int = data['rounded']

        self.health: int = data['hp']
        self.attack: int = data['attack']
        self.defense: int = data['defense']
        self.spattack: int = data['spatk']
        self.spdefense: int = data['spdef']
        self.speed: int = data['speed']

class Moves:
    def __init__(self, data: Mapping[str, str]) -> None:
        self.first: str = data['1']
        self.second: Optional[str] = data['2']
        self.third: Optional[str] = data['3']
        self.fourth: Optional[str] = data['4']

        self._iter = iter(tuple(data))

    def __iter__(self):
        return self

    def __next__(self):
        return next(self._iter)

class Pokemon:
    def __init__(self, data: Mapping[str, Any], bot: 'Pokecord', user: 'User') -> None:
        self._data = data
        self.bot = bot
        self.user = user

        self._nature = self.bot.natures[data['nature']]

        self.name: str = data['name']
        self.id: int = data['id']
        self.experience: int = data['exp']
        self.level: int = data['level']

    @property
    def nature(self):
        return Nature(self._nature, self._data['nature'])

    @property
    def ivs(self):
        return Ivs(self._data['ivs'])

    @property
    def moves(self):
        return Moves(self._data['moves'])

    @property
    def data(self):
        return {'pokemon': self._data}

class Model:
    def __init__(self, record: asyncpg.Record, pool: 'Pool', bot: 'Pokecord') -> None:
        self.record = record
        self.pool = pool
        self.bot = bot

    def __repr__(self) -> str:
        name = self.__class__.__name__
        return f'<{name} id={self.id}>'

    @property
    def id(self):
        name = self.__class__.__name__.lower()
        return self.record[name + '_id']

    async def fetch(self):
        raise NotImplementedError

    async def refetch(self):
        raise NotImplementedError

class User(Model):

    @property
    def pokemons(self) -> List[Pokemon]:
        return [Pokemon(pokemon['pokemon'], self.bot, self) for pokemon in json.loads(self.record['pokemons'])]

    @property
    def entries(self) -> List[Dict]:
        return json.loads(self.record['pokemons'])

    @property
    def balance(self) -> int:
        return self.record['credits']

    @property
    def current_id(self) -> int:
        return self.record['current_id']

    @property
    def selected(self) -> int:
        return self.record['selected']

    async def fetch(self):
        user = self.bot.get_user(self.id)
        if not user:
            try:
                user = await self.bot.fetch_user(self.id)
            except (discord.NotFound, discord.HTTPException):
                user = None

        return user

    async def refetch(self):
        user = await self.pool.get_user(self.id)
        return user

    def get_pokemon_by_id(self, id: int) -> Tuple[Optional[Pokemon], List[Pokemon]]:
        copy = self.entries.copy()

        for pokemon in self.pokemons:
            other = pokemon.id

            if other == id:
                return pokemon, copy

        return None, copy

    def get_pokemon_by_name(self, name: str) -> Tuple[Optional[Pokemon], List[Pokemon]]:
        copy = self.entries.copy()

        for pokemon in self.pokemons:
            other = pokemon.name

            if other.lower() == name.lower():
                return pokemon, copy

        return None, copy

    def get_selected(self) -> Tuple[Optional[Pokemon], List[Pokemon]]:
        return self.get_pokemon_by_id(self.selected)

    def get_pokemon_moves(self, id: Union[int, str]) -> Moves:
        if isinstance(id, str):
            entry, entries = self.get_pokemon_by_name(id)

        if isinstance(id, int):
            entry, entries = self.get_pokemon_by_id(id)

        return entry.moves

    def get_selected_moves(self) -> Moves:
        entry, _ = self.get_selected()
        return entry.moves

    async def update_pokemons(self, data: List[Dict]):
        entries = json.dumps(data)

        async with self.pool.acquire() as conn:
            await conn.execute('UPDATE users SET pokemons = $1 WHERE user_id = $2', entries, self.id)
            return data

    async def add_pokemon(self, name: str, level: int, exp: int):
        id = await self.get_next_pokemon_id()
        ivs, rounded = get_ivs()
        copy = self.pokemons.copy()

        data = {
            'pokemon': {
                'name': name,
                'level': level,
                'id': id,
                'exp': exp,
                'ivs': {
                    'rounded': rounded,
                    'hp': ivs[0],
                    'attack': ivs[1],
                    'defense': ivs[2],
                    'spatk': ivs[3],
                    'spdef': ivs[4],
                    'speed': ivs[5],
                },
                'moves': {
                    '1': 'tackle',
                    '2': None,
                    '3': None,
                    '4': None
                },
                'nature': random.choice(list(self.bot.natures.values()))
            }
        }

        copy.append(data)
        await self.update_pokemons(copy)

    async def edit_pokemon(self, name: str, id: int, level: int, ivs: List[int]) -> None:
        rounded = _round(ivs)

        entry, entries = self.get_pokemon_by_id(id)
        entries.remove(entry.data)

        entry._data['name'] = name
        entry._data['level'] = level
        entry._data['exp'] = 0
        entry._data['ivs'] = {
            'rounded': rounded,
            'hp': ivs[0],
            'attack': ivs[1],
            'defense': ivs[2],
            'spatk': ivs[3],
            'spdef': ivs[4],
            'speed': ivs[5]
        }

        entries.append(entry.data)
        await self.update_pokemons(entries)

    async def update_pokemon(self, name: str, level: int) -> None:
        entry, entries = self.get_selected()
        entries.remove(entry.data)

        entry._data['name'] = name
        entry._data['exp'] = 0
        entry._data['level'] = level

        entries.append(entry.data)
        await self.update_pokemons(entries)

    async def update_pokemon_move(self, id: str, move: str):
        entry, entries = self.get_selected()
        entries.remove(entry.data)

        entry._data['moves'][id] = move
        entries.append(entry)

        await self.update_pokemons(entries)

    async def update_pokemon_nature(self, nature: str):
        entry, entries = self.get_selected()

        entries.remove(entry.data)
        entry._data['nature'] = nature.capitalize()

        entries.append(entry.data)
        await self.update_pokemons(entries)

    async def remove_pokemon(self, id: Union[str, int]):
        if isinstance(id, str):
            entry, entries = self.get_pokemon_by_name(id)
            id = entry.id

        if isinstance(id, int):
            entry, entries = self.get_pokemon_by_id(id)

        entries.remove(entry.data)
        new = await self.get_last_pokemon_id()

        if self.selected == id:
            await self.change_selected(new)

        await self.update_pokemons(entries)
        await self.change_all_ids(id)

    async def update_level(self, level: int):
        entry, entries = self.get_selected()
        entries.remove(entry.data)

        entry._data['level'] = level
        entries.append(entry.data)

        await self.update_pokemons(entries)

    def get_level(self) -> int:
        entry, entries = self.get_selected()
        return entry.level

    async def add_experience(self, exp: int):
        entry, entries = self.get_selected()
        entries.remove(entry.data)

        entry._data['exp'] += exp
        entries.append(entry.data)

        await self.update_pokemons(entries)

    def get_experience(self) -> int:
        entry, entries = self.get_selected()
        return entry.experience

    def get_pokemon_experience(self, id: Union[str, int]):
        if isinstance(id, str):
            entry, _ = self.get_pokemon_by_name(id)
            return entry.experience

        entry, _ = self.get_pokemon_by_id(id)
        return entry.experience

    async def change_selected(self, id: int):
        async with self.pool.acquire() as conn:
            await conn.execute('UPDATE users SET selected = $1 WHERE user_id = $2', id, self.id)
            return id

    async def change_all_ids(self, thrown: int):
        user = await self.refetch()
        entries = user.pokemons.copy()

        for entry in entries:
            if int(entry['id']) > thrown:
                entry['id'] = entry['id'] - 1

        await user.update_pokemons(entries)

    async def get_next_pokemon_id(self) -> int:
        async with self.pool.acquire() as conn:
            new_id = self.current_id + 1

            await conn.execute('UPDATE users SET current_id = $1 WHERE user_id = $2', new_id, self.id)
            return new_id

    async def get_last_pokemon_id(self) -> int:
        user = await self.refetch()

        async with self.pool.acquire() as conn:
            new = user.current_id - 1

            await conn.execute('UPDATE users SET current_id = $1 WHERE user_id = $2', new, self.id)
            return new

    async def add_to_balance(self, amount: int):
        new = self.balance + amount

        async with self.pool.acquire() as conn:
            await conn.execute('UPDATE users SET credits = $1 WHERE user_id = $2', new, self.id)
            return new

    async def remove_from_balance(self, amount: int):
        new = self.balance - amount

        async with self.pool.acquire() as conn:
            await conn.execute('UPDATE users SET credits = $1 WHERE user_id = $2', new, self.id)
            return new

class Guild(Model):

    @property
    def spawn_channel_id(self) -> int:
        return self.record['channel_id']

    @property
    def prefix(self) -> str:
        return self.record['prefix']

    async def fetch(self):
        guild = self.bot.get_guild(self.id)
        if not guild:
            try:
                guild = await self.bot.fetch_guild(self.id)
            except (discord.NotFound, discord.HTTPException):
                guild = None

        return guild

    async def refetch(self):
        guild = await self.pool.get_guild(self.id)
        return guild

    async def fetch_spawn_channel(self) -> Optional[discord.TextChannel]:
        guild = await self.fetch()
        channel = guild.get_channel(self.spawn_channel_id)

        if not channel:
            try:
                channel = await self.bot.fetch_channel(self.spawn_channel_id)
            except (discord.Forbidden, discord.NotFound, discord.HTTPException):
                channel = None

        return channel

    async def update_spawn_channel(self, channel_id: int):
        async with self.pool.acquire() as conn:
            await conn.execute('UPDATE guilds SET channel_id = $1 WHERE guild_id = $2', channel_id, self.id)
            return channel_id

    async def update_prefix(self, prefix: str):
        async with self.pool.acquire() as conn:
            await conn.execute('UPDATE guilds SET prefix = $1 WHERE guild_id = $2', prefix, self.id)
            return prefix

class Pool:
    def __init__(self, __pool: asyncpg.Pool, __bot: 'Pokecord') -> None:
        self.__pool = __pool
        self.bot = __bot

    def acquire(self):
        return self.__pool.acquire()

    async def close(self):
        return await self.__pool.close()

    async def execute(self, query: str, *args):
        async with self.acquire() as conn:
            ret = await conn.execute(query, *args)
            return ret

    async def fetch(self, query: str, *args):
        async with self.acquire() as conn:
            ret = await conn.fetch(query, *args)
            return ret

    async def fetchrow(self, query: str, *args):
        async with self.acquire() as conn:
            ret = await conn.fetchrow(query, *args)
            return ret

    async def add_user(self, user_id: int, name: str) -> Optional[bool]:
        ivs, rounded = get_ivs()
        data = [
            {
                'pokemon': {
                    'name': name,
                    'level': 1,
                    'id': 1,
                    'exp': 0,
                    'ivs': {
                        'rounded': rounded,
                        'hp': ivs[0],
                        'attack': ivs[1],
                        'defense': ivs[2],
                        'spatk': ivs[3],
                        'spdef': ivs[4],
                        'speed': ivs[5]
                    },
                    'moves': {
                        '1': 'tackle',
                        '2': None,
                        '3': None,
                        '4': None
                    },
                    'nature': random.choice(list(self.bot.natures.keys()))
                }
            }
        ]
        
        async with self.acquire() as conn:
            user = await conn.fetchrow('SELECT * from users WHERE user_id = $1', user_id)
            if not user:
                await conn.execute(
                    'INSERT INTO users(credits, pokemons, current_id, user_id, selected) VALUES ($1, $2, $3, $4, $5)',
                    100, json.dumps(data), 1, user_id, 1)
                return

            return True

    async def get_user(self, user_id: int) -> User:
        async with self.acquire() as conn:
            user = await conn.fetchrow('SELECT * FROM users WHERE user_id = $1', user_id)
            if not user:
                return None

            return User(user, self, self.bot)

    async def _users(self) -> List[User]:
        records = await self.fetch('SELECT * FROM users')
        users = []

        for record in records:
            user = User(record, self, self.bot)
            users.append(user)

        return users

    def users(self) -> AsyncIterator[User]:
        future = asyncio.ensure_future(self._users())
        return AsyncIterator(future, self, self.bot)

    async def add_guild(self, guild_id: int, channel_id: int=None, prefix: str='p!') -> None:
        async with self.acquire() as conn:
            guild = await conn.fetchrow('SELECT * from guilds WHERE guild_id = $1', guild_id)
            query = ('INSERT INTO guilds(guild_id, prefix) VALUES ($1, $2)', guild_id, prefix)

            if channel_id:
                query = ('INSERT INTO guilds(guild_id, channel_id, prefix VALUES($1, $2, $3)', guild_id, channel_id, prefix)

            if not guild:
                await conn.execute(*query)

            return None

    async def get_guild(self, guild_id: int) -> Guild:
        async with self.acquire() as conn:
            guild = await conn.fetchrow('SELECT * FROM guilds WHERE guild_id = $1', guild_id)
            if not guild:
                return None

            return Guild(guild, self, self.bot)

    async def _guilds(self) -> List[Guild]:
        records = await self.fetch('SELECT * FROM guilds')
        guilds = []

        for record in records:
            guild = Guild(record, self, self.bot)
            guilds.append(guild)

        return guilds

    def guilds(self) -> AsyncIterator[Guild]:
        future = asyncio.ensure_future(self._guilds())
        return AsyncIterator(future, self, self.bot)

async def connect(dns: str, *, bot: 'Pokecord'):
    pool = await asyncpg.create_pool(dns)
    return Pool(pool, bot)