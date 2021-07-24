import asyncio
from typing import (
    Generator,
    TYPE_CHECKING,
    TypeVar,
    Generic,
    List,
    Any
)

_T = TypeVar('_T')

if TYPE_CHECKING:
    from .database import Pool, Pokecord

class AsyncIterator(Generic[_T]):
    def __init__(self, future: asyncio.Future[List], pool: 'Pool', bot: 'Pokecord') -> None:
        self.future = future
        self.pool = pool
        self.bot = bot
        self.records = []
        self.index = 0

    def __await__(self) -> Generator[Any, None, List[_T]]:
        return self.future.__await__()

    def __aiter__(self):
        return self

    async def __anext__(self) -> _T:
        await self.future

        if self.future.done():
            self.records = self.future.result()

        try:
            record = self.records[self.index]
            return record
        except IndexError:
            raise StopAsyncIteration
        finally:
            self.index += 1