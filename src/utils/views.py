import discord

__all__ = 'ConfirmationView',

class ConfirmationView(discord.ui.View):
    message: discord.Message

    def __init__(self, member: discord.Member, *, timeout: float = 30.0):
        self.value = None
        self.member = member

        super().__init__(timeout=timeout)
    
    async def disable(self) -> None:
        self.confirm.disabled = True
        self.cancel.disabled = True

        await self.message.edit(view=self)

    async def interaction_check(self, interaction: discord.Interaction, /) -> bool:
        if interaction.user == self.member:
            return True
        
        await interaction.response.send_message('This is not your view.', ephemeral=True)
        return False

    @discord.ui.button(label='Confirm', style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.value = True
        
        await self.disable()
        self.stop()

    @discord.ui.button(label='Cancel', style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.value = False

        await self.disable()
        self.stop()
