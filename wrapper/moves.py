from .abilities import EffectEntry
from .endpoints import ENDPOINTS

from collections import namedtuple
from typing import List
import aiohttp

async def get_move(name: str, session=None):
    url = ENDPOINTS['move'].format(move=name)
    session = session or aiohttp.ClientSession()

    async with session.get(url) as resp:
        data = await resp.json()

    return Move(data, session)

_AffectingMove = namedtuple('_AffectingMove', 'change move')

class AffectingMoves:
    def __init__(self, __data, __session) -> None:
        self.__data = __data
        self.__session = __session

    async def increase(self):
        if getattr(self, '_increase', None):
            return self._increase

        entries = self.__data.get('increase', [])
        moves = []

        for entry in entries:
            change = entry['change']
            url = entry['move']['url']

            async with self.__session.get(url) as resp:
                move = Move(await resp.json())
                print(url)
                print(move)

            moves.append(_AffectingMove(change, move))

        self._increase = moves
        return self._increase

    async def decrease(self):
        if getattr(self, '_decrease', None):
            return self._increase

        entries = self.__data.get('decrease', [])
        moves = []

        for entry in entries:
            change = entry['change']
            url = entry['move']['url']

            async with self.__session.get(url) as resp:
                move = Move(await resp.json())

            moves.append(_AffectingMove(change, move))

        self._decrease = moves
        return self._decrease

class Move:
    _moves = {}

    def __new__(cls, __data, __session, __learned_at) -> 'Move':
        self = super().__new__(cls)

        self.__session = __session
        self.__data = __data

        self.__data['learned_at'] = __learned_at

        self.name = self.__data.get('name', '')

        self.accuracy = self.__data.get('accuracy', 100)
        self.effects = [EffectEntry(effect) for effect in self.__data.get('effect_entries', [])]

        self.power = self.__data.get('power', 0)
        self.pp = self.__data.get('pp', 0)

        move = cls._moves.setdefault(self.name, self)
        return move

    def __repr__(self) -> str:
        return '<Move name={0.name!r} accuracy={0.accuracy} power={0.power}>'.format(self)

    def __gt__(self, other):
        return self.learned_at > other.learned_at

    @property
    def priority(self):
        return self.__data.get('priority', 0)

    @property
    def learned_at(self):
        return self.__data.get('learned_at', 0)

    def learned_by(self):
        from .pokemons import Pokemon

        poks: List[Pokemon] = []
        pokemons = self.__data.get('learned_by_pokemon')

        for pokemon in pokemons:
            poks.append(Pokemon(pokemon['name'], self.__session))

        return poks