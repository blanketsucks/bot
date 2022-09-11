from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional, Dict, Any, NamedTuple, Tuple
import dataclasses
import uuid
import discord

from src.utils import sequence
from src.utils.pokedex import PokedexEntry

if TYPE_CHECKING:
    from src.bot import Pokecord
    from .user import User
    from .pool import Pool

class Moves(NamedTuple):
    first: str
    second: Optional[str] = None
    third: Optional[str] = None
    fourth: Optional[str] = None

    @classmethod
    def from_dict(cls, data: List[str]) -> Moves:
        return cls(*data)

    @classmethod
    def default(cls) -> Moves:
        return cls(first='tackle', second=None, third=None, fourth=None)

class IVs(NamedTuple):
    hp: int
    atk: int
    defense: int
    spatk: int
    spdef: int
    speed: int

    @classmethod
    def from_dict(cls, data: List[int]) -> IVs:
        return cls(*data)

    @classmethod
    def generate(cls) -> IVs:
        ivs = sequence(0, 31, 6)
        return cls(*ivs)

    @classmethod
    def max(cls) -> IVs:
        return cls(hp=31, atk=31, defense=31, spatk=31, spdef=31, speed=31)
    
    def round(self) -> float:
        return round((sum(self) / 186) * 100, 2)

class EVs(NamedTuple):
    hp: int
    atk: int
    defense: int
    spatk: int
    spdef: int
    speed: int

    @classmethod
    def from_dict(cls, data: List[int]) -> EVs:
        return cls(*data)

    @classmethod
    def generate(cls) -> EVs:
        evs = sequence(0, 255, 6)
        return cls(*evs)

    @classmethod
    def max(cls) -> EVs:
        return cls(hp=255, atk=255, defense=255, spatk=255, spdef=255, speed=255)

@dataclasses.dataclass
class Pokemon:
    id: uuid.UUID
    dex_id: int
    owner_id: int
    nickname: str
    level: int
    exp: int
    ivs: IVs
    evs: EVs
    moves: Moves
    nature: str
    catch_id: int
    is_shiny: bool
    is_starter: bool
    is_favourite: bool

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Pokemon:
        return cls(
            id=data['id'],
            dex_id=data['dex_id'],
            owner_id=data['owner_id'],
            nickname=data['nickname'],
            level=data['level'],
            exp=data['exp'],
            ivs=IVs.from_dict(data['ivs']),
            evs=EVs.from_dict(data['evs']),
            moves=Moves.from_dict(data['moves']),
            nature=data['nature'],
            catch_id=data['catch_id'],
            is_shiny=data['is_shiny'],
            is_starter=data['is_starter'],
            is_favourite=data['is_favourite']
        )

    @classmethod
    def new(cls, entry: PokedexEntry, nature: str, owner_id: int, catch_id: int, is_shiny: bool) -> Pokemon:
        return cls(
            id=uuid.uuid4(),
            dex_id=entry.id,
            owner_id=owner_id,
            nickname=entry.default_name,
            level=1,
            exp=0,
            ivs=IVs.generate(),
            evs=EVs.generate(),
            moves=Moves.default(),
            nature=nature,
            catch_id=catch_id,
            is_shiny=is_shiny,
            is_starter=False,
            is_favourite=False
        )

    async def create(self, pool: Pool) -> None:
        data: List[Any] = []
        keys = self.__dataclass_fields__.keys()

        for key in keys:
            value = getattr(self, key)
            if isinstance(value, uuid.UUID):
                data.append(str(value))
            else:
                data.append(value)

        query = 'INSERT INTO pokemons('

        query += ', '.join(keys)
        query += ') VALUES('

        query += ', '.join([f'${i}' for i in range(1, len(data) + 1)])
        query += ')'

        await pool.execute(query, *data)

    async def update(self, pool: Pool) -> None:
        data: List[Any] = []

        keys = list(self.__dataclass_fields__.keys())
        keys.remove('id')

        for key in keys:
            value = getattr(self, key)
            data.append(value)

        query = 'UPDATE pokemons SET '

        query += ', '.join([f'{key} = ${i}' for i, key in enumerate(keys, start=1)])
        query += f' WHERE id = ${len(keys) + 1}'

        data.append(str(self.id))        
        await pool.execute(query, *data)

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)