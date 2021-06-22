from discord.ext import commands
from .context import Context

class PokemonConverter(commands.Converter): ...

class PokemonIDConverter(commands.Converter):
    async def convert(self, ctx: Context, argument: str):
        converter = PokemonConverter()
        pokemon = await converter.convert(ctx, argument)

        return pokemon.id