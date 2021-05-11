import discord
from discord.ext import commands

from bot import Pokecord
from wrapper import Pokemon

class Events(commands.Cog):
    def __init__(self, bot: Pokecord) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandInvokeError):
        error = getattr(error, 'original', error)

        if isinstance(error, commands.CheckFailure):
            return

        if isinstance(error, commands.CommandNotFound):
            return

        raise error

    @commands.Cog.listener()
    async def on_pokemon_spawn(self, pokemon: Pokemon, channel: discord.TextChannel):
        ...

def setup(bot: Pokecord):
    bot.add_cog(Events(bot))