from discord.ext import commands, menus

from bot import Pokecord, Context
from utils.menus import MarketListingsSource

class Market(commands.Cog):
    def __init__(self, bot: Pokecord) -> None:
        self.bot = bot

    @commands.group(name='market', aliases=['marketplace', 'm'], invoke_without_command=True)
    async def market(self, ctx):
        pass

    @market.command(name='listings', aliases=['l'])
    async def _listings(self, ctx: Context):
        user = await self.bot.pool.get_user(ctx.author.id)
        listings = await user.get_market_listings()

        source = MarketListingsSource(listings._listings, self.bot)
        pages = menus.MenuPages(source=source)

        await pages.start(ctx)

    @market.command('add')
    async def _add(self, ctx: Context, id: int, price: int):
        user = await self.bot.pool.get_user(ctx.author.id)
        listings = await user.get_market_listings()

        if len(user.pokemons) == 1:
            return await ctx.send('You need to have atleast 2 pokemons.')

        selected = user.get_selected()[0]
        if selected.id == id:
            return await ctx.send('You can not sell your selected pokemon.')

        await listings.add(id, price)