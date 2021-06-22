import csv
import dataclasses
from typing import Callable, Dict, Tuple, Type, Union

bool_fields = (
    'enabled',
    'catchable',
    'mythical',
    'legendary',
    'ultra_beast',
    'event',
    'is_form'
)

_pokemons = {}

def _is_number(val):
    try:
        int(val)
        return True
    except ValueError:
        return False

def read(filename: str):
    fn = f'data/{filename}.csv'
    with open(fn, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        rows = [
            {k: bool(int(v)) if k in bool_fields else v for k, v in row.items() if v != ""}
            for row in reader
        ]

        rows = [
            {k: int(v) if _is_number(v) else v for k, v in row.items()}
            for row in rows
        ]
        return rows

def build_pokemon(data: Dict[str, Union[str, int , bool]]):
    if data is None:
        return None

    if data['id'] in _pokemons:
        return _pokemons[data['id']]

    id = data['id']
    dex = data['dex_number']
    region = data['region']
    slug = data['slug']
    description = data.get('description')
    enabled = data.get('enabled', False)
    catchable = data.get('catchable', False)
    names = Names(
        ja=data.get('name.ja'),
        ja_r=data.get('name.ja_r'),
        ja_t=data.get('name.ja_t'),
        en=data['name.en'],
        de=data.get('name.de'),
        fr=data.get('name.fr')
    )
    types = Types(
        first=data['type0'],
        second=data.get('type1')
    )
    rarity = Rarity(
        mythical=data.get('mythical', False),
        legendary=data.get('legendary', False),
        ub=data.get('ultra_beast', False),
        event=data.get('event', False)
    )
    height = data['height']
    weight = data['weight']
    evolutions = Evolution(
        to=build_pokemon(_pokemon_by_id(data.get('evo.to'))) if data.get('evo.to') is not None else None,
        _from=_pokemons.get(data.get('evo.from')),
        mega=data.get('evo.mega'),
        mega_x=data.get('evo.mega_x'),
        mega_y=data.get('evo.mega_y')
    )
    stats = Stats(
        hp=data['hp'],
        atk=data['atk'],
        defense=data['defense'],
        spatk=data['spatk'],
        spdef=data['spdef'],
        speed=data['speed']
    )
    
    entry = PokemonEntry(
        id=id,
        dex=dex,
        region=region,
        slug=slug,
        description=description,
        enabled=enabled,
        catchable=catchable,
        names=names,
        types=types,
        rarity=rarity,
        height=height,
        weight=weight,
        evolutions=evolutions,
        stats=stats,
        image_path=f'data/images/{id}.png',
        shiny_image_path=f'data/images/shiny/{id}.png'
    )

    _pokemons[entry.id] = entry
    return entry
    
def _pokemon_by_id(id: int):
    ids, _, _, _, _, _, _, _ = _read_pokemons()
    return ids.get(id)

def _read_pokemons() -> Tuple[Dict, ...]:
    pokemons = read('pokemon')

    by_id = {
        pokemon['id']: pokemon for pokemon in pokemons
    }
    by_dex = {
        pokemon['dex_number']: pokemon for pokemon in pokemons
    }
    by_slug = {
        pokemon['slug']: pokemon for pokemon in pokemons
    }
    by_name_en = {
        pokemon['name.en']: pokemon for pokemon in pokemons
    }

    return by_id, by_dex, by_slug, by_name_en, {}, {}, {}, {}

def get_pokemons():
    id, dex, slug, en, fr, ja, ja_r, ja_t = _read_pokemons()

    id = {
        k: build_pokemon(v) for k, v in id.items()
    }
    dex = {
        k: build_pokemon(v) for k, v in dex.items()
    }
    slug = {
        k: build_pokemon(v) for k, v in slug.items()
    }
    en = {
        k: build_pokemon(v) for k, v in en.items()
    }
    fr = {
        k: build_pokemon(v) for k, v in fr.items()
    }
    ja = {
        k: build_pokemon(v) for k, v in ja.items()
    }
    ja_r = {
        k: build_pokemon(v) for k, v in ja_r.items()
    }
    ja_t = {
        k: build_pokemon(v) for k, v in ja_t.items()
    }

    return Pokedex(
        id=id,
        dex=dex,
        slug=slug,
        en=en,
        fr=fr,
        ja=ja,
        ja_r=ja_r,
        ja_t=ja_t
    )

@dataclasses.dataclass
class Pokedex:
    id: Dict[int, 'PokemonEntry']
    dex: Dict[int, 'PokemonEntry']
    slug: Dict[str, 'PokemonEntry']
    en: Dict[str, 'PokemonEntry']
    fr: Dict[str, 'PokemonEntry']
    ja: Dict[str, 'PokemonEntry']
    ja_r: Dict[str, 'PokemonEntry']
    ja_t: Dict[str, 'PokemonEntry']

    @property
    def entries(self):
        return len(self.id.keys())

    def get(self, id: Union[str, int]):
        if isinstance(id, int):
            val = self.id.get(id)
            if val:
                return val

            print(val, id)
            val = self.dex.get(id)
            return val

        val = self.slug.get(id)
        if val:
            return val

        val = self.en.get(id)
        if val:
            return val

    def __repr__(self) -> str:
        return '<Pokedex entries={0.entries}>'.format(self)

@dataclasses.dataclass
class PokemonEntry:
    id: int
    dex: int
    region: str
    slug: str
    description: str
    enabled: bool
    catchable: bool
    names: 'Names'
    types: 'Types'
    rarity: 'Rarity'
    height: int
    weight: int
    evolutions: 'Evolution'
    stats: 'Stats'
    image_path: str
    shiny_image_path: str

    def __repr__(self) -> str:
        return '<PokemonEntry id={0.id} dex={0.dex} region={0.region!r} slug={0.slug!r}>'.format(self)

@dataclasses.dataclass
class Names:
    ja: str
    ja_r: str
    ja_t: str
    en: str
    de: str
    fr: str

    def __repr__(self) -> str:
        return '<Names en={0.en!r} fr={0.fr!r} ja={0.ja!r}>'.format(self)

@dataclasses.dataclass
class Types:
    first: str
    second: str

    def __iter__(self):
        self._iter = iter([self.first, self.second])
        return self

    def __next__(self):
        return next(self._iter)

    def __repr__(self) -> str:
        return '<Types first={0.first!r} second={0.second!r}>'.format(self)

@dataclasses.dataclass
class Rarity:
    mythical: bool
    legendary: bool
    ub: bool
    event: bool

    def __repr__(self) -> str:
        return '<Rarity mythical={0.mythical} legendary={0.legendary} ub={0.ub} event={0.event}>'.format(self)

@dataclasses.dataclass
class Stats:
    hp: int
    atk: int
    defense: int
    spatk: int
    spdef: int
    speed: int

@dataclasses.dataclass
class Evolution:
    to: 'PokemonEntry'
    _from: 'PokemonEntry'
    mega: 'PokemonEntry'
    mega_x: 'PokemonEntry'
    mega_y: 'PokemonEntry'

