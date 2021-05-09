from typing import (
    Mapping,
    Any
)

import aiohttp

class EffectEntry:
    def __init__(self, __data: Mapping[str, Any]) -> None:
        self.__data = __data

        self.effect = self.__data.get('effect', '')

    def __repr__(self) -> str:
        return '<EffectEntry short_effect={0.short_effect!r}>'.format(self)

    @property
    def short_effect(self):
        return self.__data.get('short_effect', '')

class Ability:
    def __init__(self, __data: Mapping[str, Any], __session: aiohttp.ClientSession) -> None:
        self.__data = __data
        self.__session = __session

        self.url = self.__data.get('url', '')
        self.name = self.__data.get('name', '')

    def __repr__(self) -> str:
        return '<Ability name={0.name!r} is_hidden={0.is_hidden}>'.format(self)

    @property
    def is_hidden(self):
        return self.__data.get('is_hidden', False)

    @property
    def slot(self):
        return self.__data.get('slot', 0)

    async def effect(self):
        if getattr(self, '_effect', None):
            return self._effect

        async with self.__session.get(self.url) as response:
            json = await response.json()
            entries = json['effect_entries']

            entry = entries[1]
            effect = EffectEntry(entry)

            self._effect = effect
            return effect