import typing
import asyncpg

if typing.TYPE_CHECKING:
    from .database import Pool, Pokecord

class Model:
    def __init__(self, record: asyncpg.Record, pool: 'Pool', bot: 'Pokecord') -> None:
        self.record = record
        self.pool = pool
        self.bot = bot

    def __repr__(self) -> str:
        name = self.__class__.__name__
        return f'<{name} id={self.id}>'

    @property
    def id(self):
        name = self.__class__.__name__.lower()
        return self.record[name + '_id']

    async def fetch(self):
        raise NotImplementedError

    async def refetch(self):
        raise NotImplementedError
