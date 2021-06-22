import json
import math
import random

def _round(ivs: list[int]):
    num = 0

    for iv in ivs:
        num += iv

    return round((num / 186) * 100, 2)

def get_ivs():
    ivs = []

    for i in range(6):
        iv = random.randint(0, 31)
        ivs.append(iv)

    return ivs, _round(ivs)

def calculate_health(base: int, iv: int, level: int):
    if base == 1:
        return 1

    return math.floor(0.01 * (2 * base + iv) * 100) + level + 10

def calculate_other(base: int, iv: int, level: int, nature: int):
    return math.floor(((0.01 * (2 * base + iv) * level) + 5) * nature)

def chance(__chance: int):
    return random.randint(0, __chance) == random.randint(0,  __chance)

def critical():
    crit = chance(24)

    if crit:
        return 1.5

    return 1

def damage(level: int, power: int, attack: int, defense: int, type: int):
    base = (((((2 * level) / 5) + 2) * power * attack / defense) / 50) + 2
    dmg = base * 1 * 1 * 1 * critical() * random.choice([0.85, 1]) * 1.5 * type * 1 * 1

    return dmg

def miss(acc: int):
    if acc == 100:
        return False

    return chance(acc)