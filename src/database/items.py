from __future__ import annotations

from typing import TYPE_CHECKING, Any, List, Optional, Tuple
import dataclasses

from enum import IntEnum
import asyncpg

if TYPE_CHECKING:
    from .pool import Pool

__all__ = ('ShopItemKind', 'ShopItem')

class ShopItemKind(IntEnum):
    Booster = 1
    NatureMints = 2
    MegaEvolutionsAndForms = 3
    Other = 4

    def as_string(self) -> str:
        if self is ShopItemKind.Booster:
            return 'XP Boosters'
        elif self is ShopItemKind.NatureMints:
            return 'Nature Mints'
        elif self is ShopItemKind.MegaEvolutionsAndForms:
            return 'Mega Evolutions & Forms'
        else:
            return 'Other'

@dataclasses.dataclass
class ShopItem:
    id: int
    name: str
    description: str
    kind: ShopItemKind
    price: int
    
    pool: Pool

    @classmethod
    def from_record(cls, pool: Pool, data: asyncpg.Record):
        return cls(
            id=data['id'],
            name=data['name'],
            description=data['description'],
            kind=ShopItemKind(data['kind']),
            price=data['price'],
            pool=pool
        )

    async def edit(
        self,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        kind: Optional[ShopItemKind] = None,
        price: Optional[int] = None
    ) -> None:
        names: List[str] = []
        values: List[Any] = []

        if name is not None:
            names.append('name'); values.append(name); self.name = name
        if description is not None:
            names.append('description'); values.append(description); self.description = description
        if kind is not None:
            names.append('kind'); values.append(kind); self.kind = kind
        if price is not None:
            names.append('price'); values.append(price); self.price = price

        query = 'UPDATE items SET '
        query += ', '.join([f'{k} = ${i}' for i, k in enumerate(names, start=1)]) + ' '

        query += 'VALUES('
        query += ', '.join([f'${i}' for i in range(1, len(names) + 1)])

        query += ')'

        await self.pool.execute(query, *values)
