from typing import List

import random

__all__ = (
    'sequence',
    'get_health_stat',
    'get_other_stat',
    'chance',
    'get_critical_multiplier',
    'get_damage',
    'is_miss'
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