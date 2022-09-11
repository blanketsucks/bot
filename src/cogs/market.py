from typing import List, Tuple, Optional

from discord.ext import commands
import discord

from src.bot import Pokecord
from src.utils import menus, flags
from src.utils import Context, ConfirmationView
from src.utils.pokedex import PokedexEntry
from src.database.user import UserPokemon
from src.database.market import MarketListing
from src.database.pokemons import Pokemon
from src.utils.menus.views import ViewMenuPages

class MarketSearchFlags(flags.FlagParser):
    price: Optional[str]
    name: Optional[str] = flags.flag(aliases=['n'])
    sort: Optional[str] = flags.flag(choices=['iv', 'level', 'price'])
    order: Optional[str] = flags.flag(choices=['a', 'ascending', 'd', 'descending'])
    legendary: bool = flags.flag(aliases=['leg'])
    mythical: bool = flags.flag(aliases=['myth'])
    ultra_beast: bool = flags.flag(name='ultra-beast', aliases=['ub'])
    shiny: bool = flags.flag(aliases=['sh'])
    mine: bool = flags.flag(aliases=['me'])

class MarketListingsSource(menus.ListPageSource[Tuple[Pokemon, MarketListing]]):
    def __init__(self, bot: Pokecord, entries: List[Tuple[Pokemon, MarketListing]]):
        self.bot = bot
        super().__init__(entries, per_page=20)

    async def format_page(self, menu: menus.MenuPages, entries: List[Tuple[Pokemon, MarketListing]]):
        embed = discord.Embed(color=0x36E3DD)

        description = []
        for pokemon, entry in entries:
            ret = f'{entry.id}. '

            name = self.bot.pokedex.get_pokemon(pokemon.dex_id).default_name # type: ignore
            if pokemon.is_shiny:
                ret += '✨ '

            ret += f'**{name}** | Level {pokemon.level} | IV: {pokemon.ivs.round()}% | Price: {entry.price} credits'

            name = f'Level {pokemon.level} {pokemon.ivs.round()}% IV '
            if pokemon.is_shiny:
                name += '✨ '

            name += self.bot.pokedex.get_pokemon(pokemon.dex_id).default_name # type: ignore
            description.append(ret)

        embed.description = '\n'.join(description)

        end = (1 if menu.current_page == 0 else menu.current_page) * self.per_page
        if end > len(self.entries):
            end = len(entries)

        start = end - self.per_page + 1
        if start <= 0:
            start = 1

        embed.set_footer(text=f'Showing {start}/{end} entries out of {len(self.entries)}.')

        return embed

