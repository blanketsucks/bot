import asyncpg
import json

import typing
from typing import Any, Mapping, Optional, Tuple, List

from .calc import get_ivs, _round

if typing.TYPE_CHECKING:
    from bot import Pokecord

Pokemon = Mapping[str, Any]

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

    async def fetchone(self, query: str, *args):
        async with self.acquire() as conn:
            ret = await conn.fetchval(query, *args)
            return ret

    async def cursor(self, query: str, *args):
        async with self.acquire() as conn:
            cursor = await conn.cursor(query, *args)
            return cursor

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
                    }
                }
            }
        ]
        
        async with self.acquire() as conn:
            user = await conn.fetch('SELECT * from users WHERE user_id = $1', user_id)
            if not user:
                await conn.execute(
                    'INSERT INTO users(credits, pokemons, current_id, user_id, selected) VALUES ($1, $2, $3, $4, $5)',
                    100, json.dumps(data), 1, user_id, 1)
                return

            return True

    async def get_user(self, user_id: int) -> asyncpg.Record:
        async with self.acquire() as conn:
            user = await conn.fetchrow('SELECT * FROM users WHERE user_id = $1', user_id)
            return user

    async def get_next_id(self, user_id: int) -> int:
        async with self.acquire() as conn:
            id = await conn.fetchval('SELECT current_id FROM users WHERE user_id = $1', user_id)
            new_id = id + 1

            await conn.execute('UPDATE users SET current_id = $1 WHERE user_id = $2', new_id, user_id)
            return new_id

    async def get_current_id(self, user_id: int) -> int:
        async with self.acquire() as conn:
            id = await conn.fetchval('SELECT current_id FROM users WHERE user_id = $1', user_id)
            return id

    async def get_last_id(self, user_id: int) -> int:
        id = await self.get_current_id(user_id)
        if id == 1:
            return 1

        return id - 1

    async def add_pokemon(self, user_id: int, name: str, level: int) -> None:
        async with self.acquire() as conn:

            id = await self.get_next_id(user_id)
            ivs, rounded = get_ivs()

            data = {
                'pokemon': {
                    'name': name,
                    'level': level,
                    'id': id,
                    'exp': 0,
                    'ivs': {
                        'rounded': rounded,
                        'hp': ivs[0],
                        'attack': ivs[1],
                        'defense': ivs[2],
                        'spatk': ivs[3],
                        'spdef': ivs[4],
                        'speed': ivs[5]
                    }
                }
            }
            
            pokemons = await conn.fetchval('SELECT pokemons FROM users WHERE user_id = $1', user_id)
            pokemons = json.loads(pokemons)

            pokemons.append(data)

            await conn.execute('UPDATE users SET pokemons = $1 WHERE user_id = $2', json.dumps(pokemons), user_id)

    async def edit_pokemon(self, user_id: int, id: int, level: int, ivs: typing.List[int]) -> None:
        rounded = _round(ivs)
        entry, entries = await self.get_pokemon_by_id(user_id, id)
        entries.remove(entry)

        entry['pokemon']['level'] = level
        entry['pokemon']['ivs'] = {
            'rounded': rounded,
            'hp': ivs[0],
            'attack': ivs[1],
            'defense': ivs[2],
            'spatk': ivs[3],
            'spdef': ivs[4],
            'speed': ivs[5]
        }

        entries.append(entry)

        async with self.acquire() as conn:
            await conn.execute('UPDATE users SET pokemons = $1 WHERE user_id = $2', json.dumps(entries), user_id)
            return None

    async def get_pokemons(self, user_id: int) -> List[Pokemon]:
        async with self.acquire() as conn:
            entries = await conn.fetchval('SELECT pokemons FROM users WHERE user_id = $1', user_id)
            pokemons = json.loads(entries)

            return pokemons

    async def get_pokemon_by_id(self, user_id: int, id: int) -> Tuple[Optional[Pokemon], List[Pokemon]]:
        pokemons = await self.get_pokemons(user_id)

        for pokemon in pokemons:
            other = pokemon['pokemon']['id']

            if other == id:
                return pokemon, pokemons

        return None, pokemons

    async def get_pokemon_by_name(self, user_id: int, name: str) -> Tuple[Optional[Pokemon], List[Pokemon]]:
        pokemons = await self.get_pokemons(user_id)

        for pokemon in pokemons:
            other = pokemon['pokemon']['name']

            if other == name:
                return pokemon, pokemons

        return None, pokemons

    async def update_pokemon(self, user_id: int, name: str, level: int) -> None:
        _, entry, entries = await self.get_selected(user_id)
        entries.remove(entry)

        entry['pokemon']['name'] = name
        entry['pokemon']['exp'] = 0
        entry['pokemon']['level'] = level

        entries.append(entry)

        async with self.acquire() as conn:
            await conn.execute('UPDATE users SET pokemons = $1 WHERE user_id = $2', json.dumps(entries), user_id)
            return None

    async def update_level(self, user_id: int, level: int):
        _, entry, entries = await self.get_selected(user_id)
        entries.remove(entry)

        entry['pokemon']['level'] = level
        entries.append(entry)

        async with self.acquire() as conn:
            await conn.execute('UPDATE users SET pokemons = $1 WHERE user_id = $2', json.dumps(entries), user_id)
            return None

    async def get_level(self, user_id: int) -> int:
        _, entry, entries = await self.get_selected(user_id)
        return entry['pokemon']['level']

    async def add_experience(self, user_id: int, exp: int):
        _, entry, entries = await self.get_selected(user_id)
        entries.remove(entry)

        entry['pokemon']['exp'] += exp
        entries.append(entry)

        async with self.acquire() as conn:
            await conn.execute('UPDATE users SET pokemons = $1 WHERE user_id = $2', json.dumps(entries), user_id)
            return None

    async def get_experience(self, user_id: int) -> int:
        _, entry, entries = await self.get_selected(user_id)
        return entry['pokemon']['exp']

    async def change_selected(self, user_id: int, id: int):
        async with self.acquire() as conn:
            await conn.execute('UPDATE users SET selected = $1 WHERE user_id = $2', id, user_id)

    async def get_selected(self, user_id: int) -> Tuple[int, Optional[Pokemon], List[Pokemon]]:
        async with self.acquire() as conn:
            id = await conn.fetchval('SELECT selected FROM users WHERE user_id = $1', user_id)

        pokemon, _ = await self.get_pokemon_by_id(user_id, id)
        return id, pokemon, _

    async def add_guild(self, guild_id: int, channel_id: int) -> None:
        async with self.acquire() as conn:
            guild = await conn.fetch('SELECT * from guilds WHERE guild_id = $1', guild_id)

            if not guild:
                await conn.execute('INSERT INTO guilds(guild_id, channel_id) VALUES($1, $2)', guild_id, channel_id)

            return None

    async def get_guild(self, guild_id: int) -> asyncpg.Record:
        async with self.acquire() as conn:
            guild = await conn.fetchrow('SELECT * FROM guilds WHERE guild_id = $1', guild_id)
            return guild

    async def get_spawn_channel(self, guild_id: int) -> int:
        async with self.acquire() as conn:
            id = await conn.fetchval('SELECT channel_id FROM guilds WHERE guild_id = $1', guild_id)
            return id

    async def update_spawn_channel(self, guild_id: int, channel_id: int) -> int:
        async with self.acquire() as conn:
            await conn.execute('UPDATE guilds SET channel_id = $1 WHERE guild_id = $2', channel_id, guild_id)
            return None


async def connect(dns: str, *, bot: 'Pokecord'):
    pool = await asyncpg.create_pool(dns)
    return Pool(pool, bot)