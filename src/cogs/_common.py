from typing import Optional

from src.utils import flags

class CommonPokemonFlags(flags.FlagParser):
    level: Optional[int]
    name: Optional[str] = flags.flag(aliases=['n'])
    mythical: bool = flags.flag(aliases=['myth'])
    legendary: bool = flags.flag(aliases=['leg'])
    ultra_beast: bool = flags.flag(name='ultra-beast', aliases=['ub'])
    shiny: bool = flags.flag(aliases=['sh'])