from __future__ import annotations

from typing import TYPE_CHECKING, Any, List, Optional, Dict, Any

import asyncpg
import discord

if TYPE_CHECKING:
    from .pool import Pool

class Guild:
    def __init__(self, record: asyncpg.Record, pool: Pool) -> None:
        self.data: Dict[str, Any] = dict(record)
        self.pool = pool

    @property
    def id(self) -> int:
        return self.data['id']
    
    @property
    def spawn_channel_ids(self) -> List[int]:
        return self.data['spawn_channels'] or []

    @property
    def exp_channel_ids(self) -> List[int]:
        return self.data['exp_channels'] or []

    @property
    def prefix(self) -> str:
        return self.data['prefix']

    async def set_spawn_channels(self, channel_ids: List[int]):
        await self.pool.execute('UPDATE guilds SET spawn_channels = $1 WHERE id = $2', channel_ids, self.id)
        self.data['spawn_channels'] = channel_ids

    async def set_prefix(self, prefix: str):
        await self.pool.execute('UPDATE guilds SET prefix = $1 WHERE id = $2', prefix, self.id)
        self.data['prefix'] = prefix

    async def set_exp_channels(self, channel_ids: List[int]):
        await self.pool.execute('UPDATE guilds SET exp_channels = $1 WHERE id = $2', channel_ids, self.id)
        self.data['exp_channels'] = channel_ids
