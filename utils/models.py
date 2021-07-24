import csv
import dataclasses
import json
from typing import Callable, Dict, Tuple, Type, Union
from pprint import pprint

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

def _get_evolution_level(name: str) -> int:
    with open('evolutions.json', 'r') as f:
        evolutions = json.load(f)

    return int(evolutions[name]['level'])

def _get_evolution(pokemon: 'PokemonEntry'):
    if not isinstance(pokemon, PokemonEntry):
        return None

    evo = _Evolution(
        id=pokemon.id,
        dex=pokemon.dex,
        region=pokemon.region,
        slug=pokemon.slug,
        description=pokemon.description,
        enabled=pokemon.enabled,
        catchable=pokemon.catchable,
        names=pokemon.names,
        types=pokemon.types,
        rarity=pokemon.rarity,
        height=pokemon.height,
        weight=pokemon.weight,
        evolutions=pokemon.evolutions,
        stats=pokemon.stats,
        image_path=pokemon.image_path,
        shiny_image_path=pokemon.shiny_image_path
    )
    
    evo.level = _get_evolution(evo.names.en)
    return evo

def _build_pokemon(data, key):
    return build_pokemon(_pokemon_by_id(data.get(key))) if data.get(key) is not None else None

def _build_evolution(data, key):
    pokemon = _build_pokemon(data, key)
    evo = _get_evolution(pokemon)

    return evo

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
        to=_build_evolution(data, 'evo.to'),
        _from=_pokemons.get(data.get('evo.from')),
        mega=_build_pokemon(data, 'evo.mega'),
        mega_x=_build_pokemon(data, 'evo.mega_x'),
        mega_y=_build_pokemon(data, 'evo.mega_y')
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

    _by_name_ja = []
    for pokemon in pokemons:
        if pokemon.get('name.ja') is not None:
            _by_name_ja.append(pokemon)

    _by_name_ja_r = []
    for pokemon in pokemons:
        if pokemon.get('name.ja_r') is not None:
            _by_name_ja_r.append(pokemon)

    _by_name_ja_t = []
    for pokemon in pokemons:
        if pokemon.get('name.ja_t') is not None:
            _by_name_ja_t.append(pokemon)

    _by_name_fr = []
    for pokemon in pokemons:
        if pokemon.get('name.fr') is not None:
            _by_name_fr.append(pokemon)

    by_name_ja = {
        pokemon.get('name.ja'): pokemon for pokemon in _by_name_ja
    }

    by_name_ja_r = {
        pokemon.get('name.ja_r'): pokemon for pokemon in _by_name_ja_r
    }

    by_name_ja_t = {
        pokemon.get('name.ja_t'): pokemon for pokemon in _by_name_ja_t
    }

    by_name_fr = {
        pokemon.get('name.fr'): pokemon for pokemon in _by_name_fr
    }

    return by_id, by_dex, by_slug, by_name_en, by_name_fr, by_name_ja, by_name_ja_r, by_name_ja_t

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

            val = self.dex.get(id)
            return val

        id = id.title()

        val = self.slug.get(id)
        if val:
            return val

        val = self.en.get(id)
        if val:
            return val

        val = self.fr.get(id)
        if val:
            return val

        val = self.ja.get(id)
        if val:
            return val

        val = self.ja_r.get(id)
        if val:
            return val

        val = self.ja_t.get(id)
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
        attrs = ('id', 'dex', 'region', 'slug', 'height', 'weight', 'names', 'types', 'rarity')
        repr = ['<PokemonEntry']

        for attr in attrs:
            val = getattr(self, attr)
            repr.append(f'{attr}={val!r}')

        repr.append('>')
        return ' '.join(repr)

@dataclasses.dataclass
class Names:
    ja: str
    ja_r: str
    ja_t: str
    en: str
    de: str
    fr: str

    def __iter__(self):
        self._iter = iter([self.ja, self.ja_r, self.ja_t, self.fr, self.en])
        return self

    def __next__(self):
        return next(self._iter)

    def __repr__(self) -> str:
        return '<Names en={0.en!r} fr={0.fr!r} ja={0.ja!r} ja_r={0.ja_r!r} ja_t={0.ja_t!r}>'.format(self)

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

    def __repr__(self) -> str:
        return '<Stats hp={0.hp} atk={0.atk} defense={0.defense} spatk={0.spatk} spdef={0.spdef} speed={0.speed}>'.format(self)

@dataclasses.dataclass
class Evolution:
    to: '_Evolution'
    _from: 'PokemonEntry'
    mega: 'PokemonEntry'
    mega_x: 'PokemonEntry'
    mega_y: 'PokemonEntry'

    def __repr__(self) -> str:
        attrs = ('to', '_from', 'mega', 'mega_x', 'mega_y')
        repr = ['<Evolution']

        for attr in attrs:
            val = getattr(self, attr)
            if not val:
                val = 'None'
            else:
                val = str(val.id)

            repr.append(f'{attr}={val}')
        return ' '.join(repr) + '>'

class _Evolution(PokemonEntry):
    level: int