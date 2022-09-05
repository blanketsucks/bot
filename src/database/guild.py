import discord
from typing import (
    Optional
)

from .model import RecordModel

class Guild(RecordModel):
    
    @property
    def spawn_channel_id(self) -> Optional[int]:
        return self.record['spawn_channel']

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
        return await self.pool.get_guild(self.id)

    async def fetch_spawn_channel(self) -> Optional[discord.TextChannel]:
        guild = await self.fetch()
        if not guild:
            return None

        if not self.spawn_channel_id:
            return None

        channel = guild.get_channel(self.spawn_channel_id)
        if not channel:
            try:
                channel = await guild.fetch_channel(self.spawn_channel_id)
            except (discord.Forbidden, discord.NotFound, discord.HTTPException):
                return None

        assert isinstance(channel, discord.TextChannel)
        return channel

    async def update_spawn_channel(self, channel_id: int):
        async with self.pool.acquire() as conn:
            await conn.execute('UPDATE guilds SET spawn_channel = $1 WHERE id = $2', channel_id, self.id)
            return channel_id

    async def update_prefix(self, prefix: str):
        async with self.pool.acquire() as conn:
            await conn.execute('UPDATE guilds SET prefix = $1 WHERE id = $2', prefix, self.id)
            return prefix
