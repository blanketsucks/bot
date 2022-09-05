from typing import List, Any
import random
import enum

class Colors(str, enum.Enum):
    red = '\033[1;31m'
    green = '\033[1;32m'
    blue = '\033[1;34m'
    reset = '\033[0m'

__all__ = (
    'sequence',
    'get_health_stat',
    'get_other_stat',
    'chance',
    'get_critical_multiplier',
    'get_damage',
    'is_miss',
    'print_with_color'
)

def sequence(a: int, b: int, n: int) -> List[int]:
    return [random.randint(a, b) for _ in range(n)]

def get_base_stat(stat: int, iv: int, ev: int, level: int) -> int:
    return round(((2 * stat + iv + round(ev / 4)) * level) / 100)

def get_health_stat(base: int, iv: int, ev: int, level: int):
    return 1 if base == 1 else get_base_stat(base, iv, ev, level) + level + 10

def get_other_stat(base: int, iv: int, ev: int, level: int, nature: float) -> int:
    return round((get_base_stat(base, iv, ev, level) + 5) * nature)

def chance(chance: int):
    return random.randint(0, chance) == random.randint(0,  chance)

def get_critical_multiplier() -> float:
    return 1.5 if chance(24) else 1

def get_damage(level: int, power: int, attack: int, defense: int, type: int):
    base = (((((2 * level) / 5) + 2) * power * attack / defense) / 50) + 2
    dmg = base * 1 * 1 * 1 * get_critical_multiplier() * random.choice([0.85, 1]) * 1.5 * type * 1 * 1

    return dmg

def is_miss(acc: int) -> bool:
    return False if acc == 100 else chance(acc)

def print_with_color(text: str, *values: str, **kwargs: Any) -> None:
    print(text.format(**Colors.__members__, **kwargs), *values)
