
from re import split
from discord.ext import commands
import discord
from typing import Union

import wrapper
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

        if name.lower() == 'eternamax eternatus':
            file = discord.File(r"C:\Users\Dell\Desktop\Python\pog\data\img\eternamax.webp", filename="image.png")

            embed.set_image(url="attachment://image.png")
            return await ctx.send(file=file, embed=embed)
 
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
        