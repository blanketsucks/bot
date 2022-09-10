from __future__ import annotations

from typing import (
    Any,
    Optional,
    List,
    Dict,
    TYPE_CHECKING,
    Tuple
)
import uuid
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

    def __repr__(self) -> str:
        return f'<UserPokemon id={str(self.id)!r} catch_id={self.catch_id} nickname={self.nickname!r}>'

    @classmethod
    async def convert(cls, ctx: Context, argument: str) -> Any:
        user = ctx.pool.user
        if argument.lower() in ('l', 'latest'):
            entry = user.pokemons.get(user.catch_id)
            if not entry:
                await ctx.send('Pokémon not found.')
                return False

            return entry
        if argument.isdigit():
            entry = user.pokemons.get(int(argument))
            if not entry:
                await ctx.send('Pokémon not found.')
                return False

            return entry

        pokemons = user.find(nickname=argument)
        if not pokemons:
            await ctx.send('Pokémon not found.')
            return False
        
        return pokemons[0]

    @property
    def dex(self) -> PokedexEntry:
        return self.pool.bot.pokedex.get_pokemon(self.entry.dex_id) # type: ignore
    
    @property
    def entry(self) -> Pokemon:
        return Pokemon.from_dict(self.data)

    @property
    def id(self) -> uuid.UUID:
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

    def has_nickname(self) -> bool:
        return self.nickname != self.dex.default_name

    def is_selected(self) -> bool:
        return self.entry.catch_id == self.user.selected

    def is_starter(self) -> bool:
        return self.entry.is_starter

    def exists(self) -> bool:
        return self.entry.catch_id in self.user.pokemons

    async def save(self) -> None:
        query = 'UPDATE users SET pokemons = ARRAY_APPEND(users.pokemons, CAST($1 as UUID)), catch_id = $2 WHERE id = $3'
        await self.pool.execute(query, str(self.entry.id), self.entry.catch_id, self.user.id)
    
        self.user.pokemons[self.entry.catch_id] = self
    
    async def edit(
        self,
        *,
        nickname: Optional[str] = None, 
        level: Optional[int] = None,
        exp: Optional[int] = None,
        nature: Optional[str] = None,
        moves: Optional[Moves] = None,
        ivs: Optional[IVs] = None,
        evs: Optional[EVs] = None,
        shiny: Optional[bool] = None,
        dex_id: Optional[int] = None,
        catch_id: Optional[int] = None,
        owner_id: Optional[int] = None
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
            self.data['moves'] = moves
        if ivs is not None:
            self.data['ivs'] = ivs
        if evs is not None:
            self.data['evs'] = evs
        if shiny is not None:
            self.data['shiny'] = shiny
        if catch_id is not None:
            self.data['catch_id'] = catch_id
        if owner_id is not None:
            self.data['owner_id'] = owner_id
        if dex_id is not None:
            if not self.has_nickname() and nickname is None:
                dex = self.user.bot.pokedex.get_pokemon(dex_id)
                if dex is None:
                    return self # TODO: Raise error or something

                self.data['nickname'] = dex.default_name

            self.data['dex_id'] = dex_id
        
        await self.entry.update(self.pool)

        return self

    async def add_exp(self, exp: int) -> UserPokemon:
        return await self.edit(exp=self.exp + exp)

    async def release(self) -> None:
        if not self.exists():
            raise ValueError(f'Pokemon {self.entry.catch_id!r} does not exist')

        if self.is_selected():
            if self.catch_id == 1:
                new_selected = self.catch_id + 1
            else:
                new_selected = self.catch_id - 1
        else:
            new_selected = self.catch_id

        pokemon = self.user.pokemons.pop(self.catch_id)
        query = 'UPDATE users SET pokemons = ARRAY_REMOVE(users.pokemons, $1), selected = $2 WHERE id = $3'

        await self.pool.execute(query, str(pokemon.entry.id), new_selected, self.user.id)
        await self.pool.execute('UPDATE pokemons SET owner_id = 0 WHERE id = $1', str(pokemon.id))

        self.pool.add_free_pokemon(pokemon)
        self.user.data['selected'] = new_selected

    async def select(self) -> None:
        if not self.exists():
            raise ValueError(f'Pokemon {self.entry.nickname!r} does not exist')

        if self.is_selected():
            raise ValueError(f'{self.entry.nickname!r} is already selected.')

        entry = self.entry
        await self.pool.execute(
            'UPDATE users SET selected = $1 WHERE id = $2', entry.catch_id, self.user.id
        )

        self.user.data['selected'] = entry.catch_id

    async def transfer(self, to: User) -> None:
        if self.is_selected():
            if self.catch_id == 1:
                new_selected = self.catch_id + 1
            else:
                new_selected = self.catch_id - 1
        else:
            new_selected = self.catch_id

        pokemon = self.user.pokemons.pop(self.catch_id)
        query = 'UPDATE users SET pokemons = ARRAY_REMOVE(users.pokemons, $1), selected = $2 WHERE id = $3'
        await self.pool.execute(query, str(pokemon.entry.id), new_selected, self.user.id)

        await self.pool.execute(
            'UPDATE pokemons SET owner_id = $1 WHERE id = $2', 
            to.id, str(pokemon.id)
        )

        catch_id = to.catch_id + 1
        await self.pool.execute(
            'UPDATE users SET pokemons = ARRAY_APPEND(users.pokemons, CAST($1 as UUID)), catch_id = $2 WHERE id = $3', 
            str(pokemon.id), catch_id, to.id
        )

        to.pokemons[catch_id] = pokemon

        to.data['catch_id'] = catch_id
        self.user.data['selected'] = new_selected

class User(RecordModel):
    def __init__(self, record: asyncpg.Record, pokemons: List[asyncpg.Record], pool: Pool) -> None:
        super().__init__(record, pool)
        self._update_pokemons(pokemons)
    
        self.data = dict(record)

    def _update_pokemons(self, records: List[asyncpg.Record]) -> None:
        records = sorted(records, key=lambda record: record['catch_id'])
        self.pokemons = {pokemon['catch_id']: UserPokemon(self, dict(pokemon)) for pokemon in records}

    @property
    def credits(self) -> int:
        return self.data['credits']

    @property
    def catch_id(self) -> int:
        return self.data['catch_id']

    @property
    def selected(self) -> int:
        return self.data['selected']

    @property
    def redeems(self) -> int:
        return self.data['redeems']

    def find(self, **attrs: Any) -> List[UserPokemon]:
        pokemons = [
            pokemon for pokemon in self.pokemons.values() 
            if all(pokemon.data[key] == value for key, value in attrs.items())
        ]

        return pokemons

    def get_selected(self) -> UserPokemon:
        return self.pokemons.get(self.selected) # type: ignore

    def get_unique_pokemons(self) -> List[UserPokemon]:
        pokemons: List[UserPokemon] = []
        seen: List[int] = []

        for pokemon in self.pokemons.values():
            if pokemon.dex.id in seen:
                continue

            pokemons.append(pokemon)
            seen.append(pokemon.dex.id)

        return pokemons

    def get_pokemons(self, dex_id: int) -> List[UserPokemon]:
        return [pokemon for pokemon in self.pokemons.values() if pokemon.dex.id == dex_id]

    async def get_catch_count_for(self, dex_id: int) -> int:
        record = await self.pool.fetchrow(
            'SELECT COUNT(id) FROM pokemons WHERE owner_id = $1 AND dex_id = $2', self.id, dex_id
        )

        assert record
        return record['count']

    async def add_redeems(self, amount: int) -> None:
        await self.pool.execute('UPDATE users SET redeems = redeems + $1 WHERE id = $2', amount, self.id)
        self.data['redeems'] += amount

    async def add_redeem(self) -> None:
        await self.add_redeems(1)

    async def remove_redeems(self, amount: int) -> None:
        await self.pool.execute('UPDATE users SET redeems = redeems - $1 WHERE id = $2', amount, self.id)
        self.data['redeems'] -= amount

    async def remove_redeem(self) -> None:
        await self.remove_redeems(1)
        
    async def add_credits(self, amount: int) -> None:
        await self.pool.execute('UPDATE users SET credits = credits + $1 WHERE id = $2', amount, self.id)
        self.data['credits'] += amount

    async def remove_credits(self, amount: int) ->  None:
        await self.pool.execute('UPDATE users SET credits = credits - $1 WHERE id = $2', amount, self.id)
        self.data['credits'] -= amount
            
    async def add_pokemon(
        self,
        pokemon_id: int, 
        level: int = 1, 
        exp: int = 0, 
        is_shiny: bool = False,
        *,
        ivs: Optional[IVs] = None,
        evs: Optional[EVs] = None,
        moves: Optional[Moves] = None,
        nickname: Optional[str] = None,
    ) -> UserPokemon:
        catch_id = self.catch_id + 1
        pokemon = self.pool.get_free_pokemon(pokemon_id, is_shiny=is_shiny)

        if pokemon is not None:
            await pokemon.edit(owner_id=self.id, catch_id=catch_id, level=level, exp=exp)
            self.pokemons[catch_id] = pokemon

            return pokemon

        entry = self.pool.create_pokemon(pokemon_id, self.id, catch_id, is_shiny)

        entry.level = level
        entry.exp = exp

        if ivs is not None:
            entry.ivs = ivs
        if evs is not None:
            entry.evs = evs
        if nickname is not None:
            entry.nickname = nickname
        if moves is not None:
            entry.moves = moves

        await entry.create(self.pool)

        pokemon = UserPokemon(self, entry.to_dict())
        await pokemon.save()

        await self.pool.execute('UPDATE users SET catch_id = $1 WHERE id = $2', catch_id, self.id)
        self.data['catch_id'] = catch_id

        return pokemon

    async def reindex(self) -> None:
        index = 1
        selected = 1

        data: List[Tuple[int, str]] = []
        for pokemon in sorted(self.pokemons.values(), key=lambda poke: poke.catch_id):
            if pokemon.is_selected():
                selected = index

            pokemon.data['catch_id'] = index
            data.append((index, str(pokemon.id)))

            index += 1

        self.data['catch_id'] = index - 1
        self.data['selected'] = selected

        await self.pool.execute('UPDATE users SET selected = $1, catch_id = $2 WHERE id = $3', selected, index - 1, self.id)    
        await self.pool.executemany('UPDATE pokemons SET catch_id = $1 WHERE id = $2', data)

        records = await self.pool.fetch('SELECT * FROM pokemons WHERE owner_id = $1', self.id)
        self._update_pokemons(records)

    async def refetch(self):
        record = await self.pool.fetchrow('SELECT * from users WHERE id = $1', self.id)
        assert record

        self.record = record

    async def delete(self) -> None:
        await self.pool.execute('DELETE FROM users WHERE id = $1', self.id)
        self.pool.users.pop(self.id, None)

        await self.pool.execute('DELETE FROM pokemons WHERE owner_id = $1', self.id)