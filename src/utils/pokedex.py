from __future__ import annotations

from typing import Any, Callable, Dict, NamedTuple, List, Optional
from discord.ext import commands
import pathlib
import functools
import orjson
import random
import re
import enum

from . import utils
from .context import Context
from src.consts import DATA

__all__ = (
    'PokedexEntry',
    'Pokedex',
)

class Rarity(str, enum.Enum):
    Common = 'common'
    UltraBeast = 'ultra_beast'
    Mythical = 'mythical'
    Legendary = 'legendary'

class EvolutionCondition(str, enum.Enum):
    Time = 'time'
    HeldItem = 'held_item'
    TriggerItem = 'trigger_item'

class EvolutionTime(str, enum.Enum):
    Day = 'day'
    Night = 'night'

class PokemonStats(NamedTuple):
    hp: int
    atk: int
    defense: int
    spatk: int
    spdef: int
    speed: int

class PokemonNames(NamedTuple):
    en: str
    jp: Optional[str]
    fr: Optional[str]
    de: Optional[str]
    jp_r: Optional[str]
    jp_t: Optional[str]

class PokemonRarity(NamedTuple):
    mythical: bool
    legendary: bool
    ultra_beast: bool
    event: bool

class PokemonTypes(NamedTuple):
    first: str
    second: Optional[str]

class MegaPokemonEvolutions(NamedTuple):
    normal: Optional[int]
    y: Optional[int]
    x: Optional[int]

class PokemonEvolutions(NamedTuple):
    to: List[int]
    at: Optional[int]
    time: Optional[EvolutionTime]
    held_item: Optional[str]
    trigger_item: Optional[str]
    from_: Optional[int]
    mega: MegaPokemonEvolutions
    conditions: List[EvolutionCondition]

class PokemonImages(NamedTuple):
    default: pathlib.Path[str]
    shiny: pathlib.Path[str]

class PokedexEntry(commands.Converter[Any]):
    dex: int
    id: int
    slug: str
    description: str
    region: str
    height: int
    weight: int
    names: PokemonNames
    types: PokemonTypes
    stats: PokemonStats
    evolutions: PokemonEvolutions
    rarity: PokemonRarity
    catchable: bool
    is_form: bool
    enabled: bool
    images: PokemonImages

    def __init__(self, **kwargs: Any) -> None:
        for key, value in kwargs.items():
            setattr(self, key, value)

        self.images = PokemonImages(
            default=pathlib.Path(f'src/assets/{self.id}.png'),
            shiny=pathlib.Path(f'src/assets/shiny/{self.id}.png')
        )

    def __repr__(self) -> str:
        return f'<PokedexEntry dex={self.dex} id={self.id} region={self.region!r} default_name={self.default_name!r}>'

    @classmethod
    async def convert(cls, ctx: Context, argument: str) -> PokedexEntry:
        if argument.isdigit():
            entry = ctx.bot.pokedex.get_pokemon(int(argument))
            if entry is None:
                raise commands.BadArgument(f'Pokémon {argument} does not exist.')

            return entry

        entries = ctx.bot.pokedex.find(lambda entry: entry.default_name.casefold() == argument.casefold())
        if not entries:
            raise commands.BadArgument(f'Pokémon {argument} does not exist.')

        return entries[0]

    @property
    def default_name(self) -> str:
        return self.names.en

    def get_rarity_name(self) -> str:
        if self.rarity.legendary:
            return 'Legendary'
        elif self.rarity.mythical:
            return 'Mythical'
        elif self.rarity.ultra_beast:
            return 'Ultra Beast'
        else:
            return 'Event'

class PokedexReader:
    def __init__(self, path: pathlib.Path[str]):
        self.path = path
        self.rows = self.read()

    def __repr__(self) -> str:
        return '<PokedexReader path={0.path!r}>'.format(self)

    def __iter__(self):
        return iter(self.rows)
                
    def read(self) -> List[Dict[str, Any]]:
        with self.path.open('r', encoding='utf-8') as file:
            return orjson.loads(file.read())

    def sort(self, key: str, reverse: bool = False) -> Dict[str, Any]:
        rows = sorted(self.rows, key=lambda x: x.get(key, ''), reverse=reverse)
        return {row[key]: row for row in rows if key in row}

