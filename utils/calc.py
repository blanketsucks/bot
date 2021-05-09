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

def calculate_other(base: int, iv: int, level: int):
    return math.floor(0.01 * (2 * base + iv) * level) + 5

def chance(__chance: int):
    return random.randint(1, __chance) == random.randint(1,  __chance)
