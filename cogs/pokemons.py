import random
from discord.ext import commands, menus
import discord
from typing import Optional, Union

from utils import calc, Context
from utils.menus import PokemonsSource
from bot import Pokecord

class Pokemons(commands.Cog):
    def __init__(self, bot: Pokecord) -> None:
        self.bot = bot

    @commands.command('pokemons')
    async def _pokemons(self, ctx: Context):
        user = await self.bot.pool.get_user(ctx.author.id)
        entries = user.pokemons

        source = PokemonsSource(entries, self.bot)
        pages = menus.MenuPages(source)

        await pages.start(ctx)
    
    @commands.command('info')
    async def _info(self, ctx: Context, id: Optional[Union[int, str]]):
        pokemon, pokemons = await self.bot.parse_pokemon_argument(ctx, id)

        id = pokemon.id
        name = pokemon.name
        level = pokemon.level
        nature = pokemon.nature

        rounded = pokemon.ivs.rounded
        hp = pokemon.ivs.health
        atk = pokemon.ivs.attack
        defen = pokemon.ivs.defense
        spatk = pokemon.ivs.spattack
        spdef = pokemon.ivs.spdefense
        spd = pokemon.ivs.speed

        entry = self.bot.pokedex.get(name.title())

        types = ', '.join(type.capitalize() for type in entry.types if type is not None)
        exp = pokemon.user.get_pokemon_experience(id)

        total = self.bot.levels[str(level)]['needed']
        embed = discord.Embed(title=name.title())

        embed.description = f'**Level**: {level} | **EXP**: {exp}/{total}\n'
        embed.description += f'**Types**: {types}\n'
        embed.description += f'**Nature**: {nature.name}\n\n'

        health = calc.calculate_health(entry.stats.hp, hp, level)
        attack = calc.calculate_other(entry.stats.atk, atk, level, nature.attack)
        defense = calc.calculate_other(entry.stats.defense, defen, level, nature.defense)
        spattack = calc.calculate_other(entry.stats.spatk, spatk, level, nature.spattack)
        spdefense = calc.calculate_other(entry.stats.spdef, spdef, level, nature.spdefense)
        speed = calc.calculate_other(entry.stats.speed, spd, level, nature.speed)

        stats = {
            'HP': (health, hp),
            'Attack': (attack, atk),
            'Defense': (defense, defen),
            'SP-atk': (spattack, spatk),
            'SP-def': (spdefense, spdef),
            'Speed': (speed, spd)
        }
        stats = [f'**{k}**: {v} | IV: {i}/31' for k, (v, i) in stats.items()]

        embed.description += '\n'.join(stats)
        embed.description += f'\n**Total**: {rounded}%'

        embed.set_footer(text=f'{id}/{len(pokemons)} Pokémons')
        await ctx.send_with_image(embed=embed, pokemon=entry)

    @commands.command(name='select')
    async def _select(self, ctx: commands.Context, *, id: Union[int, str]):
        entry, _ = await self.bot.parse_pokemon_argument(ctx, id)

        if not entry:
            await ctx.send(f'No Pokémon found with the id of {id}.')
            return

        name = entry.name
        level = entry.level

        await entry.user.change_selected(entry.id)
        await ctx.send(f'Changed selected pokémon to level {level} {name.title()}.')

    @commands.command(name='release')
    async def _release(self, ctx: Context, ids: commands.Greedy[Union[int, str]]):
        user = await self.bot.pool.get_user(ctx.author.id)

        if len(user.pokemons) == 1:
            return await ctx.send('You can not release all your pokémons.')

        result = await ctx.confirmation(
            f'Are you sure you want to release {len(ids)} pokémons? Type `confirm` to proceed or `cancel` to cancel this operation.'
        )

        if result is None:
            return await ctx.send('Invalid choice. Cancelling the operation.')

        if result is False:
            return await ctx.send('Cancelling the operation.')

        for id in ids:
            await user.remove_pokemon(id)

        await ctx.send(f'Successfully released {len(ids)} pokémons.')

    def __sort(self, moves, level):
        actual = []

        for move in moves:
            if move.learned_at > level:
                continue
            
            actual.append(move)
        return actual

    def __names(self, moves):
        m = []

        for move in moves:
            m.append(move.name)

        return m

    async def check_moves(self, entry, move: str):
        pokemon, _ = await self.bot.fetch_pokemon(entry.name)
        moves = await self.bot.get_moves(pokemon)

        moves = self.__sort(moves, entry.level)
        moves = self.__names(moves)

        return move in moves

    @commands.command(name='moves')
    async def _moves(self, ctx: Context):
        user = await self.bot.pool.get_user(ctx.author.id)
        entry, entries = user.get_selected()

        name = entry.name
        pokemon = self.bot.pokedex.get(name)

        moves = await self.bot.get_moves(pokemon.slug)
        m = user.get_pokemon_moves(name)

        moves = self.__sort(moves, entry.level)
        moves.sort()

        embed = discord.Embed(title=f"{name.title()}'s moves")

        embed.description = '\n'.join([f'{k}: {"None" if not v else v.title()}' for k, v in m.items()])
        embed.add_field(name='Available moves: ', value=' | '.join([move.name.replace('-', ' ').title() for move in moves]))

        await ctx.send(embed=embed)

    @commands.command(name='learn')
    async def _learn(self, ctx: commands.Context, id: str, *, move: str):
        user = await self.bot.pool.get_user(ctx.author.id)
        entry, _ = user.get_selected()

        check = await self.check_moves(entry, move)
        if not check:
            return await ctx.send('Move unavailable.')

        await user.update_pokemon_move(id, move)

    @commands.command(name='starter')
    async def _starter(self, ctx: commands.Context, *, name: Optional[str]):
        if not name:
            embed = discord.Embed(title='Picking a starter.')

            embed.description = 'In order to start your journey as a Pokémon trainer, you have to select a starter.\n'
            embed.description += 'Please pick a starter from the list below by using `p!starter <name>`'

            for generation, pokemons in self.bot.starters.items():
                gen = ' '.join(part.capitalize() for part in generation.split('-'))

                embed.add_field(name=gen, value=', '.join([pokemon.capitalize() for pokemon in pokemons]), inline=False)
            
            embed.set_image(url='https://upload.wikimedia.org/wikipedia/en/b/b1/Hoenn.jpg')
            return await ctx.send(embed=embed)

        already = await self.bot.pool.add_user(ctx.author.id, name)
        if already:
            return await ctx.send('You can not select a starter twice.')

        await ctx.send(f'Successfully chose {name.lower()} as a starter.')

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        up = random.randint(1, 150)

        user = await self.bot.pool.get_user(message.author.id)
        if not user:
            return

        pokemon, _ = user.get_selected()
        if pokemon.level == 100:
            return

        await user.add_experience(up)

        exp = user.get_experience()
        level = user.get_level()

        needed = self.bot.levels[str(level)]['needed']

        if exp > needed:
            actual = pokemon.name
            evolution = self.bot.pokedex.get(actual).evolutions.to

            name = evolution.names.en
            
            embed = discord.Embed(title='Level up!!')
            embed.description = f'Your {actual.capitalize()} has leveled up to level {level + 1}!!\n'

            if level >= int(evolution.level):
                await user.update_pokemon(name.lower(), level + 1)
                embed.description += f'{actual.capitalize()} has evolved into {name}.'

                return await message.channel.send(embed=embed)

            await user.update_pokemon(actual, level + 1)
            await message.channel.send(embed=embed)

            
def setup(bot: Pokecord):
    bot.add_cog(Pokemons(bot))
        