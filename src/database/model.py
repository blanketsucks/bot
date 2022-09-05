from __future__ import annotations

from typing import TYPE_CHECKING, Generic, TypeVar
from abc import ABC
import asyncpg

if TYPE_CHECKING:
    from .pool import Pool
    from src.bot import Pokecord

T = TypeVar('T')

class RecordModel(ABC, Generic[T]):
    def __init__(self, record: asyncpg.Record, pool: Pool) -> None:
        self.record = record
        self.pool = pool
        self.bot = pool.bot

    def __repr__(self) -> str:
        name = self.__class__.__name__
        return f'<{name} id={self.id}>'

    @property
    def id(self) -> int:
        return self.record['id']
