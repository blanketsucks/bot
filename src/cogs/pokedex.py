
from typing import List, Optional
from discord.ext import commands
from discord.ext.menus import ListPageSource, MenuPages, views, Menu
import discord

from src.utils import Context, PokedexEntry
from src.bot import Pokecord

class PokedexSource(ListPageSource):
    entries: List[PokedexEntry]

    def __init__(self, entries: List[PokedexEntry]):
        super().__init__(entries, per_page=20)

    async def format_page(self, menu: MenuPages, entries: List[PokedexEntry]):
        offset = menu.current_page * self.per_page
        embed = discord.Embed(title=f'Pokedex. Showing a total of {len(self.entries)} entries.', color=0x36E3DD)

        description = []

        for i, entry in enumerate(entries, start=offset):
            description.append(f'{i+1}. **{entry.default_name}**')

        embed.description = '\n'.join(description)
        embed.set_footer(text=f'Page {menu.current_page + 1}/{self.get_max_pages()}. Use the reactions to navigate.')

        return embed

class Pokedex(commands.Cog):
    def __init__(self, bot: Pokecord) -> None:
        self.bot = bot

    @commands.command(name='pokedex', aliases=['dex', 'pd', 'd'])
    async def _pokedex(self, ctx: Context, *, arg: Optional[str]):
        if arg is None:
            source = PokedexSource(self.bot.pokedex.entries)
            menu = MenuPages(source)

            return await menu.start(ctx)

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
    
        name = entry.default_name
        stats = {
            'HP': entry.stats.hp,
            'Attack': entry.stats.atk,
            'Defense': entry.stats.defense,
            'SP-Attack': entry.stats.spatk,
            'SP-Defense': entry.stats.spdef,
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
            '**Height**: {}'.format(entry.height),
            '**Weight**: {}'.format(entry.weight),
            '**Catchable**: {}'.format(entry.catchable),
            '**Enabled**: {}'.format(entry.enabled),
            '**Legendary**: {}'.format(entry.rarity.legendary),
            '**Mythical**: {}'.format(entry.rarity.mythical),
            '**Ultra Beast**: {}'.format(entry.rarity.ultra_beast),
            '**Is Form**: {}'.format(entry.is_form),
        ]

        embed = discord.Embed(title=f'#{entry.dex} {name}', color=0x36E3DD)
        embed.description = entry.description if entry.description else 'No description.'
        embed.description += '\n\n'

        embed.description += '\n'.join(names) + '\n\n'

        embed.description += '\n'.join(other) + '\n\n'
        embed.description += '\n'.join(stats)

        embed.set_image(url=f'https://github.com/poketwo/data/raw/master/images/{entry.id}.png')
        await ctx.send(embed=embed)

async def setup(bot: Pokecord):
    await bot.add_cog(Pokedex(bot))
        