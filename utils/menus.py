from discord.ext import menus
import discord
import typing

from database import Pokemon, Listing

if typing.TYPE_CHECKING:
    from bot import Pokecord

class PokemonsSource(menus.ListPageSource):
    def __init__(self, data, bot: 'Pokecord'):
        super().__init__(data, per_page=20)
        self.bot = bot

    async def format_page(self, menu, entries):
        offset = menu.current_page * self.per_page
        embed = discord.Embed(description='')

        for idx, entry in enumerate(entries, start=offset):
            level = entry.level
            id = entry.id

            rounded = entry.ivs.rounded
            embed.description += f'**{idx+1}.** **{entry.name.title()}** | Level: {level} | ID: {id} | IV: {rounded}%\n'

        return embed


class MarketListingsSource(menus.ListPageSource):
    def __init__(self, data, bot: 'Pokecord'):
        super().__init__(data, per_page=20)
        self.bot = bot

    async def format_page(self, menu, entries: typing.List[Listing]):
        offset = menu.current_page * self.per_page
        embed = discord.Embed(description='')

        if not entries:
            embed.description = 'No Listings Found.'
            return embed

        for idx, entry in enumerate(entries, start=offset):
            pokemon, _ = entry.get_pokemon()
            id = entry.id
            price = entry.price
            
            name = pokemon.name
            level = pokemon.level

            rounded = pokemon.ivs.rounded
            embed.description += f'**{idx+1}.** **{name.title()}** | Level: {level} | ID: {id} | IV: {rounded}% | Price: {price}\n'

        return embed
