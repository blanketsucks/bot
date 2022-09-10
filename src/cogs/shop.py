from typing import Any, Callable, Coroutine, Dict, Optional

import discord
from discord.ext import commands

from src.bot import Pokecord
from src.utils import Context
from src.database.items import ShopItemKind, ShopItem

async def _noop(*args: Any): ...

KYUREM = 646
ZEKROM = 644
RESHIRAM = 643

BLACK_KYUREM = 10022
WHITE_KYUREM = 10023

class Shop(commands.Cog):
    def __init__(self, bot: Pokecord) -> None:
        self.bot = bot

        self.callbacks: Dict[ShopItemKind, Callable[[Context, ShopItem, Optional[int]], Coroutine[Any, Any, Any]]] = {
            ShopItemKind.Booster: self.apply_xp_booster_item,
            ShopItemKind.NatureMints: self.apply_nature_mint,
            ShopItemKind.MegaEvolutionsAndForms: self.apply_form_evolution,
            ShopItemKind.Other: self.apply_other_item
        }

    async def exchange_two_pokemons_for(self, ctx: Context, dex1: int, dex2: int, result: int):
        selected = ctx.pool.user.get_selected()

        name1 = self.bot.pokedex.get_pokemon(dex1).default_name # type: ignore
        name2 = self.bot.pokedex.get_pokemon(dex2).default_name # type: ignore

        if selected.dex.id not in (dex1, dex2):
            return await ctx.send(f'You need to have either {name1} or {name2} selected.')

        search = dex1 if selected.dex.id == dex2 else dex2
        pokemons = ctx.pool.user.get_pokemons(search)
        if not pokemons:
            return await ctx.send(f'You need to have both {name1} and {name2}.')

        pokemon = pokemons.pop()
        await pokemon.release()

        await selected.edit(dex_id=result)
        name = self.bot.pokedex.get_pokemon(result).default_name # type: ignore

        await ctx.send(f'Successfully exchanged {name1} and {name2} for {name}.')

    async def apply_xp_booster_item(self, ctx: Context, item: ShopItem, amount: Optional[int]):
        if item.id == 2: # Rare candy
            if amount is None:
                amount = 1

            selected = ctx.pool.user.get_selected()
            if selected.level == 100:
                return await ctx.send('Your selected pokémon is already at the max level.')

            level = selected.level + amount
            if level > 100:
                level = 100

            await selected.edit(level=level, exp=0)

            if amount == 1:
                await ctx.send(f'Successfully bought 1 rare candy.')
            else:
                await ctx.send(f'Successfully bought {amount} rare candies.')

            return await ctx.pool.user.remove_credits(item.price * amount)

    async def apply_nature_mint(self, ctx: Context, item: ShopItem, amount: Optional[int]):
        if amount is not None:
            return await ctx.send('Nature mints do not support multiple amounts.')

        name = item.name.removesuffix('Mint').strip()
        selected = ctx.pool.user.get_selected()

        await selected.edit(nature=name)
        await ctx.send(f'Successfully changed your selected pokémon\'s nature to {name}')

        await ctx.pool.user.remove_credits(item.price)

    async def apply_form_evolution(self, ctx: Context, item: ShopItem, amount: Optional[int]):
        if amount is not None:
            return await ctx.send('Mega evolutions & forms do not support multiple amounts.')

        if item.id == 28: # Normal mega evolution
            selected = ctx.pool.user.get_selected()
            form = selected.dex.evolutions.mega.normal

            if not form:
                return await ctx.send('Your selected pokémon does not have a mega form.')

            await selected.edit(dex_id=form)
        elif item.id == 29: # X mega evolution
            selected = ctx.pool.user.get_selected()
            form = selected.dex.evolutions.mega.x

            if not form:
                return await ctx.send('Your selected pokémon does not have an X mega form.')

            await selected.edit(dex_id=form)
        elif item.id == 30: # Y mega evolution
            selected = ctx.pool.user.get_selected()
            form = selected.dex.evolutions.mega.y

            if not form:
                return await ctx.send('Your selected pokémon does not have an Y mega form.')

            await selected.edit(dex_id=form)
        elif item.id == 31: # Black kyurem
            await self.exchange_two_pokemons_for(
                ctx=ctx,
                dex1=KYUREM,
                dex2=ZEKROM,
                result=BLACK_KYUREM
            )
        elif item.id == 32: # White kyurem
            await self.exchange_two_pokemons_for(
                ctx=ctx,
                dex1=KYUREM,
                dex2=RESHIRAM,
                result=WHITE_KYUREM
            )
            
        await ctx.pool.user.remove_credits(item.price)

    async def apply_other_item(self, ctx: Context, item: ShopItem, amount: Optional[int]):
        if item.id == 1: # Redeem
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
            if page > len(ShopItemKind):
                return await ctx.send('Page not found.')

            items = await self.bot.pool.get_all_items(kind=ShopItemKind(page))

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


