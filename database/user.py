from typing import (
    Mapping,
    Any,
    Union,
    Optional,
    Tuple,
    List,
    Dict,
    TYPE_CHECKING
)
import json
import discord
import random

from utils.calc import _round, get_ivs
from .model import Model
from .market import Listings

if TYPE_CHECKING:
    from .database import Pokecord


class Nature:
    def __init__(self, data: Mapping[str, Any], name: str) -> None:
        self.name = name

        self.health: int = data['hp']
        self.attack: int = data['atk']
        self.defense: int = data['def']
        self.spattack: int = data['spatk']
        self.spdefense: int = data['spdef']
        self.speed: int = data['speed']

class Ivs:
    def __init__(self, data: Mapping[str, Any]) -> None:
        self.rounded: int = data['rounded']

        self.health: int = data['hp']
        self.attack: int = data['attack']
        self.defense: int = data['defense']
        self.spattack: int = data['spatk']
        self.spdefense: int = data['spdef']
        self.speed: int = data['speed']

class Moves:
    def __init__(self, data: Mapping[str, str]) -> None:
        self.first: str = data['1']
        self.second: Optional[str] = data['2']
        self.third: Optional[str] = data['3']
        self.fourth: Optional[str] = data['4']

        self._iter = iter(tuple(data))

    def __iter__(self):
        return self

    def __next__(self):
        return next(self._iter)

class Pokemon:
    def __init__(self, data: Mapping[str, Any], bot: 'Pokecord', user: 'User') -> None:
        self._data = data
        self.bot = bot
        self.user = user

        self._nature = data['nature']

        self.name: str = data['name']
        self.id: int = data['id']
        self.experience: int = data['exp']
        self.level: int = data['level']

    @property
    def nature(self):
        return Nature(self._nature, self._data['nature'])

    @property
    def ivs(self):
        return Ivs(self._data['ivs'])

    @property
    def moves(self):
        return Moves(self._data['moves'])

    @property
    def data(self):
        return {'pokemon': self._data}

