import pathlib
from typing import Iterable, Optional, List
from discord.ext import commands, menus
import discord

from src.utils import Context, chunk, find, title
from src.database.user import UserPokemon
from src.bot import Pokecord, PosixFlags

class PokemonFlags(PosixFlags):
    level: Optional[int]
    name: Optional[str] = commands.flag(name='name', aliases=['n'])
    nickname: Optional[str] = commands.flag(name='nickname', aliases=['nick'])

class PokemonsSource(menus.ListPageSource):
    def __init__(self, entries: List[UserPokemon]):
        super().__init__(entries, per_page=20)

    async def format_page(self, menu: menus.MenuPages, entries: List[UserPokemon]):
        offset = menu.current_page * self.per_page
        embed = discord.Embed(color=0x36E3DD)

        description = []
        for i, entry in enumerate(entries, start=offset):
            ret = f'{i+1}. '
            if entry.shiny:
                ret += '✨ '

            if entry.has_nickname():
                ret += f'**{title(entry.dex.default_name)} "{entry.nickname}"** | Level: {entry.level} | IV: {entry.ivs.round()}%'
            else:
                ret += f'**{title(entry.dex.default_name)}** | Level: {entry.level} | IV: {entry.ivs.round()}%'

            
            description.append(ret)

        embed.description = '\n'.join(description)
        embed.set_footer(text=f'Page {menu.current_page + 1}/{self.get_max_pages()}. Use the reactions to navigate.')

        return embed

class Pokemons(commands.Cog):
    def __init__(self, bot: Pokecord) -> None:
        self.bot = bot

    @commands.command(aliases=['p'])
    async def pokemons(self, ctx: Context, *, flags: PokemonFlags):
        user = ctx.pool.user
        entries = list(user.pokemons.values())
        
        if flags.level is not None:
            entries = find(entries, lambda poke: poke.level == flags.level)
        if flags.name is not None:
            name = flags.name
            entries = find(entries, lambda poke: poke.dex.default_name.casefold() == name.casefold())
        if flags.nickname is not None:
            entries = find(entries, lambda poke: poke.nickname == flags.nickname)

        if not entries:
            return await ctx.send('No results found.')

        source = PokemonsSource(entries)
        pages = menus.MenuPages(source)

        await pages.start(ctx)
    
    @commands.command(aliases=['i'])
    async def info(self, ctx: Context, *, pokemon: Optional[UserPokemon] = None):
        if pokemon is None:
            pokemon = ctx.pool.user.pokemons[ctx.pool.user.selected]

        rounded = pokemon.ivs.round()
        total = self.bot.get_needed_exp(pokemon.level)

        _title = ''
        if pokemon.shiny:
            _title += '✨ '
        
        if pokemon.has_nickname():
            _title += f'Level {pokemon.level} {title(pokemon.dex.default_name)} "{pokemon.nickname}"'
        else:
            _title += f'Level {pokemon.level} {title(pokemon.dex.default_name)}'

        embed = discord.Embed(title=_title, color=0x36E3DD)

        embed.description = f'**Level**: {pokemon.level}'
        if pokemon.level != 100:
            embed.description += f' | **EXP**: {pokemon.exp}/{total}\n'
        else:
            embed.description += '\n'

        embed.description += f'**Nature**: {pokemon.nature.name}\n\n'

        stats = {
            'HP': (pokemon.stats.health, pokemon.ivs.hp),
            'Attack': (pokemon.stats.attack, pokemon.ivs.atk),
            'Defense': (pokemon.stats.defense, pokemon.ivs.defense),
            'Sp. Atk': (pokemon.stats.spatk, pokemon.ivs.spatk),
            'Sp. Def': (pokemon.stats.spdef, pokemon.ivs.spdef),
            'Speed': (pokemon.stats.speed, pokemon.ivs.speed)
        }
        stats = [f'**{k}**: {v} | IV: {i}/31' for k, (v, i) in stats.items()]

        embed.description += '\n'.join(stats)
        embed.description += f'\n**Total IV**: {rounded}%'

        embed.set_footer(text=f'Displaying pokémon {pokemon.catch_id}.')
        embed.set_image(url='attachment://pokemon.png')

        image: pathlib.Path[str]
        if pokemon.shiny:
            image = pokemon.dex.images.shiny
        else:
            image = pokemon.dex.images.default

        file = discord.File(image, filename='pokemon.png')
        await ctx.send(embed=embed, file=file)

    @commands.command(aliases=['bal'])
    async def balance(self, ctx: Context):
        await ctx.send(f'Your current balance is {ctx.pool.user.balance.credits}')

    @commands.command()
    async def select(self, ctx: Context, *, pokemon: UserPokemon):
        if pokemon.is_selected():
            return await ctx.send('This pokémon is already selected.')

        await pokemon.select()
        await ctx.send(f'Changed selected pokémon to {pokemon.nickname.title()}.')

    @commands.command()
    async def release(self, ctx: Context, *pokemons: UserPokemon):
        if not pokemons:
            pokemons = (ctx.pool.user.get_selected(),)

        for pokemon in pokemons:
            await pokemon.release()

        await ctx.send(f'Successfully released {len(pokemons)} pokémons')
        await ctx.pool.user.reindex()

    @commands.command(aliases=['nick'])
    async def nickname(
        self, ctx: Context, pokemons: commands.Greedy[UserPokemon] = None, nickname: Optional[str] = None # type: ignore
    ):
        pokemons: Iterable[UserPokemon] # avoids a type ignore in the line below
        if not pokemons:
            pokemons = [ctx.pool.user.get_selected()]
    
        for pokemon in pokemons:
            if not nickname:
                await pokemon.edit(nickname=pokemon.dex.default_name)
            else:
                await pokemon.edit(nickname=nickname)

        if not nickname:
            await ctx.send(f'Reset the nicknames of {len(pokemons)} Pokémons.')
        else:
            await ctx.send(f'Changed the nickname of {len(pokemons)} Pokémons to {nickname}.')

    @commands.command()
    async def starter(self, ctx: Context, *, name: Optional[str]):
        user = await self.bot.pool.get_user(ctx.author.id)
        if user:
            return await ctx.send('You already have a starter.')

        if not name:
            embed = discord.Embed(title='Picking a starter.', color=0x36E3DD)

            embed.description = 'In order to start your journey as a Pokémon trainer, you have to select a starter.\n'
            embed.description += 'Please pick a starter from the list below by using `p!starter <name>`'

            for generation, pokemons in enumerate(chunk(3, self.bot.starters), 1):
                embed.description += f'\n\n**Generation {generation}**\n'
                embed.description += ' | '.join(pokemons)
            
            embed.set_image(url='https://upload.wikimedia.org/wikipedia/en/b/b1/Hoenn.jpg')
            embed.set_footer(text='NOTE: You can only choose a single starter.')

            return await ctx.send(embed=embed)

        if name.capitalize() not in self.bot.starters:
            return await ctx.send('Invalid starter name.')

        dex = self.bot.pokedex.find(lambda entry: entry.default_name.casefold() == name.casefold())[0]
        await self.bot.pool.add_user(ctx.author.id, dex.id)

        await ctx.send(f'Successfully chose {name.title()} as a starter.')
            
async def setup(bot: Pokecord):
    await bot.add_cog(Pokemons(bot))
        