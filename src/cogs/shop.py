from typing import Any, Callable, Coroutine, Dict, Optional

import discord
from discord.ext import commands

from src.bot import Pokecord
from src.utils import Context, find
from src.database.items import ShopItemKind, ShopItem

async def _noop(*args: Any): ...

class Shop(commands.Cog):
    def __init__(self, bot: Pokecord) -> None:
        self.bot = bot

        self.callbacks: Dict[ShopItemKind, Callable[[Context, ShopItem, Optional[int]], Coroutine[Any, Any, Any]]] = {
            ShopItemKind.Booster: self.apply_xp_booster_item,
            ShopItemKind.Other: self.apply_other_item
        }

    async def apply_xp_booster_item(self, ctx: Context, item: ShopItem, amount: Optional[int]):
        if item.name == 'Rare Candy':
            if amount is None:
                amount = 1

            selected = ctx.pool.user.get_selected()
            if selected.level == 100:
                return await ctx.send('Your selected pokemon is already at the max level.')

            level = selected.level + amount
            if level > 100:
                level = 100

            await selected.edit(level=level, exp=0)

            if amount == 1:
                await ctx.send(f'Successfully bought 1 rare candy.')
            else:
                await ctx.send(f'Successfully bought {amount} rare candies.')

            return await ctx.pool.user.remove_credits(item.price * amount)

    async def apply_other_item(self, ctx: Context, item: ShopItem, amount: Optional[int]):
        if item.name == 'Redeem':
            if amount is None:
                amount = 1

            await ctx.pool.user.add_redeems(amount)
            if amount == 1:
                await ctx.send(f'Successfully bought 1 redeem.')
            else:
                await ctx.send(f'Successfully bought {amount} redeems.')

            return await ctx.pool.user.remove_credits(item.price * amount)

    @commands.command()
    async def shop(self, ctx: Context, page: Optional[int] = None):
        if page is not None:
            items = await self.bot.pool.get_all_items()
            items = find(items, lambda item: item.kind == page)

            embed = discord.Embed(title=f'Shop — {ctx.pool.user.credits} Credits', color=0x36E3DD)
            embed.description = f'Use `{ctx.prefix}buy <item-id>` to buy a shop item.'

            for item in items:
                embed.add_field(
                    name=f'{item.name} (ID: {item.id}) — {item.price} Credits', 
                    value=item.description,
                    inline=False
                )     

            return await ctx.send(embed=embed)

        embed = discord.Embed(title=f'Shop — {ctx.pool.user.credits} Credits', color=0x36E3DD)
        embed.description = f'Use `{ctx.prefix}shop <page>` to view different pages.'

        for i, kind in enumerate(ShopItemKind, start=1):
            embed.add_field(name=f'Page {i}', value=kind.as_string(), inline=False)

        await ctx.send(embed=embed)

    @commands.command()
    async def buy(self, ctx: Context, item_id: int, amount: Optional[int] = None):
        item = await self.bot.pool.get_item(item_id)
        if not item:
            return await ctx.send('That item does not exist.')

        if amount is not None:
            if (item.price * amount) > ctx.pool.user.credits:
                return await ctx.send('You do not have enough credits.')
        else:
            if item.price > ctx.pool.user.credits:
                return await ctx.send('You do not have enough credits.')
        
        callback = self.callbacks.get(item.kind, _noop)
        await callback(ctx, item, amount)

async def setup(bot: Pokecord):
    await bot.add_cog(Shop(bot))


