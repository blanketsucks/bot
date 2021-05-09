import json
from discord.ext import commands
import discord
from typing import Union

from utils import calc
from bot import Pokecord

class Pokedex(commands.Cog):
    def __init__(self, bot: Pokecord) -> None:
        self.bot = bot

    @commands.command(name='pokedex', aliases=['dex'])
    async def _pokedex(self, ctx: commands.Context, *, dex: Union[str, int]):
        pokemon, shiny = await self.bot.fetch_pokemon(dex)
        if not pokemon:
            return await ctx.send(
                content='Pokémon not found.'
            )

        await pokemon.get_stats()
        types = await pokemon.get_types()

        name = self.bot._parse_pokemon(pokemon.name)
        name = ' '.join([part.capitalize() for part in name.split(' ')])

        stats = {
            'HP': pokemon.health,
            'Attack': pokemon.attack,
            'Defense': pokemon.defense,
            'SP-atk': pokemon.spatk,
            'SP-def': pokemon.spdef,
            'Speed': pokemon.speed
        }
        stats = [f'**{k}**: {v.base}' for k, v in stats.items()]
        sprite = pokemon.sprite.front

        if shiny:
            sprite = pokemon.sprite.shiny

        types = ', '.join(type.name.capitalize() for type in types)

        embed = discord.Embed(title=f'#{pokemon.dex} {name}')
        embed.description = f'**Types**: {types}\n\n'

        embed.description += '\n'.join(stats)

        embed.set_image(url=sprite)
        await ctx.send(embed=embed)

    @commands.command(name='moves')
    async def _moves(self, ctx: commands.Context, *, dex: Union[str, int]):
        pokemon, shiny = await self.bot.fetch_pokemon(dex)
        if not pokemon:
            return await ctx.send(
                content='Pokémon not found.'
            )

        name = self.bot._parse_pokemon(pokemon.name)
        name = ' '.join([part.capitalize() for part in name.split(' ')])

        moves = await pokemon.get_moves()
        moves.sort()

        embed = discord.Embed(title=f'Available Moves for: {name}')

        parsed = '\n'.join([f'**{move.name}**: Level {move.learned_at}' for move in moves])
        embed.description = parsed

        await ctx.send(embed=embed)

def setup(bot: Pokecord):
    bot.add_cog(Pokedex(bot))
        