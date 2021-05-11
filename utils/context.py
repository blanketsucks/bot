from discord.ext import commands
import discord
import traceback
import typing

from .translator import Translator

if typing.TYPE_CHECKING:
    from bot import Pokecord

class Context(commands.Context):
    bot: 'Pokecord'

    async def format_exception(self, exc: Exception):
        embed = discord.Embed(color=0x2F3136)
        embed.description = f'```py\n{traceback.format_exc()}\n```'

        return await self.send(embed=embed)

    async def confirmation(self, content: str):
        def check(m):
            return m.channel == self.channel and m.author == self.author

        await self.send(content=content)
        message = await self.bot.wait_for('message', check=check)

        if message.content.lower() == 'confirm':
            return True

        if message.content.lower() == 'cancel':
            return False

        return None

    async def get_language(self):
        async with self.bot.pool.acquire() as conn:
            ...
    
    async def translate(self, content: str, *, embed: discord.Embed=None):
        language = await self.get_language()
        translator = Translator(language)

        text = await translator.translate(content)
        message = await self.send(content=text)

        await translator.close()
        return message