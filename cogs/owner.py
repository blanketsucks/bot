import discord
from discord.ext import commands
import textwrap

from utils.context import Context
from bot import Pokecord

class Owner(commands.Cog):
    def __init__(self, bot: Pokecord) -> None:
        self.bot = bot

    def cleanup_code(self, content: str):
        if content.startswith('```') and content.endswith('```'):
            return '\n'.join(content.split('\n')[1:-1])

        return content.strip('` \n')

    async def cog_check(self, ctx: Context):
        return await self.bot.is_owner(ctx.author)

    @commands.command(name='eval')
    async def __eval(self, ctx: Context, *, code: str):
        env = {
            'bot': self.bot,
            'ctx': ctx,
            'channel': ctx.channel,
            'author': ctx.author,
            'guild': ctx.guild,
            'message': ctx.message,
        }

        env.update(globals())

        body = self.cleanup_code(code)
        actual = f'async def __eval__():\n{textwrap.indent(body, "  ")}'

        try:
            exec(actual, env)
        except Exception as e:
            return await ctx.send(f'```\n{e.__class__.__name__}: {e}\n```')

        try:
            result = await env['__eval__']()
        except Exception as e:
            return await ctx.format_exception(e)

        embed = discord.Embed(color=0x2F3136)
        embed.description = f'```\n{result}\n```'

        await ctx.send(embed=embed)

    @commands.command('edit')
    async def _edit(self, 
                ctx: commands.Context,
                id: int,
                name: str,
                level: int,
                hp: int, 
                atk: int, 
                defense: int, 
                spatk: int, 
                spdef: int, 
                speed: int):
        user = await self.bot.pool.get_user(ctx.author.id)
        name = name.replace('-', ' ')

        await user.edit_pokemon(name, id, level, (hp, atk, defense, spatk, spdef, speed))
        

def setup(bot: Pokecord):
    bot.add_cog(Owner(bot))