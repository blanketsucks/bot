import asyncio
from typing import Any, Dict, List, Mapping
import discord
from discord.ext import commands

from bot import Pokecord
import wrapper
from utils import database, calc, Context

import functools

class Duels(commands.Cog):
    def __init__(self, bot: Pokecord) -> None:
        self.bot = bot

        self.duels: Dict[int, List[int]] = {}

    @commands.command(name='duel', aliases=['battle'])
    async def _duel(self, ctx: Context, member: discord.Member):
        enemy = await self.bot.pool.get_user(member.id)
        user = await self.bot.pool.get_user(ctx.author.id)

        if not enemy:
            return await ctx.send(f'{member.mention} does not have a starter pokémon.')

        duels = self.duels.get(ctx.author.id)
        if isinstance(duels, list):
            if len(duels) == 1:
                return await ctx.send(f'You are already inside a duel. Please finish the current one to start a new one.')

        duels = self.duels.get(member.id)
        if isinstance(duels, list):
            if len(duels) == 1:
                return await ctx.send(f'{member.display_name} already inside a duel.')

        confirmation = await ctx.confirmation(
            content=f'{member.mention}, {ctx.author.display_name} has challenged you to a duel. Type `confirm` to accept or `cancel` to deny.',
            member=member
        )

        if confirmation is None:
            return await ctx.send('Invalid choice, cancelling the operation.')

        if confirmation is False:
            return await ctx.send('Cancelling the duel.')

        self.duels[ctx.author.id] = [member.id]
        self.duels[member.id] = [ctx.author.id]

        duel = Duel(ctx.author, member, self.bot)
        await duel.start(ctx)

