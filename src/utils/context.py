from __future__ import annotations

from typing import TYPE_CHECKING, Dict, NamedTuple, Any, Optional

import copy
import discord
from discord.ext import commands

if TYPE_CHECKING:
    from src.bot import Pokecord
    from src.database import User, Guild

__all__ = 'Context', 'ContextPool'

VALID_EDIT_KWARGS: Dict[str, Any] = {
    'content': None,
    'embeds': [],
    'attachments': [],
    'suppress': False,
    'delete_after': None,
    'allowed_mentions': None,
    'view': None,
}

class ContextPool(NamedTuple):
    user: User
    guild: Guild

class Context(commands.Context['Pokecord']):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.count = 0

    pool: ContextPool

    async def send(self, content: Optional[str] = None, **kwargs: Any) -> discord.Message:
        if self.has_previous_message():
            previous = self.get_previous_message()
            assert previous

            kw = copy.deepcopy(VALID_EDIT_KWARGS)
            kw['content'] = content

            kw.update({k: v for k, v in kwargs.items() if k in VALID_EDIT_KWARGS})
            if 'embed' in kwargs:
                kw.setdefault('embeds', []).append(kwargs['embed'])

            file = kwargs.get('file')
            if file is not None:
                kw['attachments'] = [file]
            else:
                kw['attachments'] = []

            try:
                message = await previous.edit(**kw)
                self.bot.add_message(self.key, message)

                self.count += 1
            except discord.HTTPException:
                message = await super().send(content, **kwargs)
                self.bot.add_message(self.key, message)

            return message

        message = await super().send(content, **kwargs)
        self.bot.add_message(self.key, message)

        self.count += 1
        return message

    def has_previous_message(self) -> bool:
        return self.key in self.bot.messages

    def get_previous_message(self) -> Optional[discord.Message]:
        return self.bot.messages.get(self.key)

    @property
    def key(self) -> str:
        return f'{self.channel.id}-{self.message.id}-{self.count}'