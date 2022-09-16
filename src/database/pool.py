from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, TYPE_CHECKING, Sequence, Tuple

import asyncpg
import json
import datetime
import functools

from .user import User, UserPokemon
from .guild import Guild
from .pokemons import Pokemon
from .items import ShopItem, ShopItemKind
from .market import Market
from src.utils import chance, TTLDict

if TYPE_CHECKING:
    from src.bot import Pokecord

class Pool:
    free: TTLDict[int, Tuple[List[UserPokemon], List[UserPokemon]]]

    def __init__(self, pool: asyncpg.Pool[asyncpg.Record], bot: Pokecord) -> None:
        self.wrapped = pool
        self.bot = bot

        self.users: Dict[int, User] = {}
        self.guilds: Dict[int, Guild] = {}

        self.market: Optional[Market] = None

        # { dex_id: ( [non-shiny pokemons...], [shiny pokemons...] ) }
        self.free = TTLDict(expiry=datetime.timedelta(minutes=60))

    async def __aenter__(self) -> Pool:
        return self

    async def __aexit__(self, *args: Any):
        await self.close()

    def acquire(self):
        return self.wrapped.acquire()

    async def close(self):
        return await self.wrapped.close()

    async def execute(self, query: str, *args: Any):
        async with self.acquire() as conn:
            return await conn.execute(query, *args)

    async def executemany(self, query: str, args: Iterable[Sequence[Any]], **kwargs: Any):
        async with self.acquire() as conn:
            return await conn.executemany(query, args, **kwargs)

    async def fetch(self, query: str, *args) -> List[asyncpg.Record]:
        async with self.acquire() as conn:
            return await conn.fetch(query, *args)

    async def fetchrow(self, query: str, *args) -> Optional[asyncpg.Record]:
        async with self.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def fetchval(self, query: str, *args) -> Any:
        async with self.acquire() as conn:
            return await conn.fetchval(query, *args)

    async def fill_cache(self) -> None:
        await self.fill_user_cache()
        await self.fill_guild_cache()

        await self.get_market()

    def add_free_pokemon(self, pokemon: UserPokemon) -> None:
        free = self.free.setdefault(pokemon.dex.id, ([], []))
        free[pokemon.is_shiny()].append(pokemon)

    def get_free_pokemon(self, dex_id: int, *, is_shiny: bool = False) -> Optional[UserPokemon]:
        if dex_id not in self.free:
            return None

        free = self.free[dex_id][is_shiny]
        if not free:
            return None

        return free.pop()

    def create_pokemon(self, pokemon_id: int, owner_id: int, catch_id: int, is_shiny: bool) -> Pokemon:
        pokemon = self.bot.pokedex.get_pokemon(pokemon_id)
        if not pokemon:
            raise ValueError(f'Dex entry with id {pokemon_id!r} does not exist')

        nature = self.bot.generate_nature()
        return Pokemon.new(pokemon, nature, owner_id, catch_id, is_shiny)

    async def add_user(self, user_id: int, pokemon_id: int) -> User:
        async with self.acquire() as conn:
            record = await conn.fetchrow('SELECT * from users WHERE id = $1', user_id)
            if not record:
                entry = self.create_pokemon(pokemon_id, user_id, 1, chance(8192))

                entry.is_starter = True
                await entry.create(self)

                await conn.execute('INSERT INTO users(id, pokemons) VALUES($1, $2)', user_id, [str(entry.id)])
                record = await conn.fetchrow('SELECT * from users WHERE id = $1', user_id)

            assert record

            pokemons = await conn.fetch('SELECT * from pokemons WHERE owner_id = $1', user_id)
            return User(record, pokemons, self)

    async def get_user(self, user_id: int) -> Optional[User]:
        if user_id in self.users:
            return self.users[user_id]

        async with self.acquire() as conn:
            record = await conn.fetchrow('SELECT * FROM users WHERE id = $1', user_id)
            if not record:
                return None

            pokemons = await conn.fetch('SELECT * from pokemons WHERE owner_id = $1', user_id)
            user = User(record, pokemons, self)

            self.users[user_id] = user
            await user.reindex()

            return user

    async def fill_user_cache(self) -> None:
        records = await self.fetch('SELECT * FROM users')
        for record in records:
            if record['id'] in self.users:
                continue

            pokemons = await self.fetch('SELECT * from pokemons WHERE owner_id = $1', record['id'])
            user = User(record, pokemons, self)

            self.users[record['id']] = user
            await user.reindex()

    async def add_guild(self, guild_id: int) -> Guild:
        async with self.acquire() as conn:
            record = await conn.fetchrow('SELECT * from guilds WHERE id = $1', guild_id)
            if not record:
                await conn.execute('INSERT INTO guilds(id) VALUES($1)', guild_id)

            record = await conn.fetchrow('SELECT * from guilds WHERE id = $1', guild_id)
            assert record

            guild = Guild(record, self)
            self.guilds[guild_id] = guild

            return guild

    async def get_guild(self, guild_id: int) -> Optional[Guild]:
        if guild_id in self.guilds:
            return self.guilds[guild_id]

        record = await self.fetchrow('SELECT * FROM guilds WHERE id = $1', guild_id)
        if not record:
            return None

        guild = Guild(record, self)
        self.guilds[guild_id] = guild

        return guild

    async def fill_guild_cache(self):
        records = await self.fetch('SELECT * FROM guilds')
        for record in records:
            if record['id'] in self.guilds:
                continue

            guild = Guild(record, self)
            self.guilds[record['id']] = guild
    
    async def get_market(self) -> Market:
        if self.market is None:
            self.market = await Market.fetch(self)

        return self.market

    async def add_item(self, name: str, description: str, price: int, kind: ShopItemKind):
        await self.execute(
            'INSERT INTO items(name, description, price, kind) VALUES($1, $2, $3, $4)',
            name, description, price, kind
        )

    async def delete_item(self, id: int) -> None:
        await self.execute('DELETE FROM items WHERE id = $1', id)

    async def get_item(self, id: int) -> Optional[ShopItem]:
        record = await self.fetchrow('SELECT * FROM items WHERE id = $1', id)
        if not record:
            return None

        return ShopItem.from_record(self, record)

    async def get_all_items(self, *, kind: Optional[ShopItemKind] = None) -> List[ShopItem]:
        if kind is not None:
            records = await self.fetch('SELECT * FROM items WHERE kind = $1', kind)
        else:
            records = await self.fetch('SELECT * FROM items')
            
        return [ShopItem.from_record(self, record) for record in records]

    @functools.lru_cache(maxsize=128)
    async def fetch_guilds(self) -> List[Guild]:
        records = await self.fetch('SELECT * FROM guilds')
        return [Guild(record, self) for record in records]

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