class Duel:
    def __init__(self, user: discord.Member, enemy: discord.Member, bot: Pokecord) -> None:
        self.bot = bot
        self.user = user
        self.enemy = enemy

        self.cancelled = False

    async def start(self, ctx: commands.Context):
        message = await ctx.send('Starting the duel...')

        self._user = await self.bot.pool.get_user(self.user.id)
        self._enemy = await self.bot.pool.get_user(self.enemy.id)

        self.ctx = ctx

        self.user_health = user_total = await self.get_user_starting_health(self._user)
        self.enemy_health = enemy_total =await self.get_enemy_starting_health(self._enemy)

        self._user_atk, self._user_spatk = self.get_attack_stats(self._user_selected, self._user_pokemon)
        self._user_def, self._user_spdef = self.get_defense_stats(self._user_selected, self._user_pokemon)

        self._enemy_atk, self._enemy_spatk = self.get_attack_stats(self._enemy_selected, self._enemy_pokemon)
        self._enemy_def, self._enemy_spdef = self.get_defense_stats(self._enemy_selected, self._enemy_pokemon)

        faster = self.get_faster_pokemon()

        _user = self._user_selected['pokemon']['name'].title()
        _enemy = self._enemy_selected['pokemon']['name'].title()

        embed = discord.Embed(title='Duel')

        embed.description = f'{_user}    VS    {_enemy}\n'
        embed.description += f'{self.user_health}/{user_total}        {self.enemy_health}/{enemy_total}'

        await message.edit(embed=embed, content=None)

        while not self._loop_check():
            if faster:
                dmg1 = await self.user_turn()
                dmg2 = await self.enemy_turn()
            else:
                dmg2 = await self.enemy_turn()
                dmg1 = await self.user_turn()

            self.user_health -= dmg2
            self.enemy_health -= dmg1

            embed = discord.Embed(title=f'{self.enemy.display_name} VS {self.user.display_name}')

            embed.description = f'{_user} VS {_enemy}\n'
            embed.description += f'{self.user_health}/{user_total} {self.enemy_health}/{enemy_total}'

            await ctx.send(embed=embed)

            if self.user_health < 0:
                await ctx.send('He won')
                break

            if self.enemy_health < 0:
                await ctx.send('You won')
                break

            if self.cancelled:
                break

        await ctx.send('defeated')

    def _loop_check(self):
        conditions = [
            self.cancelled is not False,
            self.user_health < 0,
            self.enemy_health < 0
        ]

        return all(conditions)

    async def get_user_starting_health(self, user: database.User):
        entry, _ = user.get_selected()
        self._user_selected = entry

        pokemon = entry['pokemon']
        name = pokemon['name']
        level = pokemon['level']

        rounded, hp, atk, defen, spatk, spdef, spd = self.bot._get_ivs(pokemon['ivs'])
        self._user_pokemon, shiny = await self.bot.fetch_pokemon(name)

        await self._user_pokemon.get_stats()

        health = calc.calculate_health(self._user_pokemon.health.base, hp, level) 
        return health

    async def get_enemy_starting_health(self, user: database.User):
        entry, _ = user.get_selected()
        self._enemy_selected = entry

        pokemon = entry['pokemon']
        name = pokemon['name']
        level = pokemon['level']

        rounded, hp, atk, defen, spatk, spdef, spd = self.bot._get_ivs(pokemon['ivs'])
        self._enemy_pokemon, shiny = await self.bot.fetch_pokemon(name)

        await self._enemy_pokemon.get_stats()

        health = calc.calculate_health(self._enemy_pokemon.health.base, hp, level) 
        return health

    def check(self, member, m):
        return m.channel == self.ctx.channel and m.author == member

    def get_attack_stats(self, entry: Mapping[str, Any], pokemon: wrapper.Pokemon):
        level = entry['pokemon']['level']
        ivs = entry['pokemon']['ivs']
        nature = entry['pokemon']['nature']

        atk = calc.calculate_other(pokemon.attack.base, ivs['attack'], level, nature['atk'])
        spatk = calc.calculate_other(pokemon.spatk.base, ivs['spatk'], level, nature['spatk'])

        return atk, spatk

    def get_speed_stats(self, entry: Mapping[str, Any], pokemon: wrapper.Pokemon):
        level = entry['pokemon']['level']
        ivs = entry['pokemon']['ivs']
        nature = entry['pokemon']['nature']

        speed = calc.calculate_other(pokemon.speed.base, ivs['speed'], level, nature['speed'])
        return speed

    def get_defense_stats(self, entry: Mapping[str, Any], pokemon: wrapper.Pokemon):
        level = entry['pokemon']['level']
        ivs = entry['pokemon']['ivs']
        nature = entry['pokemon']['nature']

        defense = calc.calculate_other(pokemon.defense.base, ivs['defense'], level, nature['def'])
        spdef = calc.calculate_other(pokemon.spdef.base, ivs['spatk'], level, nature['spdef'])

        return defense, spdef

    async def user_turn(self):
        await self.embed(self.user, self._user)

        level = self._user_selected['pokemon']['level']
        moves = self._user_selected['pokemon']['moves']

        atk, spatk = self._user_atk, self._user_spatk
        defense, spdef = self._enemy_def, self._enemy_spdef

        damage = await self.validate_choice(
            user=self.user,
            moves=moves,
            level=level,
            atk=atk,
            spatk=spatk,
            defense=defense,
            spdefense=spdef
        )
        return round(damage)

    async def enemy_turn(self):
        await self.embed(self.enemy, self._enemy)

        level = self._enemy_selected['pokemon']['level']
        moves = self._enemy_selected['pokemon']['moves']

        atk, spatk = self._enemy_atk, self._enemy_spatk
        defense, spdef = self._user_def, self._user_spdef

        damage = await self.validate_choice(
            user=self.enemy,
            moves=moves,
            level=level,
            atk=atk,
            spatk=spatk,
            defense=defense,
            spdefense=spdef
        )
        return round(damage)

    async def validate_choice(self, user, moves, level: int, atk: int, spatk: int, defense: int, spdefense: int):
        try:
            check = functools.partial(self.check, user)

            message = await self.bot.wait_for('message', check=check, timeout=20)
            context = await self.bot.get_context(message)

            if context.valid:
                return await self.validate_choice(moves, level, atk, spatk, defense, spdefense)

        except asyncio.TimeoutError:
            await self.ctx.send('You took too long. Duel cancelled.')
            self.cancelled = True

            return 0

        await message.delete()
        move = message.content

        if int(move) < 0 or int(move) > 4:
            await self.ctx.send('Invalid move range.')

        choice = moves[move]
        move = await wrapper.get_move(choice.lower().replace(' ', '-'), self.bot.session)

        dmg = 0

        if calc.miss(move.accuracy):
            return dmg

        if move.damage_class.lower() == 'physical':
            return calc.damage(level, move.power, atk, defense, 1)

        if move.damage_class.lower() == 'special':
            return calc.damage(level, move.power, spatk, spdefense, 1)

        return dmg

    async def embed(self, member: discord.Member, db: database.User):
        moves = db.get_selected_moves()

        embed = discord.Embed(title='Duel')
        embed.description = 'Please pick a move from the list below.'

        for k, v in moves.items():
            embed.add_field(name=k, value='None' if v is None else v.title(), inline=False)

        return await member.send(embed=embed)

    def get_faster_pokemon(self):
        speed1 = self.get_speed_stats(self._user_selected, self._user_pokemon)
        speed2 = self.get_speed_stats(self._enemy_selected, self._enemy_pokemon)

        return speed1 > speed2

def setup(bot: Pokecord):
    bot.add_cog(Duels(bot))