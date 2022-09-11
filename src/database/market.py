from __future__ import annotations

from typing import Dict, TYPE_CHECKING, Any, List, Optional

import uuid
import asyncpg

from .user import Pokemon, User, UserPokemon

if TYPE_CHECKING:
    from .pool import Pool

class MarketListing:
    def __init__(self, market: Market, data: Dict[str, Any]) -> None:
        self.data = data
        self.market = market
        self.pool = market.pool

    def __repr__(self) -> str:
        return f'<MarketListing id={self.id} price={self.price} owner_id={self.owner_id} pokemon_id={str(self.pokemon_id)!r}>'

    @classmethod
    def create(cls, market: Market, id: int, price: int, owner_id: int, pokemon_id: uuid.UUID):
        data = {'id': id, 'price': price, 'owner_id': owner_id, 'pokemon_id': pokemon_id}
        return cls(market, data)

    @property
    def id(self) -> int:
        return self.data['id']

    @property
    def price(self) -> int:
        return self.data['price']
    
    @property
    def owner_id(self) -> int:
        return self.data['owner_id']

    @property
    def pokemon_id(self) -> uuid.UUID:
        return self.data['pokemon_id']

    async def fetch_pokemon_data(self) -> Dict[str, Any]:
        record = await self.pool.fetchrow('SELECT * FROM pokemons WHERE id = $1', str(self.pokemon_id))
        assert record

        return dict(record)

    async def fetch_pokemon(self) -> Pokemon:
        data = await self.fetch_pokemon_data()
        return Pokemon.from_dict(data)

    async def fetch_owner(self) -> User:
        return await self.pool.get_user(self.owner_id) # type: ignore

    async def buy(self, user: User) -> None:
        owner = await self.fetch_owner()

        # Assuming checks have been done before to ensure the buyer has enough credits
        await owner.add_credits(self.price)
        await user.remove_credits(self.price)
    
        catch_id = user.catch_id + 1
        await self.pool.execute(
            'UPDATE pokemons SET owner_id = $1, catch_id = $2, is_listed = FALSE WHERE id = $3', 
            user.id, catch_id, self.pokemon_id
        )

        data = await self.fetch_pokemon_data()
        user.pokemons[catch_id] = UserPokemon(user, data)

        await self.pool.execute('UPDATE users SET pokemons = ARRAY_APPEND(users.pokemons, $1) WHERE id = $2', self.pokemon_id, user.id)
        await self.delete()

        self.market.listings.pop(self.id)

    async def cancel(self) -> None:
        self.market.listings.pop(self.id)
        await self.delete()

        user = await self.pool.get_user(self.owner_id)
        assert user

        await self.pool.execute('UPDATE users SET pokemons = ARRAY_APPEND(users.pokemons, $1) WHERE id = $2', self.pokemon_id, self.owner_id)
        record = await self.pool.fetchrow('SELECT * FROM pokemons WHERE id = $1', self.pokemon_id)
        assert record

        catch_id = user.catch_id + 1
        await self.pool.execute('UPDATE pokemons SET catch_id = $1 WHERE id = $2', catch_id, self.pokemon_id)


        user.pokemons[catch_id] = UserPokemon(user, dict(record))

        user.data['catch_id'] = catch_id

    async def delete(self) -> None:
        await self.pool.execute('DELETE FROM market WHERE id = $1', self.id)

class Market:
    def __init__(self, records: List[asyncpg.Record], pool: Pool) -> None:
        self.pool = pool
        self.listings: Dict[int, MarketListing] = {
            record['id']: MarketListing(self, dict(record)) for record in records
        }

    @classmethod
    async def fetch(cls, pool: Pool) -> Market:
        records = await pool.fetch('SELECT * FROM market')
        return cls(records, pool)

    async def add_listing(self, price: int, pokemon: UserPokemon) -> MarketListing:
        id: int = await self.pool.fetchval(
            'INSERT INTO market(price, owner_id, pokemon_id) VALUES($1, $2, $3) RETURNING id',
            price, pokemon.user.id, str(pokemon.id)
        )

        selected = pokemon.get_new_catch_id()
        pokemon.user.pokemons.pop(pokemon.catch_id)

        await self.pool.execute(
            'UPDATE users SET pokemons = ARRAY_REMOVE(users.pokemons, $1), selected = $2 WHERE id = $3',
            str(pokemon.id), selected, pokemon.user.id
        )

        await self.pool.execute(
            'UPDATE pokemons SET nickname = $1, is_favourite = FALSE, is_listed = TRUE WHERE id = $2', pokemon.dex.default_name, str(pokemon.id)
        )

        listing = MarketListing.create(self, id, price, pokemon.user.id, pokemon.id)
        self.listings[id] = listing

        return listing

    async def get_listing(self, id: int) -> Optional[MarketListing]:
        if id in self.listings:
            return self.listings[id]

        async with self.pool.acquire() as conn:
            record = await conn.fetchrow('SELECT * FROM market WHERE id = $1', id)
            if not record:
                return None

            listing = MarketListing(self, dict(record))
            self.listings[id] = listing

            return listing
