from __future__ import annotations

from typing import TYPE_CHECKING, NamedTuple
from discord.ext import commands

if TYPE_CHECKING:
    from src.bot import Pokecord
    from src.database import User, Guild

__all__ = 'Context', 'ContextPool'

class ContextPool(NamedTuple):
    user: User
    guild: Guild

class Context(commands.Context['Pokecord']):
    pool: ContextPool