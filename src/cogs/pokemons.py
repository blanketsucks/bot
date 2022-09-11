from typing import Iterable, Optional, List
from discord.ext import commands
import discord

from src.utils import Context, chunk, find, ConfirmationView
from src.utils import menus, flags
from src.database.user import UserPokemon, User
from src.bot import Pokecord

class PokemonFlags(flags.FlagParser):
    level: Optional[int]
    name: Optional[str] = flags.flag(aliases=['n'])
    nickname: Optional[str] = flags.flag(aliases=['nick'])
    sort: Optional[str] = flags.flag(choices=['iv', 'level'])
    order: Optional[str] = flags.flag(choices=['a', 'ascending', 'd', 'descending'])
    legendary: bool = flags.flag(aliases=['leg'])
    ultra_beast: bool = flags.flag(name='ultra-beast', aliases=['ub'])
    shiny: bool = flags.flag(aliases=['sh'])
    favourite: bool = flags.flag(aliases=['fav'])

class PokemonsSource(menus.ListPageSource[UserPokemon]):
    def __init__(self, user: User, entries: List[UserPokemon]):
        self.user = user
        super().__init__(entries, per_page=20)

    async def format_page(self, menu: menus.MenuPages, entries: List[UserPokemon]):
        embed = discord.Embed(color=0x36E3DD)

        description = []
        for entry in entries:
            ret = f'{entry.catch_id}. '
            if entry.is_shiny():
                ret += '✨ '

            if entry.has_nickname():
                ret += f'**{entry.dex.default_name} "{entry.nickname}"** '
            else:
                ret += f'**{entry.dex.default_name}** '

            if entry.is_favourite():
                ret += ' ❤️ | '
            else:
                ret += '| '

            ret += f'Level: {entry.level}'
            if self.user.has_detailed_pokemon_view():
                ret +=  f' | IV: {entry.ivs.round()}%'

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

class Pokemons(commands.Cog):
    def __init__(self, bot: Pokecord) -> None:
        self.bot = bot

    @commands.command(aliases=['p'])
    async def pokemons(self, ctx: Context, *, flags: PokemonFlags = PokemonFlags.default()):
        user = ctx.pool.user
        entries = list(user.pokemons.values())
        
        if flags.level is not None:
            entries = find(entries, lambda entry: entry.level == flags.level)
        if flags.name is not None:
            name = flags.name
            entries = find(entries, lambda entry: entry.dex.default_name.casefold() == name.casefold())
        if flags.nickname is not None:
            entries = find(entries, lambda entry: entry.nickname == flags.nickname)
        if flags.shiny:
            entries = find(entries, lambda entry: entry.is_shiny())
        if flags.legendary:
            entries = find(entries, lambda entry: entry.dex.rarity.legendary)
        if flags.ultra_beast:
            entries = find(entries, lambda entry: entry.dex.rarity.ultra_beast)
        if flags.favourite:
            entries = find(entries, lambda entry: entry.is_favourite())

        if flags.sort is not None:
            if flags.sort == 'iv':
                entries.sort(key=lambda pokemon: pokemon.ivs.round(), reverse=True)
            elif flags.sort == 'level':
                entries.sort(key=lambda pokemon: pokemon.level, reverse=True)

        if flags.order is not None:
            if flags.order in ('d', 'descending'):
                entries.reverse()

        if not entries:
            return await ctx.send('No results found.')

        source = PokemonsSource(ctx.pool.user, entries)
        pages = menus.MenuPages(source)

        await pages.start(ctx)
    
    @commands.command(aliases=['i'])
    async def info(self, ctx: Context, *, pokemon: Optional[UserPokemon] = None):
        if pokemon is None:
            pokemon = ctx.pool.user.pokemons.get(ctx.pool.user.selected)
            if not pokemon:
                return await ctx.send('Please select a pokémon.')

        embed, file = pokemon.build_discord_embed_for(ctx.pool.user)
        await ctx.send(embed=embed, file=file)

    @commands.command(aliases=['bal'])
    async def balance(self, ctx: Context):
        await ctx.send(f'Your current balance is {ctx.pool.user.credits}')

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

        view = ConfirmationView(ctx.author) # type: ignore
        view.message = await ctx.send(
            'Are you sure you want to release those pokémons? Click on `Confirm` to release them.', view=view
        )

        await view.wait()
        await view.message.delete()

        if not view.value:
            return await ctx.send('Aborted.')

        for pokemon in pokemons:
            await pokemon.release()

        await ctx.send(f'Successfully released {len(pokemons)} pokémons')
        await ctx.pool.user.reindex()

    @commands.command(aliases=['nick'])
    async def nickname(
        self, ctx: Context, pokemons: commands.Greedy[UserPokemon], nickname: Optional[str] = None, # type: ignore
    ):
        pokemons: Iterable[UserPokemon]
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

    @commands.command(aliases=['fav'])
    async def favourite(self, ctx: Context, *pokemons: UserPokemon):
        if not pokemons:
            pokemons = (ctx.pool.user.get_selected(),)

        for pokemon in pokemons:
            if pokemon.is_favourite():
                continue
            
            await pokemon.set_favourite(True)

        await ctx.send(f'Successfully favourited {len(pokemons)} pokémons')

    @commands.command(aliases=['unfav'])
    async def unfavourite(self, ctx: Context, *pokemons: UserPokemon):
        if not pokemons:
            pokemons = (ctx.pool.user.get_selected(),)

        for pokemon in pokemons:
            if not pokemon.is_favourite():
                continue
            
            await pokemon.set_favourite(False)

        await ctx.send(f'Successfully unfavourited {len(pokemons)} pokémons')

    @commands.command()
    async def reindex(self, ctx: Context):
        await ctx.pool.user.reindex()
        await ctx.send('Successfully reindexed all of your pokémons.')

    @commands.command()
    async def details(self, ctx: Context):
        if ctx.pool.user.has_detailed_pokemon_view():
            await ctx.pool.user.set_detailed_view(False)
            await ctx.send('Disabled detailed pokémon information.')
        else:
            await ctx.pool.user.set_detailed_view(True)
            await ctx.send('Enabled detailed pokémon information.')

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
        