from typing import List, AsyncIterator, Optional
import aiohttp

from .stats import Stat, _stats, Stats
from .moves import Move
from .forms import Form
from .abilities import Ability
from .types import Type

class Cache:
    def __init__(self) -> None:
        self.stats = {}
        self.moves = {}
        self.abilities = {}
        self.forms = {}
        self.types = {}

    def add_stat(self, stat: Stat):
        self.stats[stat.name] = stat

    def get_stat(self, name: str) -> Optional[Stat]:
        return self.stats.get(name)

    def add_move(self, move: Move):
        self.moves[move.name] = move

    def get_move(self, name: str) -> Optional[Move]:
        return self.moves.get(name)

    def add_ability(self, ability: Ability):
        self.abilities[ability.name] = ability

    def get_ability(self, name: str) -> Optional[Ability]:
        return self.abilities.get(name)

    def add_form(self, form: Form):
        self.forms[form.name] = form

    def get_form(self, name: str) -> Optional[Form]:
        return self.forms.get(name)

    def add_type(self, type: Type):
        self.types[type.name] = type

    def get_type(self, name: str) -> Optional[Type]:
        return self.types.get(name)

class HTTPClient:
    def __init__(self, data, session: aiohttp.ClientSession=None) -> None:
        self._session = session or aiohttp.ClientSession()

        self.data = data
        self._cache = Cache()

    async def get_stats(self) -> List[Stat]:
        if getattr(self, '_stats', None):
            return self._stats

        entries = self.data.get('stats')

        stats = []
        for entry in entries:
            base = entry['base_stat']
            effort = entry['effort']

            url = entry['stat']['url']
            async with self._session.get(url) as resp:
                json = await resp.json()

                json['base'] = base
                json['effort'] = effort

                _id = json['id']

                cls = _stats.get(_id)
                stat = cls(json, self._session)

                self._cache.add_stat(stat)
            stats.append(stat)

        stats = Stats(
            hp=stats[0],
            attack=stats[1],
            defense=stats[2],
            spattack=stats[3],
            spdef=stats[4],
            speed=stats[5]
        )

        self._stats = stats
        return self._stats

    async def get_moves(self) -> List[Move]:
        if getattr(self, '_moves', None):
            return self._moves

        entries = self.data.get('moves', [])

        moves = []
        for entry in entries:
            url = entry['move']['url']
            learned_at = entry['version_group_details'][0]['level_learned_at']

            async with self._session.get(url) as resp:
                data = await resp.json()
                move = Move(data, self._session, learned_at)

                self._cache.add_move(move)
            moves.append(move)
        
        self._moves = moves
        return self._moves

    async def get_abilities(self) -> List[Ability]:
        if getattr(self, '_abilities', None):
            return self._abilities

        abilities = self.data.get('abilities', [])
        entries = []

        for data in abilities:
            ability = Ability(data['ability'], self._session) 
            self._cache.add_ability(ability)

            entries.append(ability)

        self._abilities = entries
        return entries

    async def get_forms(self) -> List[Form]:
        if getattr(self, '_forms', None):
            return self._forms

        entries = self.data.get('forms', [])
        forms = []

        for entry in entries:
            url = entry['url']
            async with self._session.get(url) as resp:
                data = await resp.json()
                form = Form(data, self._session)

                self._cache.add_form(form)
            forms.append(form)

        self._forms = forms
        return forms

    async def get_types(self) -> List[Type]:
        if getattr(self, '_types', None):
            return self._types

        entries = self.data.get('types', [])
        types = []

        for entry in entries:
            url = entry['type']['url']

            async with self._session.get(url) as resp:
                data = await resp.json()
                type = Type(data, self._session)

                self._cache.add_type(type)
            types.append(type)

        self._types = types
        return self._types

    async def _gen_moves(self) -> AsyncIterator[Move]:
        moves = await self.get_moves()
        for move in moves:
            yield move

    async def _gen_abilities(self) -> AsyncIterator[Ability]:
        abilities = await self.get_abilities()
        for ability in abilities:
            yield ability

    async def _gen_stats(self) -> AsyncIterator[Stat]:
        stats = await self.get_stats()
        for stat in stats:
            yield stat

    async def _gen_forms(self) -> AsyncIterator[Form]:
        forms = await self.get_forms()
        for form in forms:
            yield form

    async def _gen_types(self) -> AsyncIterator[Type]:
        types = await self.get_types()
        for type in types:
            yield type

    