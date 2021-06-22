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

        duel = Duel(
            players=[ctx.author, member],
            records=[user, enemy],
            bot=self.bot
        )
        await duel.start(ctx)

class Stats:
    def __init__(self, health: int, atk: int, defense: int, spatk: int, spdef: int, speed: int) -> None:
        self.health = health
        self.attack = atk
        self.defense = defense
        self.spatk = spatk
        self.spdef = spdef
        self.speed = speed

class Player:
    def __init__(self, user: discord.Member, record: database.User, bot: Pokecord) -> None:
        self.user = user
        self.record = record
        self.bot = bot

    async def prepare(self):
        health = await self.get_starting_health()
        attack, spatk = self.get_attack_stats()
        defense, spdef = self.get_defense_stats()
        speed = self.get_speed_stats()

        self.stats = stats = Stats(
            health=health,
            atk=attack,
            defense=defense,
            spatk=spatk,
            spdef=spdef,
            speed=speed,
        )

    async def send_embed(self):
        moves = self.selected.moves

        embed = discord.Embed(title='Duel')
        embed.description = 'Please pick a move from the list below.'

        for (number, move) in moves:
            embed.add_field(name=number, value='None' if move is None else move.title(), inline=False)

        return await self.user.send(embed=embed)

    def check(self, member, m):
        return m.channel == self.ctx.channel and m.author == member

    async def turn(self, ctx: commands.Context):
        await self.send_embed()
        damage = await self.validate_turn(ctx)

        return damage

    async def validate_turn(self,  ctx: commands.Context) -> int:
        try:
            check = functools.partial(self.check, self.user)

            message = await self.bot.wait_for('message', check=check, timeout=20)
            context = await self.bot.get_context(message)

            if context.valid:
                return await self.validate_turn()

        except asyncio.TimeoutError:
            await ctx.send('You took too long. Duel cancelled.')
            self.cancelled = True

            return 0

        await message.delete()
        move = message.content

        if int(move) < 0 or int(move) > 4:
            await self.ctx.send('Invalid move range.')

        choice = self.selected.data['moves'][move]
        move = await wrapper.get_move(choice.lower().replace(' ', '-'), self.bot.session)

        dmg = 0

        if calc.miss(move.accuracy):
            return dmg

        if move.damage_class.lower() == 'physical':
            return round(calc.damage(self.selected.level, move.power, self.stats.attack, self.stats.defense, 1))

        if move.damage_class.lower() == 'special':
            return round(calc.damage(self.selected.level, move.power, self.stats.spatk, self.stats.spdefense, 1))

        return dmg


    async def get_starting_health(self):
        entry, _ = self.record.get_selected()
        self.selected = entry

        name = entry.name
        level = entry.level
        hp = entry.ivs.health
        
        self.pokemon, shiny = await self.bot.fetch_pokemon(name)
        await self.pokemon.get_stats()

        health = calc.calculate_health(self.pokemon.health.base, hp, level) 
        return health

    def get_attack_stats(self):
        level = self.selected.level
        ivs = self.selected.data['ivs']
        nature = self.selected.nature

        atk = calc.calculate_other(self.pokemon.attack.base, ivs['attack'], level, nature.attack)
        spatk = calc.calculate_other(self.pokemon.spatk.base, ivs['spatk'], level, nature.spattack)

        return atk, spatk

    def get_speed_stats(self):
        level = self.selected.level
        ivs = self.selected.data['ivs']
        nature = self.selected.nature

        speed = calc.calculate_other(self.pokemon.speed.base, ivs['speed'], level, nature.speed)
        return speed

    def get_defense_stats(self):
        level = self.selected.level
        ivs = self.selected.data['ivs']
        nature = self.selected.nature

        defense = calc.calculate_other(self.pokemon.defense.base, ivs['defense'], level, nature.defense)
        spdef = calc.calculate_other(self.pokemon.spdef.base, ivs['spatk'], level, nature.spdefense)

        return defense, spdef


class Duel:
    def __init__(self, players: List[discord.Member], records: List[database.User], bot: Pokecord) -> None:
        self.bot = bot

        self.p1 = Player(players[0], records[0], bot)
        self.p2 = Player(players[1], records[1], bot)

        self.cancelled = False

    async def start(self, ctx: commands.Context):
        self.ctx = ctx
        message = await ctx.send('Starting the duel...')

        await self.p1.prepare()
        await self.p2.prepare()

        faster = self.get_faster_pokemon()

        first = self.p1.selected.name.title()
        second = self.p2.selected.name.title()

        embed = discord.Embed(title='Duel')

        embed.description = f'{first}    VS    {second}\n'
        embed.description += f'{self.user_health}/{self.p1.stats.health}        {self.enemy_health}/{self.p2.stats.health}'

        await message.edit(embed=embed, content=None)

        while not self._loop_check():
            if faster:
                dmg1 = await self.p1.turn(self.ctx)
                dmg2 = await self.p2.turn(self.ctx)
            else:
                dmg2 = await self.p2.turn(self.ctx)
                dmg1 = await self.p1.turn(self.ctx)

            self.user_health -= dmg2
            self.enemy_health -= dmg1

            embed = discord.Embed(title=f'{self.p1.user.display_name} VS {self.p1.user.display_name}')

            embed.description = f'{first} VS {second}\n'
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
        return self.p1.stats.speed > self.p2.stats.speed

def setup(bot: Pokecord):
    bot.add_cog(Duels(bot))