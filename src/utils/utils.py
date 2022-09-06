from typing import Iterable, List, Any, TypeVar, Tuple, Callable
import enum
import itertools

__all__ = (
    'chunk',
    'find',
    'title',
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

def chunk(n: int, iterable: Iterable[T]) -> Iterable[Tuple[T, ...]]:
    it = iter(iterable)
    while True:
        chunk = tuple(itertools.islice(it, n))
        if not chunk:
            return

        yield chunk

def find(items: Iterable[T], predicate: Callable[[T], bool]) -> List[T]:
    return [item for item in items if predicate(item)]

def print_with_color(text: str, *values: str, **kwargs: Any) -> None:
    print(text.format(**Colors.__members__, **kwargs), *values)

def title(s: str) -> str:
    new = s[0].upper()
    is_first_letter = False

    for char in s[1:]:
        if char.isspace():
            new += char
            is_first_letter = True
        else:
            if is_first_letter:
                new += char.upper()
                is_first_letter = False
            else:
                new += char
    
    return new
