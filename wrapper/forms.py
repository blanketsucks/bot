import aiohttp
from typing import Any, List, Mapping

from .sprites import Sprite
from .types import Type

class Form:
    def __init__(self, __data: Mapping[str, Any], __session: aiohttp.ClientSession) -> None:
        self.__data = __data
        self.__session = __session

        self.form_name = self.__data.get('form_name', '')
        self.form_names = self.__data.get('form_names', [])
        self.id = self.__data.get('id', 0)
        self.form_order = self.__data.get('order', 0)

        self.sprite = Sprite(
            self.__data['sprites'],
            self.__data['sprites']
        )

    def __repr__(self) -> str:
        return '<Form id={0.id} name={0.name!r}>'.format(self)

    async def types(self) -> List[Type]:
        if getattr(self, '_types', None):
            return self._types
    
        entries = self.__data.get('types', [])
        types = []

        for entry in entries:
            url = entry['type']['url']
            async with self.__session.get(url) as resp:
                data = await resp.json()
                _type = Type(data, self.__session)
            
            types.append(_type)

        self._types = types
        return types

    @property
    def name(self):
        return self.__data.get('name', '')

    @property
    def order(self):
        return self.__data.get('order', 0)

    @property
    def is_default(self):
        return self.__data.get('is_default')

    @property
    def is_mega(self):
        return self.__data.get('is_mega')

    @property
    def is_battle_only(self):
        return self.__data.get('is_battle_only')
