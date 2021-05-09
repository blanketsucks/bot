import asyncio
from typing import (
    Dict,
)
import aiohttp

from .endpoints import ENDPOINTS
from .stats import _names
from .sprites import Sprite
from .http import HTTPClient

async def get_pokemon(name: str, session=None):
    try:
        return Pokemon._pokemons[name]
    except KeyError:
        pass

    url = ENDPOINTS['pokemon'].format(pokemon=name)
    session = session or aiohttp.ClientSession()

    async with session.get(url) as resp:
        data = await resp.json()
    
    return Pokemon(data, session)

class Pokemon:
    _pokemons: Dict[str, 'Pokemon'] = {}
    _http: HTTPClient
    session: aiohttp.ClientSession

    def __new__(cls, data, session: aiohttp.ClientSession=None, loop: asyncio.AbstractEventLoop=None):
        self = super().__new__(cls)

        self.name = data['name']
        self.loop = loop or asyncio.get_event_loop()

        self._data = data
        self._http = HTTPClient(data, session)

        self.session = self._http._session
        self._waiter = asyncio.ensure_future(self.__queue())

        pokemon = cls._pokemons.setdefault(self.name, self)
        return pokemon

    def __repr__(self) -> str:
        return '<Pokemon name={0.name!r}>'.format(self)

    async def __queue(self):
        await asyncio.gather(
            *[
                self.get_abilities(),
                self.get_forms(),
                self.get_moves(),
                self.get_stats()
            ]
        )

    @property
    def base_experience(self) -> int:
        return self._data.get('base_experience', 0)

    @property
    def height(self):
        return self._data.get('height', 0)

    @property
    def is_default(self):
        return self._data.get('is_default', False)

    @property
    def dex(self):
        return self._data.get('order', 0)

    @property
    def id(self):
        return self._data.get('id', 0)

    @property
    def sprite(self):
        return Sprite(
            self._data['sprites']['other']['official-artwork'],
            self._data['sprites']['versions']['generation-vii']['ultra-sun-ultra-moon']
        )

    @property
    def health(self):
        return self._http._stats.hp

    @property
    def attack(self):
        return self._http._stats.attack

    @property
    def defense(self):
        return self._http._stats.defense

    @property
    def spatk(self):
        return self._http._stats.spattack

    @property
    def spdef(self):
        return self._http._stats.spdef

    @property
    def speed(self):
        return self._http._stats.speed

    async def wait_for_cache(self):
        await self._waiter

    def get_ability(self, name: str):
        return self._http._cache.get_ability(name)

    def get_move(self, name: str):
        return self._http._cache.get_move(name)

    def get_form(self, name: str):
        return self._http._cache.get_form(name)

    def get_stat(self, name: str):
        if name not in _names:
            valid = ', '.join(_names)
            raise ValueError(
                f'Invalid stat. Valid stats: {valid}'
            )

        return self._http._cache.get_stat(name)

    def get_type(self, name: str):
        return self._http._cache.get_type(name)

    async def abilities(self):
        return await self._http._gen_abilities()

    async def get_abilities(self):
        return await self._http.get_abilities()

    async def moves(self):
        return await self._http._gen_moves()

    async def get_moves(self):
        return await self._http.get_moves()

    async def forms(self):
        return await self._http._gen_forms()

    async def get_forms(self):
        return await self._http.get_forms()
    
    async def stats(self):
        return await self._http._gen_stats()

    async def get_stats(self):
        return await self._http.get_stats()

    async def types(self):
        return await self._http._gen_types()

    async def get_types(self):
        return await self._http.get_types()