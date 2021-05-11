from typing import List, Union
import discord

from bot import Pokecord
from .context import Context

class Paginator:
    def __init__(self, 
                ctx: Context, 
                *, 
                embeds: List[discord.Embed], 
                timeout: int=180.0) -> None:

        self.ctx = ctx
        self.bot: Pokecord = self.ctx.bot
        self.timeout = timeout
        self.embeds = embeds
        self.index = 0
        self.message = None
        self.reactions = {
            '➡️': self.next,
            '⏩': self.last,
            '⏹️': self.stop,
            '⏪': self.first,
            '⬅️': self.back
        }

        self.actual_reactions = list(self.reactions.keys())
        self.pages = len(embeds)

    async def start(self, content: Union[str, discord.Embed]):
        if isinstance(content, discord.Embed):
            message = await self.ctx.send(embed=content)
        else:
            message = await self.ctx.send(content)

        self.message = message

        await self.add_reactions()
        await self._loop()

    async def add_reactions(self):
        for reaction in self.actual_reactions:
            await self.message.add_reaction(reaction)

    async def action(self, emoji: str):
        coroutine = self.reactions.get(emoji)
        await coroutine()
    
    def check(self, payload: discord.RawReactionActionEvent):
        if payload.member != self.message.author:
            return False

        if str(payload.emoji) not in self.actual_reactions:
            return False

        if payload.member.bot:
            return False

        return True

    async def _loop(self):
        ...

    async def stop(self):
        await self.message.clear_reactions()
        await self.message.delete()

    async def next(self):
        if self.index == self.pages:
            self.index = 0
            return await self.message.edit(embed=self.embeds[self.index])

        self.index += 1
        return await self.message.edit(embed=self.embeds[self.index])

    async def back(self):
        if self.index == 0:
            self.index = self.pages - 1
            return await self.message.edit(embed=self.embeds[self.index])

        self.index -= 1
        return await self.message.edit(embed=self.embeds[self.index])

    async def first(self):
        self.index = 0
        return await self.message.edit(embed=self.embeds[self.index])

    async def last(self):
        self.index = self.pages - 1
        return await self.message.edit(embed=self.embeds[self.index])