class Pokedex:
    def __init__(self) -> None: 
        self.reader = PokedexReader(self.path)
        self.pokemons: Dict[int, PokedexEntry] = self.create_all_pokemons()

    def __iter__(self):
        return iter(self.pokemons.values())

    @property
    def path(self) -> pathlib.Path:
        return DATA / 'pokedex.json'

    @property
    def entries(self) -> List[PokedexEntry]:
        return list(self)

    @functools.cached_property
    def names(self) -> List[str]:
        return [pokemon.default_name for pokemon in self]

    @functools.cached_property
    def legendaries(self) -> List[PokedexEntry]:
        return self.find(lambda pokemon: pokemon.rarity.legendary)

    @functools.cached_property
    def mythicals(self) -> List[PokedexEntry]:
        return self.find(lambda pokemon: pokemon.rarity.mythical)

    @functools.cached_property
    def ultra_beasts(self) -> List[PokedexEntry]:
        return self.find(lambda pokemon: pokemon.rarity.ultra_beast)

    @functools.cached_property
    def commons(self) -> List[PokedexEntry]:
        return self.find(lambda pokemon: not any([*pokemon.rarity, pokemon.is_form]))

    def random(self, *, rarity: Optional[Rarity] = None) -> PokedexEntry:
        if rarity is None:
            return random.choice(self.entries)

        return random.choice(self.with_rarity(rarity))

    def find(self, predicate: Callable[[PokedexEntry], bool]) -> List[PokedexEntry]:
        return utils.find(self, predicate)

    def with_language(self, language: str) -> Dict[str, PokedexEntry]:
        pokemons = self.find(lambda pokemon: getattr(pokemon.names, language, None) is not None)
        return {getattr(pokemon.names, language): pokemon for pokemon in pokemons}

    def with_rarity(self, rarity: Rarity) -> List[PokedexEntry]:
        return self.find(lambda pokemon: getattr(pokemon.rarity, rarity, False))

    def with_form(self, form: str) -> List[PokedexEntry]:
        return self.find(lambda pokemon: pokemon.default_name.startswith(form.title()) and pokemon.is_form)

    def get_pokemon(self, pokemon_id: int) -> Optional[PokedexEntry]:
        return self.pokemons.get(pokemon_id)

    def create_all_pokemons(self) -> Dict[int, PokedexEntry]:
        pokemons: Dict[int, PokedexEntry] = {}

        for row in self.reader:
            pokemon = self.create_pokemon(row)
            pokemons[pokemon.id] = pokemon

        return pokemons

    def create_pokemon(self, row: Dict[str, Any]) -> PokedexEntry:
        descprition = re.sub(r'\n', ' ', row.get('description', ''))
        return PokedexEntry(
            dex=row['dex_number'],
            id=row['id'],
            slug=row['slug'],
            description=descprition,
            region=row['region'],
            height=row['height'] / 10,
            weight=row['weight'] / 10,
            names=self.create_names(row),
            types=self.create_types(row),
            stats=self.create_stats(row),
            evolutions=self.create_evolutions(row),
            rarity=self.create_rarity(row),
            is_form=row.get('is_form', False),
            catchable=row.get('catchable', False),
            enabled=row.get('enabled', False)
        )

    def create_stats(self, data: Dict[str, Any]) -> PokemonStats:
        return PokemonStats(
            hp=data['hp'],
            atk=data['atk'],
            defense=data['defense'],
            spatk=data['spatk'],
            spdef=data['spdef'],
            speed=data['speed']
        )

    def create_evolutions(self, data: Dict[str, Any]) -> PokemonEvolutions:
        mega = MegaPokemonEvolutions(
            normal=data.get('evo.mega'),
            y=data.get('evo.mega_y'),
            x=data.get('evo.mega_x')
        )

        to = []
        if 'evo.to' in data:
            to = data['evo.to']
            if not isinstance(to, list):
                to = [to]

        evolutions = PokemonEvolutions(
            to=to,
            at=data.get('evo.level'),
            time=EvolutionTime(data['evo.time']) if 'evo.time' in data else None,
            held_item=data.get('evo.held_item_id'),
            trigger_item=data.get('evo.trigger_item_id'),
            from_=data.get('evo.from'),
            mega=mega,
            conditions=[EvolutionCondition(cond) for cond in data.get('evo.conditions', [])]
        )

        return evolutions

    def create_types(self, data: Dict[str, Any]) -> PokemonTypes:
        return PokemonTypes(
            first=data['type.0'],
            second=data.get('type.1')
        )

    def create_rarity(self, data: Dict[str, Any]) -> PokemonRarity:
        return PokemonRarity(
            mythical=data.get('mythical', False),
            legendary=data.get('legendary', False),
            ultra_beast=data.get('ultra_beast', False),
            event=data.get('event', False)
        )

    def create_names(self, data: Dict[str, Any]) -> PokemonNames:
        return PokemonNames(
            en=data.get('name.en', data['slug']),
            jp=data.get('name.ja'),
            fr=data.get('name.fr'),
            de=data.get('name.de'),
            jp_r=data.get('name.ja_r'),
            jp_t=data.get('name.ja_t')
        )