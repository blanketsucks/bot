
from typing import List, Optional
from discord.ext import commands
from discord.ext.menus import ListPageSource, MenuPages
import discord

from src.database import User
from src.utils import Context, PokedexEntry, title
from src.bot import Pokecord

class PokedexSource(ListPageSource):
    entries: List[PokedexEntry]

    def __init__(self, user: User, entries: List[PokedexEntry]):
        self.user = user
        self.uniques = len(user.get_unique_pokemons())

        super().__init__(entries, per_page=20)

    async def format_page(self, menu: MenuPages, entries: List[PokedexEntry]):
        offset = menu.current_page * self.per_page or 1
        embed = discord.Embed(title=f'Your pokédex', color=0x36E3DD)
        embed.description = f'You have caught {self.uniques} out of {len(self.entries)} pokémons.'

        for i, entry in enumerate(entries, start=offset):
            count = await self.user.get_catch_count_for(entry.id)
            if count == 0:
                value = '❌ Not caught yet.'
            else:
                value = f'✅ {count} caught.'

            embed.add_field(name=f'{title(entry.default_name)} #{i}', value=value)

        # embed.set_footer(text=f'Page {menu.current_page + 1}/{self.get_max_pages()}. Use the reactions to navigate.')

        return embed

class Pokedex(commands.Cog):
    def __init__(self, bot: Pokecord) -> None:
        self.bot = bot

    @commands.command(name='pokedex', aliases=['dex', 'pd', 'd'])
    async def _pokedex(self, ctx: Context, *, arg: Optional[str]):
        if arg is None:
            entries = self.bot.pokedex.find(lambda entry: entry.catchable)
            source = PokedexSource(ctx.pool.user, entries)

            menu = MenuPages(source)
            return await menu.start(ctx)

        is_shiny = False
        if arg.startswith('shiny'):
            arg = arg.removeprefix('shiny').strip()
            is_shiny = True

        try:
            entry = await PokedexEntry.convert(ctx, arg)
        except commands.BadArgument:
            matches = self.bot.get_close_matches(arg)
            if matches:
                ret = ', '.join(matches)
                await ctx.send(content=f'Pokémon not found.\nDid you mean {ret}?')
            else:
                await ctx.send(content=f'Pokémon not found.')

            return
    
        stats = {
            'HP': entry.stats.hp,
            'Attack': entry.stats.atk,
            'Defense': entry.stats.defense,
            'Sp. Atk': entry.stats.spatk,
            'Sp. Def': entry.stats.spdef,
            'Speed': entry.stats.speed
        }
        stats = [f'**{k}**: {v}' for k, v in stats.items()]
        types = ', '.join(type.title() for type in entry.types if type is not None)

        names = []
        if entry.names.jp:
            ret = f':flag_jp: {entry.names.jp}'
            if entry.names.jp_r:
                ret += f', {entry.names.jp_r}'
            if entry.names.jp_t:
                ret += f', {entry.names.jp_t}'

            names.append(ret)
        if entry.names.fr:
            names.append(f':flag_fr: {entry.names.fr}')
        if entry.names.de:
            names.append(f':flag_de: {entry.names.de}')

        other = [
            '**Type(s)**: {}'.format(types),
            '**Pokemon ID**: {}'.format(entry.id),
            '**Region**: {}'.format(entry.region.capitalize()),
            '**Height**: {}m'.format(entry.height),
            '**Weight**: {}kg'.format(entry.weight),
            '**Catchable**: {}'.format(entry.catchable),
            '**Enabled**: {}'.format(entry.enabled),
            '**Rarity**: {}'.format(entry.get_rarity_name()),
            '**Is Form**: {}'.format(entry.is_form),
        ]

        embed = discord.Embed(color=0x36E3DD)
        if is_shiny:
            embed.title = f'#{entry.dex} — ✨ {title(entry.default_name)}'
        else:
            embed.title = f'#{entry.dex} — {title(entry.default_name)}'

        embed.description = entry.description if entry.description else 'No description.'
        embed.description += '\n\n'

        embed.description += '\n'.join(names)

        embed.add_field(name='Pokémon Information', value='\n'.join(other))
        embed.add_field(name='Base Stats', value='\n'.join(stats))

        embed.set_image(url='attachment://pokemon.png')

        count = await ctx.pool.user.get_catch_count_for(entry.id)
        if not count:
            embed.set_footer(text='You haven\'t caught this pokémon yet.')
        else:
            embed.set_footer(text=f'You\'ve caught {count} of this pokémon')

        if is_shiny:
            file = discord.File(entry.images.shiny, filename='pokemon.png')
        else:
            file = discord.File(entry.images.default, filename='pokemon.png')

        await ctx.send(embed=embed, file=file)

async def setup(bot: Pokecord):
    await bot.add_cog(Pokedex(bot))
        