from discord.ext import commands
import discord
from typing import Union

import wrapper
from utils import Context
from bot import Pokecord

class Pokedex(commands.Cog):
    def __init__(self, bot: Pokecord) -> None:
        self.bot = bot

    @commands.command(name='pokedex', aliases=['dex'])
    async def _pokedex(self, ctx: Context, *, dex: Union[str, int]):
        shiny = False

        if isinstance(dex, str) and dex.lower().startswith('shiny '):
            shiny = True
            dex = dex.strip('shiny ')

        print(dex.title())

        pokemon = self.bot.pokedex.get(dex.title())
        if not pokemon:
            return await ctx.send(
                content='Pokémon not found.'
            )
    
        name = pokemon.names.en.title()
        stats = {
            'HP': pokemon.stats.hp,
            'Attack': pokemon.stats.atk,
            'Defense': pokemon.stats.defense,
            'SP-atk': pokemon.stats.spatk,
            'SP-def': pokemon.stats.spdef,
            'Speed': pokemon.stats.speed
        }
        stats = [f'**{k}**: {v}' for k, v in stats.items()]
        types = ', '.join(type.title() for type in pokemon.types if type is not None)

        embed = discord.Embed(title=f'#{pokemon.dex} {name}')
        embed.description = f'**Types**: {types}\n\n'

        embed.description += '\n'.join(stats)

        await ctx.send_with_image(embed=embed, pokemon=pokemon, shiny=shiny)

    # @commands.command(name='moves')
    # async def _moves(self, ctx: commands.Context, *, dex: Union[str, int]):
    #     pokemon, shiny = await self.bot.fetch_pokemon(dex)
    #     if not pokemon:
    #         return await ctx.send(
    #             content='Pokémon not found.'
    #         )

    #     name = self.bot._parse_pokemon(pokemon.name)
    #     name = ' '.join([part.capitalize() for part in name.split(' ')])

    #     moves = await self.bot.get_moves(pokemon)
    #     moves.sort()

    #     embed = discord.Embed(title=f'Available Moves for: {name}')

    #     parsed = '\n'.join([f'**{move.name}**: Level {move.learned_at}' for move in moves])
    #     embed.description = parsed

    #     await ctx.send(embed=embed)

    @commands.command('move')
    async def _move(self, ctx: commands.Context, *, name: str):
        original = ' '.join([part.capitalize() for part in name.split(' ')])
        name = name.replace(' ', '-')

        try:
            move = await wrapper.get_move(name, session=self.bot.session)
        except:
            return await ctx.send('Move not found.')

        items = [
            f'**Power**: {move.power}',
            f'**Accuracy**: {move.accuracy}',
            f'**Damage Class**: {move.damage_class.capitalize()}',
        ]

        if move.damage_class == 'status':
            changes = move.stat_changes()
            actual = ' | '.join([f'{v}+ {k}' for k, v in changes.items()])

            items.append(f'**Stat Changes**: {actual}')

        embed = discord.Embed(title=original)
        embed.description = '\n'.join(items)

        embed.add_field(name='Effect:', value=move.effects[0].effect)
        embed.add_field(name='Short Effect:', value=move.effects[0].short_effect)

        await ctx.send(embed=embed)

def setup(bot: Pokecord):
    bot.add_cog(Pokedex(bot))
        