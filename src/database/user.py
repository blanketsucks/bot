from __future__ import annotations

from typing import (
    Any,
    Optional,
    List,
    Dict,
    TYPE_CHECKING
)
from discord.ext import commands
import asyncpg

from src.utils import get_health_stat, get_other_stat, PokedexEntry, Context
from .model import RecordModel
from .pokemons import EVs, IVs, Moves, Pokemon

if TYPE_CHECKING:
    from src.bot import Nature
    from .pool import Pool

class UserPokemonStats:
    def __init__(self, pokemon: UserPokemon) -> None:
        self.pokemon = pokemon

    @property
    def health(self) -> int:
        return get_health_stat(
            base=self.pokemon.dex.stats.hp,
            iv=self.pokemon.ivs.hp,
            ev=self.pokemon.evs.hp,
            level=self.pokemon.level
        )

    @property
    def attack(self) -> int:
        return get_other_stat(
            base=self.pokemon.dex.stats.atk,
            iv=self.pokemon.ivs.atk,
            ev=self.pokemon.evs.atk,
            level=self.pokemon.level,
            nature=self.pokemon.nature.atk
        )

    @property
    def defense(self) -> int:
        return get_other_stat(
            base=self.pokemon.dex.stats.defense,
            iv=self.pokemon.ivs.defense,
            ev=self.pokemon.evs.defense,
            level=self.pokemon.level,
            nature=self.pokemon.nature.defense
        )


    @property
    def spatk(self) -> int:
        return get_other_stat(
            base=self.pokemon.dex.stats.spatk,
            iv=self.pokemon.ivs.spatk,
            ev=self.pokemon.evs.spatk,
            level=self.pokemon.level,
            nature=self.pokemon.nature.spatk
        )
    
    @property
    def spdef(self) -> int:
        return get_other_stat(
            base=self.pokemon.dex.stats.spdef,
            iv=self.pokemon.ivs.spdef,
            ev=self.pokemon.evs.spdef,
            level=self.pokemon.level,
            nature=self.pokemon.nature.spdef
        )

    @property
    def speed(self) -> int:
        return get_other_stat(
            base=self.pokemon.dex.stats.speed,
            iv=self.pokemon.ivs.speed,
            ev=self.pokemon.evs.speed,
            level=self.pokemon.level,
            nature=self.pokemon.nature.speed
        )

