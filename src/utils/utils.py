from typing import Iterable, List, Any, TypeVar, Tuple, Callable
import enum
import itertools

__all__ = (
    'chunk',
    'find',
    'parse_integer_ordering',
    'print_with_color',
    'Colors'
)

T = TypeVar('T')

class Colors(str, enum.Enum):
    red = '\033[1;31m'
    green = '\033[1;32m'
    yellow = '\033[1;33m'
    blue = '\033[1;34m'
    reset = '\033[0m'

class Order(enum.IntEnum):
    EQ = 0
    GT = 1
    LT = 2

def chunk(n: int, iterable: Iterable[T]) -> Iterable[Tuple[T, ...]]:
    it = iter(iterable)
    while True:
        chunk = tuple(itertools.islice(it, n))
        if not chunk:
            return

        yield chunk

def find(items: Iterable[T], predicate: Callable[[T], bool]) -> List[T]:
    return [item for item in items if predicate(item)]

def parse_integer_ordering(inp: str, comp: int) -> bool:
    order = Order.EQ
    parsed = 0

    if inp[0] == '>':
        inp = inp[1:]; order = Order.GT
    elif inp[0] == '<':
        inp = inp[1:]; order = Order.LT

    parsed = int(inp)
    if order is Order.EQ:
        return comp == parsed
    elif order is Order.GT:
        return comp > parsed
    else:
        return comp < parsed

def print_with_color(text: str, *values: str, **kwargs: Any) -> None:
    print(text.format(**Colors.__members__, **kwargs), *values)