class User(Model):
    @property
    def pokemons(self) -> List[Pokemon]:
        return [Pokemon(pokemon['pokemon'], self.bot, self) for pokemon in json.loads(self.record['pokemons'])]

    @property
    def entries(self) -> List[Dict]:
        return json.loads(self.record['pokemons'])

    @property
    def balance(self) -> int:
        return self.record['credits']

    @property
    def current_id(self) -> int:
        return self.record['current_id']

    @property
    def selected(self) -> int:
        return self.record['selected']

    async def fetch(self):
        user = self.bot.get_user(self.id)
        if not user:
            try:
                user = await self.bot.fetch_user(self.id)
            except (discord.NotFound, discord.HTTPException):
                user = None

        return user

    async def refetch(self):
        user = await self.pool.get_user(self.id)
        return user

    def get_pokemon_by_id(self, id: int) -> Tuple[Optional[Pokemon], List[Pokemon]]:
        copy = self.entries.copy()

        for pokemon in self.pokemons:
            other = pokemon.id

            if other == id:
                return pokemon, copy

        return None, copy

    def get_pokemon_by_name(self, name: str) -> Tuple[Optional[Pokemon], List[Pokemon]]:
        copy = self.entries.copy()

        for pokemon in self.pokemons:
            other = pokemon.name

            if other.lower() == name.lower():
                return pokemon, copy

        return None, copy

    def get_selected(self) -> Tuple[Optional[Pokemon], List[Pokemon]]:
        return self.get_pokemon_by_id(self.selected)

    def get_pokemon(self, id: Union[str, int]) -> Optional[Pokemon]:
        if isinstance(id, str):
            return self.get_pokemon_by_name(id)[0]

        return self.get_pokemon_by_id(id)[0]

    def get_pokemon_moves(self, id: Union[int, str]) -> Moves:
        if isinstance(id, str):
            entry, entries = self.get_pokemon_by_name(id)

        if isinstance(id, int):
            entry, entries = self.get_pokemon_by_id(id)

        return entry.moves

    def get_selected_moves(self) -> Moves:
        entry, _ = self.get_selected()
        return entry.moves

    async def update_pokemons(self, data: List[Dict]):
        entries = json.dumps(data)

        async with self.pool.acquire() as conn:
            await conn.execute('UPDATE users SET pokemons = $1 WHERE user_id = $2', entries, self.id)
            return data

    async def add_pokemon(self, name: str, level: int, exp: int):
        id = await self.get_next_pokemon_id()
        ivs, rounded = get_ivs()
        copy = self.entries.copy()

        data = {
            'pokemon': {
                'name': name,
                'level': level,
                'id': id,
                'exp': exp,
                'ivs': {
                    'rounded': rounded,
                    'hp': ivs[0],
                    'attack': ivs[1],
                    'defense': ivs[2],
                    'spatk': ivs[3],
                    'spdef': ivs[4],
                    'speed': ivs[5],
                },
                'moves': {
                    '1': 'tackle',
                    '2': None,
                    '3': None,
                    '4': None
                },
                'nature': random.choice(list(self.bot.natures.values()))
            }
        }

        copy.append(data)
        await self.update_pokemons(copy)

    async def edit_pokemon(self, name: str, id: int, level: int, ivs: List[int]) -> None:
        rounded = _round(ivs)

        entry, entries = self.get_pokemon_by_id(id)
        entries.remove(entry.data)

        entry._data['name'] = name
        entry._data['level'] = level
        entry._data['exp'] = 0
        entry._data['ivs'] = {
            'rounded': rounded,
            'hp': ivs[0],
            'attack': ivs[1],
            'defense': ivs[2],
            'spatk': ivs[3],
            'spdef': ivs[4],
            'speed': ivs[5]
        }

        entries.append(entry.data)
        await self.update_pokemons(entries)

    async def update_pokemon(self, name: str, level: int) -> None:
        entry, entries = self.get_selected()
        entries.remove(entry.data)

        entry._data['name'] = name
        entry._data['exp'] = 0
        entry._data['level'] = level

        entries.append(entry.data)
        await self.update_pokemons(entries)

    async def update_pokemon_move(self, id: str, move: str):
        entry, entries = self.get_selected()
        entries.remove(entry.data)

        entry._data['moves'][id] = move
        entries.append(entry)

        await self.update_pokemons(entries)

    async def update_pokemon_nature(self, nature: str):
        entry, entries = self.get_selected()

        entries.remove(entry.data)
        entry._data['nature'] = nature.capitalize()

        entries.append(entry.data)
        await self.update_pokemons(entries)

    async def remove_pokemon(self, id: Union[str, int]):
        if isinstance(id, str):
            entry, entries = self.get_pokemon_by_name(id)
            id = entry.id

        if isinstance(id, int):
            entry, entries = self.get_pokemon_by_id(id)

        entries.remove(entry.data)
        new = await self.get_last_pokemon_id()

        if self.selected == id:
            await self.change_selected(new)

        await self.update_pokemons(entries)
        await self.change_all_ids(id)

    async def update_level(self, level: int):
        entry, entries = self.get_selected()
        entries.remove(entry.data)

        entry._data['level'] = level
        entries.append(entry.data)

        await self.update_pokemons(entries)

    def get_level(self) -> int:
        entry, entries = self.get_selected()
        return entry.level

    async def add_experience(self, exp: int):
        entry, entries = self.get_selected()
        entries.remove(entry.data)

        entry._data['exp'] += exp
        entries.append(entry.data)

        await self.update_pokemons(entries)

    def get_experience(self) -> int:
        entry, entries = self.get_selected()
        return entry.experience

    def get_pokemon_experience(self, id: Union[str, int]):
        if isinstance(id, str):
            entry, _ = self.get_pokemon_by_name(id)
            return entry.experience

        entry, _ = self.get_pokemon_by_id(id)
        return entry.experience

    async def change_selected(self, id: int):
        async with self.pool.acquire() as conn:
            await conn.execute('UPDATE users SET selected = $1 WHERE user_id = $2', id, self.id)
            return id

    async def change_all_ids(self, thrown: int):
        user = await self.refetch()
        entries = user.pokemons.copy()

        for entry in entries:
            if int(entry['id']) > thrown:
                entry['id'] = entry['id'] - 1

        await user.update_pokemons(entries)

    async def get_next_pokemon_id(self) -> int:
        async with self.pool.acquire() as conn:
            new_id = self.current_id + 1

            await conn.execute('UPDATE users SET current_id = $1 WHERE user_id = $2', new_id, self.id)
            return new_id

    async def get_last_pokemon_id(self) -> int:
        user = await self.refetch()

        async with self.pool.acquire() as conn:
            new = user.current_id - 1

            await conn.execute('UPDATE users SET current_id = $1 WHERE user_id = $2', new, self.id)
            return new

    async def add_to_balance(self, amount: int):
        new = self.balance + amount

        async with self.pool.acquire() as conn:
            await conn.execute('UPDATE users SET credits = $1 WHERE user_id = $2', new, self.id)
            return new

    async def remove_from_balance(self, amount: int):
        new = self.balance - amount

        async with self.pool.acquire() as conn:
            await conn.execute('UPDATE users SET credits = $1 WHERE user_id = $2', new, self.id)
            return new

    async def get_market_listings(self):
        async with self.pool.acquire() as conn:
            listings = await conn.fetchrow('SELECT * FROM market WHERE user_id = $1', self.id)
            return Listings(listings, self.pool, self.bot, self)