import discord
from discord.ext import commands

from bot import Pokecord
from utils import database

class Shop(commands.Cog):
    def __init__(self, bot: Pokecord) -> None:
        self.bot = bot

        self.forms = {
            'mega': 2500,
            'primal': 2500,
            'mega-y': 2500,
            'mega-x': 2500,
            'gigantamax': 5000,
            'ultra-necrozma': 1500,
            'dusk-mane-necrozma': 1500,
            'dawn-wings-necrozma': 1500,
            'white-kyurem': 1500,
            'black-kyurem': 1500,
            'giratina-origin': 1500,
        }

        self.special_forms = {
            'dusk-mane-necrozma': ('necrozma', 'solgaleo'),
            'dawn-wings-necrozma': ('necrozma', 'lunala'),
            'white-kyurem': ('kyurem', 'reshiram'),
            'black-kyurem': ('kyurem', 'zekrom')
        }

        self.can_mega_x = ('charizard', 'mewtwo')
        self.can_mega_y = self.can_mega_x

        self.can_primal = ('kyogre', 'groudon')

    @commands.command(name='balance', aliases=['bal'])
    async def _balance(self, ctx: commands.Context):
        user = await self.bot.pool.get_user(ctx.author.id)
        balance = user.balance

        embed = discord.Embed(title=f"{ctx.author.display_name}'s balance")
        embed.description = f'You currently have: {balance} credits.'

        await ctx.send(embed=embed)

    @commands.group(name='shop', invoke_without_command=True)
    async def shop(self, ctx: commands.Context):
        ...

    @shop.command(name='natures')
    async def _natures(self, ctx: commands.Context):
        embed = discord.Embed(title='Natures')

        embed.description = 'Here are a list of all available natures and their respective stat changes.\n'
        embed.description += 'All of the natures cost `75 credits` each.'

        for key, item in self.bot.natures.items():
            summary = item['summary']
            embed.add_field(name=key, value=summary, inline=False)

        await ctx.send(embed=embed)

    @shop.command(name='forms')
    async def _forms(self, ctx: commands.Context):
        embed = discord.Embed(title='Forms')
        
        embed.description = '**Prices**: \n'
        embed.description += 'Mega/Primal: `2500 credits` | Gigantamax: `5000 credits` | Other: `1500 credits`'

        forms = ' | '.join([form.title() for form in self.forms.keys() if form not in self.special_forms.keys()])
        embed.add_field(name='Available Forms', value=forms)

        def format(k):
            return ', '.join(name.title() for name in k)

        special = '\n'.join([f'**{form.title()}** | Requires: {format(k)}' for form, k in self.special_forms.items()])
        embed.add_field(name='Special Forms', value=special, inline=False)

        await ctx.send(embed=embed)

    @commands.group(name='buy', invoke_without_command=True)
    async def buy(self, ctx: commands.Context):
        ...

    @buy.command(name='nature')
    async def _nature(self, ctx: commands.Context, name: str):
        user = await self.bot.pool.get_user(ctx.author.id)

        if name.capitalize() not in self.bot.natures.keys():
            return await ctx.send('Invalid nature.')

        if user.balance < 75:
            return await ctx.send('You do not have enough money.')

        await user.update_pokemon_nature(name)
        await user.remove_from_balance(75)

        await ctx.send(f'Successfully switched to the {name.capitalize()} nature.')

    @buy.command(name='form')
    async def _form(self, ctx: commands.Context, *, form: str):
        user = await self.bot.pool.get_user(ctx.author.id)
        form = form.lower()

        if form not in self.forms:
            return await ctx.send('Invalid nature.')

        price = self.forms.get(form)

        if user.balance < price:
            return await ctx.send('You do not have enough money')

        if form == 'mega':
            name = user.get_selected()[0]['pokemon']['name']
            if self._check_mega(name) is False:
                return await ctx.send('Invalid pokémon to mega.')

            await self.buy_mega(user)
            return await ctx.send(f'Transformed {name.title()} into Mega {name.title()}.')

        if form == 'mega-x':
            name = user.get_selected()[0]['pokemon']['name']
            if self._check_mega_x(name) is False:
                return await ctx.send('Invalid pokémon to mega.')

            await self.buy_mega(user, x=True)
            return await ctx.send(f'Transformed {name.title()} into Mega {name.title()} X.')

        if form == 'mega-y':
            name = user.get_selected()[0]['pokemon']['name']
            if self._check_mega_x(name) is False:
                return await ctx.send('Invalid pokémon to mega.')

            await self.buy_mega(user, y=True)
            return await ctx.send(f'Transformed {name.title()} into Mega {name.title()} Y.')

        if form == 'primal':
            name = user.get_selected()[0]['pokemon']['name']
            if self._check_primal(name) is False:
                return await ctx.send('Invalid pokémon to mega.')

            await self.buy_mega(user, primal=True)
            return await ctx.send(f'Transformed {name.title()} into Primal {name.title()}.')

        if form == 'gigantamax':
            name = user.get_selected()[0]['pokemon']['name']
            if self._check_giga(name) is False:
                return await ctx.send('Invalid pokémon to gigantamax.')

            await self.buy_giga(user)
            return await ctx.send(f'Transformed {name.title()} into Gigantamax {name.title()}.')

        if form == 'ultra-necrozma':
            name = user.get_selected()[0]['pokemon']['name']
            if self._check_necrozma(name) is False:
                return await ctx.send('Please select necrozma in order to ultra it.')

            await self.buy_necrozma_form(user)
            return await ctx.send(f'Transformed {name.title()} into Ultra {name.title()}.')

        if form == 'dawn-wings-necrozma':
            name = user.get_selected()[0]['pokemon']['name']

            if self._check_necrozma(name) is False:
                return await ctx.send('Please select necrozma in order to transform it into a dawn wings.')

            lunala, _ = user.get_pokemon_by_name('lunala')
            if not lunala:
                return await ctx.send('You need to have a lunala in order to proceed.')

            await self.buy_necrozma_form(user, dawn=True)
            return await ctx.send(f'Transformed {name.title()} into Dawn Wings {name.title()}.')

        if form == 'dusk-mane-necrozma':
            name = user.get_selected()[0]['pokemon']['name']

            if self._check_necrozma(name) is False:
                return await ctx.send('Please select necrozma in order to transform it into a dusk mane.')

            solgaleo, _ = user.get_pokemon_by_name('solgaleo')
            if not solgaleo:
                return await ctx.send('You need to have a solgaleo in order to proceed.')

            await self.buy_necrozma_form(user, dusk=True)
            return await ctx.send(f'Transformed {name.title()} into Dusk Mane {name.title()}.')

        if form == 'black-kyurem':
            name = user.get_selected()[0]['pokemon']['name']

            if self._check_kyurem(name) is False:
                return await ctx.send('Please select kyurem in order to transform it into a black.')

            zekrom, _ = user.get_pokemon_by_name('zerkrom')
            if not zekrom:
                return await ctx.send('You need to have a zekrom in order to proceed.')

            await self.buy_kyurem_form(user, black=True)
            return await ctx.send(f'Transformed {name.title()} into Black {name.title()}.')

        if form == 'white-kyurem':
            name = user.get_selected()[0]['pokemon']['name']

            if self._check_kyurem(name) is False:
                return await ctx.send('Please select kyurem in order to transform it into a black.')

            reshiram, _ = user.get_pokemon_by_name('reshiram')
            if not reshiram:
                return await ctx.send('You need to have a reshiram in order to proceed.')

            await self.buy_kyurem_form(user, white=True)
            return await ctx.send(f'Transformed {name.title()} into White {name.title()}.')


    def _check_mega(self, name: str):
        if name.lower() not in self.bot.megas:
            return False

        return True

    def _check_mega_x(self, name: str):
        if name.lower() not in self.can_mega_x:
            return False

        return True

    def _check_mega_y(self, name: str):
        if name.lower() not in self.can_mega_y:
            return False

        return True

    def _check_primal(self, name: str):
        if name.lower() not in self.can_primal:
            return False

        return True

    def _check_giga(self, name: str):
        if name.lower() not in self.bot.gigas:
            return False

        return True

    def _check_necrozma(self, name: str):
        return name.lower() == 'necrozma'

    def _check_kyurem(self, name: str):
        return name.lower() == 'kyurem'

    async def buy_giga(self, user: database.User):
        entry, _ = user.get_selected()

        id = entry['pokemon']['id']
        level = entry['pokemon']['level']
        ivs = entry['pokemon']['ivs']

        ivs = list(ivs.values())
        ivs.pop(0)

        name = entry['pokemon']['name']

        await user.edit_pokemon('gigantamax ' + name, id, level, ivs)
        await user.remove_from_balance(5000)

    async def buy_mega(self, user: database.User, *, x: bool=False, y: bool=False, primal: bool=False):
        entry, _ = user.get_selected()

        id = entry['pokemon']['id']
        level = entry['pokemon']['level']
        ivs = entry['pokemon']['ivs']

        ivs = list(ivs.values())
        ivs.pop(0)

        name = entry['pokemon']['name']
        original = name

        if x is False and y is False:
            name = 'mega ' + original

        if x:
            name = 'mega ' + original + ' x'

        if y:
            name = 'mega ' + original + ' x'

        if primal:
            name = 'primal ' + original

        await user.edit_pokemon(name, id, level, ivs)
        await user.remove_from_balance(2500)

    async def buy_necrozma_form(self, user: database.User, *, dawn: bool=False, dusk: bool=False):
        entry, _ = user.get_selected()

        id = entry['pokemon']['id']
        level = entry['pokemon']['level']
        ivs = entry['pokemon']['ivs']

        ivs = list(ivs.values())
        ivs.pop(0)

        if dawn:
            old = user.get_pokemon_by_name('lunala')[0]['pokemon']['id']

            await user.remove_pokemon(old)
            user = await user.refetch()

            await user.edit_pokemon('dawn wings necrozma', id, level, ivs)
            return await user.remove_from_balance(1500)

        if dusk:
            old = user.get_pokemon_by_name('solgaleo')[0]['pokemon']['id']

            await user.remove_pokemon(old)
            user = await user.refetch()

            await user.edit_pokemon('dusk mane necrozma', id, level, ivs)
            return await user.remove_from_balance(1500)

        await user.edit_pokemon('ultra necrozma', id, level, ivs)
        return await user.remove_from_balance(1500)

    async def buy_kyurem_form(self, user: database.User, *, black: bool=False, white: bool=False):
        entry, _ = user.get_selected()

        id = entry['pokemon']['id']
        level = entry['pokemon']['level']
        ivs = entry['pokemon']['ivs']

        ivs = list(ivs.values())
        ivs.pop(0)

        if black:
            old = user.get_pokemon_by_name('zekrom')[0]['pokemon']['id']

            await user.remove_pokemon(old)
            user = await user.refetch()

            await user.edit_pokemon('black kyurem', id, level, ivs)
            return await user.remove_from_balance(1500)

        if white:
            old = user.get_pokemon_by_name('reshiram')[0]['pokemon']['id']

            await user.remove_pokemon(old)
            user = await user.refetch()

            await user.edit_pokemon('white kyurem', id, level, ivs)
            return await user.remove_from_balance(1500)


def setup(bot: Pokecord):
    bot.add_cog(Shop(bot))