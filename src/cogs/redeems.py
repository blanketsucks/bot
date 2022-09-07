import discord
from discord.ext import commands

from .spawns import Spawns
from src.bot import Pokecord
from src.utils import Context, PokedexEntry, title, chance

class Redeems(commands.Cog):
    def __init__(self, bot: Pokecord) -> None:
        self.bot = bot

    @commands.command()
    async def redeems(self, ctx: Context) -> None:
        embed = discord.Embed(title=f'Your redeems: {ctx.pool.user.redeems}', color=0x36E3DD)

        embed.description = 'Redeems can be used to receive any pokémon of your choice, or alternatively credits. '
        embed.description += 'Currently the only way to get redeems is buying them from the shop.'

        embed.add_field(
            name=f'{ctx.prefix}redeem <pokémon>', 
            value='This will give you a pokémon of your choice. The pokémon must be a valid catchable pokémon.',
            inline=False
        )

        embed.add_field(
            name=f'{ctx.prefix}redeem spawn <pokémon>',
            value='This will spawn a pokémon of your choice. The pokémon must be a valid catchable pokémon.',
            inline=False
        )

        embed.add_field(
            name=f'{ctx.prefix}redeem credits',
            value=f'This will give you {Pokecord.REDEEM_CREDIT_AMOUNT} credits.',
            inline=False
        )

        await ctx.send(embed=embed)
        
    @commands.group(invoke_without_command=True)
    async def redeem(self, ctx: Context, *, pokemon: PokedexEntry):
        if ctx.pool.user.redeems < 1:
            return await ctx.send('You do not have enough redeems.')

        if not pokemon.catchable:
            return await ctx.send('Sorry, you cannot redeem this pokemon.')

        await ctx.pool.user.add_pokemon(pokemon_id=pokemon.id)
        await ctx.send(f'Successfully redeemed {title(pokemon.default_name)}')

        await ctx.pool.user.remove_redeem()

    @redeem.command()
    async def spawn(self, ctx: Context, *, pokemon: PokedexEntry):
        if ctx.pool.user.redeems < 1:
            return await ctx.send('You do not have enough redeems.')

        if not pokemon.catchable:
            return await ctx.send('Sorry, you cannot redeem this pokemon.')

        spawns: Spawns = self.bot.get_cog('Spawns') # type: ignore

        embed = discord.Embed(title='Use p!catch <pokémon name> to catch the following pokémon.', color=0x36E3DD)
        embed.set_image(url='attachment://pokemon.png')

        file = discord.File(pokemon.images.default, filename='pokemon.png')
        await ctx.send(embed=embed, file=file)

        await spawns.wait(ctx.channel.id, pokemon, chance(8192))
        await ctx.pool.user.remove_redeem()

    @redeem.command()
    async def credits(self, ctx: Context):
        if ctx.pool.user.redeems < 1:
            return await ctx.send('You do not have enough redeems.')

        await ctx.pool.user.add_credits(Pokecord.REDEEM_CREDIT_AMOUNT)
        await ctx.pool.user.remove_redeem()

async def setup(bot: Pokecord):
    await bot.add_cog(Redeems(bot))