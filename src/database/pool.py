from __future__ import annotations

from typing import Any, List, Optional, TYPE_CHECKING
import asyncpg
import json
import functools

from .user import User
from .guild import Guild
from .pokemons import EVs, Pokemon, IVs, Moves

if TYPE_CHECKING:
    from src.bot import Pokecord

class Pool:
    def __init__(self, pool: asyncpg.Pool[asyncpg.Record], bot: Pokecord) -> None:
        self.wrapped = pool
        self.bot = bot

    async def __aenter__(self) -> Pool:
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return await self.close()

    def acquire(self):
        return self.wrapped.acquire()

    async def close(self):
        return await self.wrapped.close()

    async def execute(self, query: str, *args: Any):
        async with self.acquire() as conn:
            return await conn.execute(query, *args)

    async def fetch(self, query: str, *args) -> List[asyncpg.Record]:
        async with self.acquire() as conn:
            return await conn.fetch(query, *args)

    async def fetchrow(self, query: str, *args) -> Optional[asyncpg.Record]:
        async with self.acquire() as conn:
            return await conn.fetchrow(query, *args)

    def create_pokemon(self, pokemon_id: int, catch_id: int) -> Pokemon:
        pokemon = self.bot.pokedex.get_pokemon(pokemon_id)
        if not pokemon:
            raise ValueError(f'Pokemon {pokemon_id!r} does not exist')

        ivs = IVs.generate()
        evs = EVs.generate()
        moves = Moves.default()

        nature = self.bot.generate_nature()
        name = pokemon.default_name

        return Pokemon(pokemon_id, name, 1, 0, ivs, evs, moves, nature, catch_id)

    async def add_user(self, user_id: int, pokemon_id: int) -> User:
        async with self.acquire() as conn:
            record = await conn.fetchrow('SELECT * from users WHERE id = $1', user_id)
            if not record:
                entry = self.create_pokemon(pokemon_id, 1)

                query = 'INSERT INTO users(id, pokemons) VALUES($1, $2)'
                data = {entry.catch_id: entry.to_dict()}

                await conn.execute(query, user_id, data)

                record = await conn.fetchrow('SELECT * from users WHERE id = $1', user_id)

            assert record
            return User(record, self)

    async def get_user(self, user_id: int) -> Optional[User]:
        async with self.acquire() as conn:
            user = await conn.fetchrow('SELECT * FROM users WHERE id = $1', user_id)
            if not user:
                return None

            return User(user, self)

    async def add_guild(
        self, 
        guild_id: int, 
        *,
        spawn_channel_id: Optional[int] = None, 
        prefix: Optional[str] = None
    ) -> Guild:
        async with self.acquire() as conn:
            record = await conn.fetchrow('SELECT * from guilds WHERE id = $1', guild_id)
            if not record:
                params: List[Any] = [guild_id]
                query = 'INSERT INTO guilds(id)'

                if spawn_channel_id is not None:
                    params.append(spawn_channel_id)
                if prefix is not None:
                    params.append(prefix)

                query = 'INSERT INTO guilds(id) VALUES($1)'
                await conn.execute(query, *params)

            record = await conn.fetchrow('SELECT * from guilds WHERE id = $1', guild_id)

            assert record
            return Guild(record, self)

    async def get_guild(self, guild_id: int) -> Optional[Guild]:
        record = await self.fetchrow('SELECT * FROM guilds WHERE id = $1', guild_id)
        if not record:
            return None

        return Guild(record, self)

    @functools.lru_cache(maxsize=128)
    async def fetch_guilds(self) -> List[Guild]:
        records = await self.fetch('SELECT * FROM guilds')
        return [Guild(record, self) for record in records]

    @functools.lru_cache(maxsize=128)
    async def fetch_users(self) -> List[User]:
        records = await self.fetch('SELECT * FROM users')
        return [User(record, self) for record in records]

async def connect(dns: str, bot: Pokecord):
    async def init(conn: asyncpg.Connection):
        await conn.set_type_codec(
            'json',
            encoder=json.dumps,
            decoder=json.loads,
            schema='pg_catalog'
        )

    pool = await asyncpg.create_pool(dns, init=init)
    if not pool:
        raise RuntimeError('Could not connect to database')

    return Pool(pool, bot)