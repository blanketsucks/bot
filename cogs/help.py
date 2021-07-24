import discord
from discord.ext import commands
from discord.ext.commands import Cog, Command

from typing import Optional, Mapping, List, Any

class HelpCommand(commands.HelpCommand):
    context: commands.Context

    def __init__(self):
        super().__init__(
            command_attrs={"help": "Show help about the bot, a command, or a category."}
        )
    
    async def send_bot_help(self, mapping: Mapping[Optional[Cog], List[Command]]):
        ctx = self.context
        embed = discord.Embed(
            title='Help command.',
            description=f'`{self.clean_prefix}help <category>` for more info on a category.')

        for cog, command in mapping.items():
            if not cog:
                continue

            embed.add_field(
                name=cog.qualified_name or 'No category.',
                value=cog.description or 'No description.'
            )

        await ctx.send(embed=embed)

    async def send_cog_help(self, cog: Cog):
        ctx = self.context
        embed = discord.Embed(
            title=f'{cog.qualified_name} CCommands.'
        )

        for command in cog.walk_commands():
            signature = self.clean_prefix + command.qualified_name + " "
            signature += command.signature

            embed.add_field(
                name=signature,
                value=command.help or "No help found...",
                inline=False,
            )

        await ctx.send(embed=embed)
    
    async def send_command_help(self, command: Command) -> Any:
        embed = discord.Embed()
        embed.title = self.clean_prefix + command.qualified_name

        if command.description:
            embed.description = f"{command.description}\n\n{command.help}"
        else:
            embed.description = command.help or "No help found..."

        embed.add_field(name="Signature", value=self.get_command_signature(command))

        await self.context.send(embed=embed)
