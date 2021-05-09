from .moves import AffectingMoves

from dataclasses import dataclass

@dataclass
class Stats:
    hp: 'Health'
    attack: 'Attack'
    defense: 'Defense'
    spattack: 'SPAttack'
    spdef: 'SPDefense'
    speed: 'Speed'

class Stat:
    name: str
    id: int

    def __init__(self, __data, __session) -> None:
        self._data = __data
        self.__session = __session

        self.index = self._data.get('game_index', 0)
        self.base = __data['base']

        self._affecting = AffectingMoves(__data['affecting_moves'], __session)

        self.is_battle_only = self._data.get('is_battle_only', False)

    def __repr__(self) -> str:
        return '<{0.__class__.__name__} base={0.base} effort={0.effort}>'.format(self)

    @property
    def effort(self):
        return self._data.get('effort', 0)

    @property
    def affecting_moves(self):
        return self._affecting

    
class Health(Stat):
    name = 'hp'
    id = 1

class Attack(Stat):
    name = 'attack'
    id = 2

class Defense(Stat):
    name = 'defense'
    id = 3

class SPAttack(Stat):
    name = 'special-attack'
    id = 4

class SPDefense(Stat):
    name = 'special-defense'
    id = 5

class Speed(Stat):
    name = 'speed'
    id = 6

_stats = {
    1: Health,
    2: Attack,
    3: Defense,
    4: SPAttack,
    5: SPDefense,
    6: Speed,
}

_names = (cls.name for cls in _stats.values())