import random
import asyncpg
import asyncio
import json
from typing import (
    Optional, 
    List,  
    TYPE_CHECKING,
)

from utils.calc import get_ivs
from .user import User
from .guild import Guild
from .utils import AsyncIterator

if TYPE_CHECKING:
    from bot import Pokecord

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

            market = await conn.fetchrow('SELECT * from market WHERE user_id = $1', user_id)
            if not market:
                await conn.execute(
                    'INSERT INTO market(user_id, entries) VALUES ($1, $2)',
                    user_id, json.dumps([])
                )

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