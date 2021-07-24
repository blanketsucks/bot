import enum
import json
from typing import Dict, List, Union, TYPE_CHECKING, Optional
import asyncpg

if TYPE_CHECKING:
    from .database import Pool, Pokecord
    from .user import User

class ListingState(enum.IntEnum):
    SOLD = 2
    REMOVED = 1
    PENDING = 0

class Listings:
    def __init__(self, record: asyncpg.Record, pool: 'Pool', bot: 'Pokecord', user: 'User') -> None:
        self.record = record
        self.pool = pool
        self.user = user
        self.bot = bot

        print(self.entries)
        self._listings = [
            Listing(data, self.user) for data in self.entries
        ]

    @property
    def user_id(self) -> int:
        return self.record['user_id']
        
    @property
    def entries(self) -> List[Dict]:
        return json.loads(self.record['entries'])

    def _get_listings_by_name(self, name: str, user: 'User'):
        entries = [Listing(data, user) for data in self.entries]
        if isinstance(name, int):
            return [], entries

        listings = []

        for entry in entries:
            pokemon = entry.get_pokemon()
            if name.lower() == pokemon.name.lower():
                listings.append(entry)

        return listings, entries

    def _get_listing_by_id(self, id: int, entries: List['Listing']):
        listing = None
        for entry in entries:
            if entry.id == id:
                listing = entry

        return listing

    def get(self, id: Union[str, int]) -> Optional[Union['Listing', List['Listing']]]:
        listings, entries = self._get_listings_by_name(id, self.user)

        if listings:
            return listings

        if isinstance(id, int):
            listing = self._get_listing_by_id(id, entries)
            return listing

        return None

    async def add(self, id: Union[str, int], price: int):
        copy = self.entries.copy()

        state = ListingState.PENDING
        pokemon = self.user.get_pokemon(id)

        if not pokemon:
            return False

        data = {
            'pokemon': pokemon._data,
            'price': price,
            'state': state,
            'id': self.bot.current_market_id
        }

        copy.append(data)
        self.bot.increment_market_id()

        async with self.pool.acquire() as conn:
            await conn.execute(
                'UPDATE market SET entries = $1 WHERE user_id = $2',
                json.dumps(copy), self.user_id 
            )
            return True

    async def remove(self, id: int):
        pass

class Listing:
    def __init__(self, data: Dict, user: 'User') -> None:
        self.user = user
        self.state = ListingState(data['state'])
        self.id: int = data['id']
        self._data = data['pokemon']
        self.price: int = data['price']

    def get_pokemon(self):
        return self.user.get_pokemon_by_id(self._data['id'])