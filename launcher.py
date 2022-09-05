import datetime
import asyncio
import aiohttp

from src.utils import print_with_color
from src.bot import Pokecord
from src import database
import config

async def main():
    bot = Pokecord()

    await bot.load_extension('jishaku')

    await bot.load_extension('src.cogs.pokedex')
    await bot.load_extension('src.cogs.pokemons')
    await bot.load_extension('src.cogs.spawns')

    pool = await database.connect(config.DATABASE, bot=bot)
    print_with_color('{green}[INFO]{reset} Successfully connected to database.')

    async with pool.acquire() as conn:
        version = await conn.fetchval('SELECT version()')
        print_with_color('{green}[INFO]{reset} PostgreSQL version:', version)

        with open('src/database/schema.sql', 'r') as f:
            await conn.execute(f.read())

        print_with_color('{green}[INFO]{reset} Database schema created.')

    now = datetime.datetime.now()
    print_with_color('{green}[INFO]{reset} Starting bot at {blue}{now}{reset}.', now=now)
    
    async with aiohttp.ClientSession() as session:
        bot.session = session
        bot.pool = pool

        async with bot:
            await bot.start(config.TOKEN)

try:
    asyncio.run(main())
except KeyboardInterrupt:
    pass