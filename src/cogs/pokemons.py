import itertools
from typing import Optional, List
from discord.ext import commands, menus
import discord

from src.utils import Context
from src.database.user import UserPokemon
from src.bot import Pokecord, PosixFlags

class PokemonFlags(PosixFlags):
    level: Optional[int]

class PokemonsSource(menus.ListPageSource):
    def __init__(self, entries: List[UserPokemon]):
        super().__init__(entries, per_page=20)

    async def format_page(self, menu: menus.MenuPages, entries: List[UserPokemon]):
        offset = menu.current_page * self.per_page
        embed = discord.Embed(title=f'Pokemon. Showing a total of {len(self.entries)} entries.', color=0x00ff00)

        description = []

        for i, entry in enumerate(entries, start=offset):
            ret = f"{i+1}. **{entry.nickname}** | Level: {entry.level} | IVs: {entry.ivs.round()}"
            description.append(ret)

        embed.description = "\n".join(description)
        embed.set_footer(text=f"Page {menu.current_page + 1}/{self.get_max_pages()}. Use the reactions to navigate.")

        return embed

class Pokemons(commands.Cog):
    def __init__(self, bot: Pokecord) -> None:
        self.bot = bot

    @commands.command()
    async def pokemons(self, ctx: Context, *, flags: PokemonFlags):
        user = ctx.pool.user
        entries = list(user.pokemons.values())
        
        if flags.level is not None:
            entries = user.find(level=flags.level)

        source = PokemonsSource(entries)
        pages = menus.MenuPages(source)

        await pages.start(ctx)
    
    @commands.command('info')
    async def _info(self, ctx: Context, *, pokemon: Optional[UserPokemon]):
        if pokemon is None:
            pokemon = ctx.pool.user.pokemons[ctx.pool.user.selected]

        rounded = pokemon.ivs.round()
        types = ', '.join([type.capitalize() for type in pokemon.dex.types if type is not None])

        total = self.bot.levels[str(pokemon.level)]['needed']
        embed = discord.Embed(title=pokemon.nickname.title())

        embed.description = f'**Level**: {pokemon.level} | **EXP**: {pokemon.exp}/{total}\n'
        embed.description += f'**Types**: {types}\n'
        embed.description += f'**Nature**: {pokemon.nature.name}\n\n'

        stats = {
            'HP': (pokemon.stats.health, pokemon.ivs.hp),
            'Attack': (pokemon.stats.attack, pokemon.ivs.atk),
            'Defense': (pokemon.stats.defense, pokemon.ivs.defense),
            'SP-atk': (pokemon.stats.spatk, pokemon.ivs.spatk),
            'SP-def': (pokemon.stats.spdef, pokemon.ivs.spdef),
            'Speed': (pokemon.stats.speed, pokemon.ivs.speed)
        }
        stats = [f'**{k}**: {v} | IV: {i}/31' for k, (v, i) in stats.items()]

        embed.description += '\n'.join(stats)
        embed.description += f'\n**Total**: {rounded}%'

        embed.set_footer(text=f'{pokemon.catch_id}/{len(pokemon.user.entries)} Pokémons')
        embed.set_image(url='attachment://pokemon.png')

        file = discord.File(pokemon.dex.image, filename='pokemon.png')
        await ctx.send(embed=embed, file=file)

    @commands.command()
    async def select(self, ctx: commands.Context, *, pokemon: UserPokemon):
        if pokemon.is_selected():
            return await ctx.send('This pokemon is already selected.')

        await pokemon.select()
        await ctx.send(f'Changed selected pokémon to {pokemon.nickname.title()}.')

    @commands.command()
    async def nickname(self, ctx: Context, pokemon: UserPokemon, nickname: str):
        old = pokemon.nickname
        await pokemon.edit(nickname=nickname)

        await ctx.send(f'Changed nickname of {old} to {nickname}.')

    @commands.command()
    async def starter(self, ctx: commands.Context, *, name: Optional[str]):
        user = await self.bot.pool.get_user(ctx.author.id)
        if user:
            return await ctx.send('You already have a starter.')

        if not name:
            embed = discord.Embed(title='Picking a starter.')

            embed.description = 'In order to start your journey as a Pokémon trainer, you have to select a starter.\n'
            embed.description += 'Please pick a starter from the list below by using `p!starter <name>`'

            for generation, pokemons in enumerate(itertools.tee(self.bot.starters, 3), 1):
                embed.description += f'\n\n**Generation {generation}**\n'
                embed.description += '\n'.join(f'{i+1}. {pokemon}' for i, pokemon in enumerate(pokemons))
            
            embed.set_image(url='https://upload.wikimedia.org/wikipedia/en/b/b1/Hoenn.jpg')
            return await ctx.send(embed=embed)

        if name.capitalize() not in self.bot.starters:
            return await ctx.send('Invalid starter name.')

        dex = self.bot.pokedex.find(lambda entry: entry.default_name.casefold() == name.casefold())[0]
        await self.bot.pool.add_user(ctx.author.id, dex.id)

        await ctx.send(f'Successfully chose {name.title()} as a starter.')
            
async def setup(bot: Pokecord):
    await bot.add_cog(Pokemons(bot))
        