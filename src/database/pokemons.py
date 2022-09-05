from __future__ import annotations

from typing import List, Optional, Dict, Any, NamedTuple
import dataclasses

from src.utils import sequence

@dataclasses.dataclass
class Moves:
    first: str
    second: Optional[str] = None
    third: Optional[str] = None
    fourth: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Moves:
        return cls(**data)

    @classmethod
    def default(cls) -> Moves:
        return cls(first='tackle', second=None, third=None, fourth=None)

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)

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


@dataclasses.dataclass
class Pokemon:
    id: int
    nickname: str
    level: int
    exp: int
    ivs: IVs
    evs: EVs
    moves: Moves
    nature: str
    catch_id: int

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Pokemon:
        moves = Moves.from_dict(data['moves'])
        ivs = IVs.from_dict(data['ivs'])
        evs = EVs.from_dict(data['evs'])

        return cls(
            id=data['id'],
            nickname=data['nickname'],
            level=data['level'],
            exp=data['exp'],
            ivs=ivs,
            evs=evs,
            moves=moves,
            nature=data['nature'],
            catch_id=data['catch_id']
        )

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)