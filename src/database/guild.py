from typing import List, Optional
import discord

from .model import RecordModel

class Guild(RecordModel):
    
    @property
    def spawn_channel_ids(self) -> List[int]:
        return self.record['spawn_channels'] or []

    @property
    def exp_channel_ids(self) -> List[int]:
        return self.record['exp_channels'] or []

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

    async def set_spawn_channels(self, channel_ids: List[int]):
        await self.pool.execute('UPDATE guilds SET spawn_channels = $1 WHERE id = $2', channel_ids, self.id)

    async def set_prefix(self, prefix: str):
        await self.pool.execute('UPDATE guilds SET prefix = $1 WHERE id = $2', prefix, self.id)

    async def set_exp_channels(self, channel_ids: List[int]):
        await self.pool.execute('UPDATE guilds SET exp_channels = $1 WHERE id = $2', channel_ids, self.id)