class Market(commands.Cog):
    def __init__(self, bot: Pokecord) -> None:
        self.bot = bot

    @commands.group(invoke_without_command=True, aliases=['m'])
    async def market(self, ctx: Context) -> None: ...

    @market.command(aliases=['a'])
    async def add(self, ctx: Context, pokemon: UserPokemon, price: int):
        if pokemon.is_favourite():
            return await ctx.send('You cannot add favourited pokémons to the market.')
        elif pokemon.is_starter():
            return await ctx.send('You cannot add your starter to the market.')

        if price >= 9223372036854775807:
            return await ctx.send(
                'Listing price must be between 0 and 9,223,372,036,854,775,807 credits.'
            )
        elif price < 0:
            return await ctx.send(
                'Listing price must be between 0 and 9,223,372,036,854,775,807 credits.'
            )

        name = f'Level {pokemon.level} {pokemon.ivs.round()}% IV '
        if pokemon.is_shiny():
            name += '✨ '

        name += pokemon.dex.default_name

        view = ConfirmationView(ctx.author) # type: ignore
        view.message = await ctx.send(f'Are you sure you want to list your **{name}** for **{price}** credits?', view=view)

        await view.wait()
        await view.message.delete()

        if not view.value:
            return await ctx.send('Aborted.')

        market = await self.bot.pool.get_market()
        await market.add_listing(price, pokemon)

        await ctx.send('Successfully added your pokémon to the market.')

    @market.command(aliases=['i'])
    async def info(self, ctx: Context, id: int):
        market = await self.bot.pool.get_market()
        listing = await market.get_listing(id)

        if not listing:
            return await ctx.send('Listing not found.')

        data = await listing.fetch_pokemon_data()
        entry = UserPokemon(ctx.pool.user, data) # Provide a fake user to the pokemon since it won't matter either way

        embed, file = entry.build_discord_embed_for(
            ctx.pool.user, show_favourite=False, show_nickname=False, add_footer=False
        )

        embed.add_field(name='Market Listing', value=f'**ID**: {listing.id}\n**Price**: {listing.price} credits')

        embed.set_footer(text=f'Owner ID: {listing.owner_id}')
        await ctx.send(embed=embed, file=file)

    @market.command(aliases=['s'])
    async def search(self, ctx: Context, *, flags: MarketSearchFlags = MarketSearchFlags.default()):
        market = await self.bot.pool.get_market()
        listings = list(market.listings.values())

        entries: List[Tuple[Pokemon, MarketListing]] = []

        for listing in listings:
            pokemon = await listing.fetch_pokemon()
            entry: PokedexEntry = self.bot.pokedex.get_pokemon(pokemon.dex_id) # type: ignore

            if flags.price is not None:
                price = flags.price
                order = 'eq'

                if flags.price.endswith('>'):
                    price = flags.price.removesuffix('>')
                    order = 'gt'
                elif flags.price.endswith('<'):
                    price = flags.price.removesuffix('<')
                    order = 'lt'

                try:
                    price = int(price)
                except ValueError:
                    return await ctx.send('Invalid price argument.')

                if order == 'eq':
                    if listing.price != price: continue
                elif order == 'gt':
                    if listing.price < price: continue
                else:
                    if listing.price > price: continue
            if flags.name is not None:
                if pokemon.nickname.casefold() != flags.name.casefold(): continue
            if flags.legendary:
                if not entry.rarity.legendary: continue
            if flags.mythical:
                if not entry.rarity.mythical: continue
            if flags.ultra_beast:
                if not entry.rarity.ultra_beast: continue
            if flags.shiny:
                if not pokemon.is_shiny: continue
            if flags.mine:
                if listing.owner_id != ctx.author.id: continue
            
            entries.append((pokemon, listing))

        if flags.sort is not None:
            if flags.sort == 'iv':
                entries.sort(key=lambda entry: entry[0].ivs.round())
            elif flags.sort == 'level':
                entries.sort(key=lambda entry: entry[0].level)
            else:
                entries.sort(key=lambda entry: entry[1].price)

        if flags.order is not None:
            if flags.order in ('d', 'descending'):
                entries.reverse()

        if not entries:
            return await ctx.send('No results found.')

        source = MarketListingsSource(self.bot, entries)
        menu = ViewMenuPages(source)
        
        await menu.start(ctx)

    @market.command(aliases=['r'])
    async def remove(self, ctx: Context, id: int):
        market = await self.bot.pool.get_market()
        listing = await market.get_listing(id)

        if not listing:
            return await ctx.send('Listing not found.')

        if listing.owner_id != ctx.author.id:
            return await ctx.send('You do not own that listing.')

        await listing.cancel()
        await ctx.send('Successfully removed that listing from the market.')

    @market.command(aliases=['b'])
    async def buy(self, ctx: Context, id: int):
        market = await self.bot.pool.get_market()
        listing = await market.get_listing(id)

        if not listing:
            return await ctx.send('Listing not found.')

        if listing.price > ctx.pool.user.credits:
            return await ctx.send('You do not have enough credits.')

        if listing.owner_id == ctx.pool.user.id:
            return await ctx.send('You cannot buy your own listing.')

        pokemon = await listing.fetch_pokemon()
        name = f'Level {pokemon.level} {pokemon.ivs.round()}% IV '
        if pokemon.is_shiny:
            name += '✨ '

        name += self.bot.pokedex.get_pokemon(pokemon.dex_id).default_name # type: ignore

        view = ConfirmationView(ctx.author) # type: ignore
        view.message = await ctx.send(
            f'Are you sure you want to buy this **{name}** for **{listing.price}** credits?', view=view
        )

        await view.wait()
        await view.message.delete()

        if not view.value:
            return await ctx.send('Aborted.')

        await listing.buy(ctx.pool.user)
        await ctx.send('Successfully bought that market listing.')

async def setup(bot: Pokecord):
    await bot.add_cog(Market(bot))
