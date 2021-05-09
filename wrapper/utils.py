import asyncio
from typing import (
    Coroutine,
    Generator,
    Mapping,
    Any,
    AsyncGenerator
)
import typing

_T = typing.TypeVar('_T')

class AsyncIterator:
    def __init__(self, generator: typing.AsyncIterator[_T], coro: Coroutine[Any, Any, _T]) -> None:
        self.coro = coro
        self.gen = generator

    def __await__(self):
        return self.coro.__await__()

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return await self.gen.__anext__()
        except:
            raise StopAsyncIteration

class _waiter:
    URL = None

    async def wait_for_data(self):
        if self._waiter.done():
            return self._waiter.result()

        await asyncio.wait_for(
            fut=self._waiter,
            timeout=None
        )

        return self._waiter.result()

    async def _check(self):
        return await self.wait_for_data()

    async def _get(self) -> Mapping[str, Any]:
        async with self._session.get(self.URL) as resp:
            self._data = await resp.json()
            self._waiter.set_result(self._data)

            return None