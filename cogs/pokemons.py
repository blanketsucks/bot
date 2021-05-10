import random
from discord.ext import commands
import discord
from typing import Optional, Union

from utils import calc
from bot import Pokecord

class Pokemons(commands.Cog):
    def __init__(self, bot: Pokecord) -> None:
        self.bot = bot

    @commands.command('pokemons')
    async def _pokemons(self, ctx: commands.Context):
        user = await self.bot.pool.get_user(ctx.author.id)
        entries = user.pokemons

        embed = discord.Embed()
        embed.description = ''

        for entry in entries:
            poke = entry['pokemon']

            level = poke['level']
            id = poke['id']
            name = poke['name']

            rounded, hp, atk, defense, spatk, spdef, speed = self.bot._get_ivs(poke['ivs'])
            pokemon, shiny = await self.bot.fetch_pokemon(name)

            name = self.bot._parse_pokemon(pokemon.name)
            name = ' '.join([part.capitalize() for part in name.split(' ')])

            embed.description += f'**{name}** | Level: {level} | ID: {id} | IV: {rounded}%\n'

        if not embed.description:
            embed.title = 'No pokémons found.'
            embed.description = embed.Empty

        await ctx.send(embed=embed)
    
    @commands.command('info')
    async def _info(self, ctx: commands.Context, id: Optional[Union[int, str]]):
        user = await self.bot.pool.get_user(ctx.author.id)

        if not id:
            entry, entries = user.get_selected()

        else:
            if isinstance(id, int):
                entry, entries = user.get_pokemon_by_id(id)
                if not entry:
                    await ctx.send(f'No Pokémon found with the id of {id}.')
                    return

            if isinstance(id, str):
                if id.lower() == 'latest' or id.lower() == 'l':
                    id = user.current_id
                    entry, entries = user.get_pokemon_by_id(id)

                else:
                    entry, entries = user.get_pokemon_by_name(id)

        pokemon = entry['pokemon']

        id = pokemon['id']
        name = pokemon['name']
        level = pokemon['level']

        rounded, hp, atk, defen, spatk, spdef, spd = self.bot._get_ivs(pokemon['ivs'])
        pokemon, shiny = await self.bot.fetch_pokemon(name)

        await pokemon.get_stats()

        types = await pokemon.get_types()
        types = ', '.join(type.name.capitalize() for type in types)

        name = self.bot._parse_pokemon(pokemon.name)
        name = ' '.join([part.capitalize() for part in name.split(' ')])

        exp = user.get_pokemon_experience(id)

        total = self.bot.levels[str(level)]['needed']
        embed = discord.Embed(title=name)

        embed.description = f'**Level**: {level} | **EXP**: {exp}/{total}\n'
        embed.description += f'**Types**: {types}\n\n'

        file = None

        sprite = pokemon.sprite.front
        if shiny:
            sprite = pokemon.sprite.shiny

        embed.set_image(url=sprite)

        if name.lower() == 'eternamax eternatus':
            file = discord.File(r"C:\Users\Dell\Desktop\Python\pog\data\img\eternamax.webp", filename="image.png")
            embed.set_image(url="attachment://image.png")

        health = calc.calculate_health(pokemon.health.base, hp, level)
        attack = calc.calculate_other(pokemon.attack.base, atk, level)
        defense = calc.calculate_other(pokemon.defense.base, defen, level)
        spattack = calc.calculate_other(pokemon.spatk.base, spatk, level)
        spdefense = calc.calculate_other(pokemon.spdef.base, spdef, level)
        speed = calc.calculate_other(pokemon.speed.base, spd, level)

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

        embed.set_footer(text=f'{id}/{len(entries)} Pokémons')

        await ctx.send(embed=embed, file=file)

    @commands.command(name='select')
    async def _select(self, ctx: commands.Context, id: int):
        user = await self.bot.pool.get_user(ctx.author.id)
        entry, _ = user.get_pokemon_by_id(id)

        if not entry:
            await ctx.send(f'No Pokémon found with the id of {id}.')
            return

        name = entry['pokemon']['name']
        level = entry['pokemon']['level']

        pokemon, _ = await self.bot.fetch_pokemon(name)

        name = self.bot._parse_pokemon(pokemon.name)
        name = ' '.join([part.capitalize() for part in name.split(' ')])

        await user.change_selected(ctx.author.id, id)
        await ctx.send(f'Changed selected pokémon to level {level} {name}.')

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
        if pokemon['pokemon']['level'] == 100:
            return

        await user.add_experience(up)

        exp = user.get_experience()
        level = user.get_level()

        needed = self.bot.levels[str(level)]['needed']

        if exp > needed:
            actual = pokemon['pokemon']['name']
            evolution = self.bot.evolutions[actual.capitalize()]

            name = evolution['evolution']
            evo = evolution['level']

            embed = discord.Embed(title='Level up!!')
            embed.description = f'Your {actual.capitalize()} has leveled up to level {level + 1}!!\n'

            if level >= int(evo):
                await user.update_pokemon(name.lower(), level + 1)
                embed.description += f'{actual.capitalize()} has evolved into {name}.'

                return await message.channel.send(embed=embed)

            await user.update_pokemon(actual, level + 1)
            await message.channel.send(embed=embed)

            
def setup(bot: Pokecord):
    bot.add_cog(Pokemons(bot))
        