class UserPokemon(commands.Converter[Any]):
    def __init__(self, user: User, data: Dict[str, Any]) -> None:
        self.user = user
        self.data = data

    @classmethod
    async def convert(cls, ctx: Context, argument: str) -> UserPokemon:
        user = ctx.pool.user
        if argument.lower() in ('l', 'latest'):
            entry = user.pokemons.get(user.catch_id)
            if not entry:
                raise commands.BadArgument('You do not have a selected pokemon.')

            return entry
        if argument.isdigit():
            entry = user.pokemons.get(int(argument))
            if not entry:
                raise commands.BadArgument('You do not have a pokemon with that id.')

            return entry

        pokemons = user.find(nickname=argument)
        if not pokemons:
            raise commands.BadArgument('You do not have a pokemon with that name.')
        
        return pokemons[0]

    @property
    def dex(self) -> PokedexEntry:
        return self.pool.bot.pokedex.get_pokemon(self.entry.id) # type: ignore
    
    @property
    def entry(self) -> Pokemon:
        return Pokemon.from_dict(self.data)

    @property
    def id(self) -> int:
        return self.entry.id

    @property
    def nickname(self) -> str:
        return self.entry.nickname

    @property
    def level(self) -> int:
        return self.entry.level

    @property
    def exp(self) -> int:
        return self.entry.exp

    @property
    def ivs(self) -> IVs:
        return self.entry.ivs

    @property
    def evs(self) -> EVs:
        return self.entry.evs
    
    @property
    def moves(self) -> Moves:
        return self.entry.moves
    
    @property
    def shiny(self) -> bool:
        return self.entry.shiny

    @property
    def nature(self) -> Nature:
        return self.user.bot.get_nature(self.entry.nature) # type: ignore

    @property
    def stats(self):
        return UserPokemonStats(self)

    @property
    def catch_id(self) -> int:
        return self.entry.catch_id

    @property
    def pool(self):
        return self.user.pool

    def is_selected(self) -> bool:
        return self.entry.catch_id == self.user.selected

    def exists(self) -> bool:
        return self.entry.catch_id in self.user.pokemons

    async def save(self) -> None:
        entry = self.entry
        async with self.pool.acquire() as conn:
            query = 'UPDATE users SET pokemons = $1, catch_id = $2 WHERE id = $3'

            data = self.user.entries.copy()
            data[entry.catch_id] = entry.to_dict()
            
            await conn.execute(query, data, entry.catch_id, self.user.id)
        
        self.user.pokemons[self.entry.catch_id] = self
    
    async def edit(
        self,
        *,
        nickname: Optional[str] = None, 
        level: Optional[int] = None,
        exp: Optional[int] = None,
        nature: Optional[str] = None,
        moves: Optional[Moves] = None,
        id: Optional[int] = None,
    ) -> UserPokemon:
        if not self.exists():
            raise ValueError(f'Pokemon {self.entry.nickname!r} does not exist')

        if nickname is not None:
            self.data['nickname'] = nickname
        if level is not None:
            self.data['level'] = level
        if exp is not None:
            self.data['exp'] = exp
        if nature is not None:
            self.data['nature'] = nature
        if moves is not None:
            self.data['moves'] = moves.to_dict()
        if id is not None:
            self.data['id'] = id
        
        await self.save()
        return self

    async def add_exp(self, exp: int) -> UserPokemon:
        return await self.edit(exp=self.exp + exp)

    async def release(self) -> None:
        if not self.exists():
            raise ValueError(f'Pokemon {self.entry.catch_id!r} does not exist')

        if self.is_selected():
            new_selected = self.catch_id - 1
        else:
            new_selected = self.catch_id

        entries = self.user.entries.copy()
        entries.pop(str(self.catch_id))

        async with self.pool.acquire() as conn:
            query = 'UPDATE users SET pokemons = $1, selected = $2 WHERE id = $3'
            await conn.execute(query, entries, new_selected, self.user.id)

    async def select(self) -> None:
        if not self.exists():
            raise ValueError(f'Pokemon {self.entry.nickname!r} does not exist')

        if self.is_selected():
            raise ValueError(f'{self.entry.nickname!r} is already selected.')

        entry = self.entry
        async with self.pool.acquire() as conn:
            query = 'UPDATE users SET selected = $1 WHERE user_id = $2'
            await conn.execute(query, entry.catch_id, self.user.id)

class UserBalance:
    def __init__(self, user: User, credits: int) -> None:
        self.user = user
        self.credits = credits

    @property
    def pool(self):
        return self.user.pool

    async def increment(self, by: int) -> int:
        self.credits += by
        async with self.pool.acquire() as conn:
            query = 'UPDATE users SET credits = $1 WHERE user_id = $2'
            await conn.execute(query, self.credits, self.user.id)

        return self.credits

    async def decrement(self, by: int) -> int:
        self.credits -= by
        async with self.pool.acquire() as conn:
            query = 'UPDATE users SET credits = $1 WHERE user_id = $2'
            await conn.execute(query, self.credits, self.user.id)

        return self.credits

class User(RecordModel):
    def __init__(self, record: asyncpg.Record, pool: Pool) -> None:
        super().__init__(record, pool)
        self.pokemons = {int(catch_id): UserPokemon(self, pokemon) for catch_id, pokemon in self.entries.items()}

    @property
    def entries(self) -> Dict[Any, Dict[str, Any]]:
        return self.record['pokemons']

    @property
    def balance(self) -> UserBalance:
        return UserBalance(self, self.record['credits'])

    @property
    def catch_id(self) -> int:
        return self.record['catch_id']

    @property
    def selected(self) -> int:
        return self.record['selected']

    def find(self, **attrs: Any) -> List[UserPokemon]:
        pokemons = [
            pokemon for pokemon in self.pokemons.values() 
            if all(pokemon.data[key] == value for key, value in attrs.items())
        ]

        return pokemons

    def get_selected(self) -> UserPokemon:
        return self.pokemons.get(self.selected) # type: ignore
            
    async def add_pokemon(self, pokemon_id: int, level: int, exp: int, is_shiny: bool):
        id = self.catch_id + 1
        entry = self.pool.create_pokemon(pokemon_id, id, is_shiny)

        entry.level = level
        entry.exp = exp
        entry.catch_id = id

        pokemon = UserPokemon(self, entry.to_dict())
        await pokemon.save()

        return pokemon

    async def wipe(self) -> None:
        await self.pool.execute('DELETE FROM users WHERE id = $1', self.id)