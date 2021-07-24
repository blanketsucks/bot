import discord
from typing import (
    Optional
)

from .model import Model

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
