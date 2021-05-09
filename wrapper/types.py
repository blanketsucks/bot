from typing import List
import aiohttp

from .endpoints import ENDPOINTS
from .moves import Move

async def get_type(name: str, session=None):
    url = ENDPOINTS['type'].format(type=name)
    session = session or aiohttp.ClientSession()

    async with session.get(url) as resp:
        data = await resp.json()

    return Type(data, session)

class DamageRelation:
    def __init__(self, __data, __session) -> None:
        self.__data = __data
        self.__session = __session

    async def _get_entries(self, key: str):
        if getattr(self, '_' + key, None):
            return getattr(self, '_' + key)

        entries = self.__data.get(key, [])
        types = []

        for entry in entries:
            url = entry['url']

            async with self.__session.get(url) as resp:
                data = await resp.json()
                _type = Type(data, self.__session)

            types.append(_type)

        setattr(self, '_' + key, types)
        return types

    async def double_damage_from(self):
        return await self._get_entries('double_damage_from')

    async def double_damage_to(self):
        return await self._get_entries('double_damage_to')

    async def half_damage_from(self):
        return await self._get_entries('half_damage_from')

    async def half_damage_to(self):
        return await self._get_entries('half_damage_to')

    async def no_damage_from(self):
        return await self._get_entries('no_damage_from')

    async def no_damage_to(self):
        return await self._get_entries('no_damage_to')

class Type:
    _types = {}

    def __new__(cls, __data, __session) -> 'Type':
        self = super().__new__(cls)

        self.__data = __data
        self.__session = __session

        self.id = __data.get('id', 0)
        self.name = __data.get('name', 0)

        return cls._types.setdefault(self.name, self)

    @property
    def damage_relations(self):
        return DamageRelation(self.__data.get('damage_relations', {}), self.__session)

    async def moves(self) -> List[Move]:
        if getattr(self, '_moves', None):
            return self._moves

        entries = self.__data.get('moves', [])
        moves = []

        for entry in entries:
            url = entry['url']
            async with self.__session.get(url) as resp:
                try:
                    data = await resp.json()
                except aiohttp.ContentTypeError:
                    break

                move = Move(data, self.__session)

            moves.append(move)

        self._moves = moves
        return moves
