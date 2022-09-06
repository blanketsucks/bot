from __future__ import annotations

from typing import Optional

from discord.ext import commands
import discord

from src.utils import Context
from src.bot import Pokecord

class GuildConfig(commands.Cog):
    def __init__(self, bot: Pokecord) -> None:
        self.bot = bot

    @commands.group(invoke_without_command=True)
    async def config(self, ctx: Context) -> None: ...

    @config.command(aliases=['p'])
    async def prefix(self, ctx: Context, *, prefix: Optional[str] = None):
        if prefix is None:
            return await ctx.send(f'My current prefix is: `{ctx.pool.guild.prefix}`')

        if 1 < len(prefix) < 15:
            return await ctx.send('The prefix must be between 1 and 15 characters long.')

        assert isinstance(ctx.author, discord.Member)
        if not ctx.author.guild_permissions.manage_channels: # TODO: manage_messages maybe?
            return await ctx.send('You do not have enough permissions')

        await ctx.pool.guild.set_prefix(prefix)
        await ctx.send(f'Successfully changed the prefix to `{prefix}`')

    @config.command(aliases=['s'])
    async def spawns(self, ctx: Context, *channels: discord.TextChannel):
        assert ctx.guild
        if not channels:
            if not ctx.pool.guild.spawn_channel_ids:
                return await ctx.send('A spawn channel has not been set yet.')

            chnls = [ctx.guild.get_channel(channel_id) for channel_id in ctx.pool.guild.spawn_channel_ids]
            mentions = ', '.join([channel.mention for channel in chnls]) # type: ignore

            return await ctx.send(f'Current spawn channels: {mentions}')

        assert isinstance(ctx.author, discord.Member)
        if not ctx.author.guild_permissions.manage_channels:
            return await ctx.send('You do not have enough permissions')

        channel_ids = [channel.id for channel in channels]
        mentions = ', '.join([channel.mention for channel in channels])

        await ctx.pool.guild.set_spawn_channels(channel_ids)
        await ctx.send(f'Successfully set the spawn channels to: {mentions}')

async def setup(bot: Pokecord):
    await bot.add_cog(GuildConfig(bot))