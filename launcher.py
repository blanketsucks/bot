from typing import List, Tuple
import datetime
import asyncio
import aiohttp
import logging

from src.utils import print_with_color, Colors
from src.bot import Pokecord
from src import database
import config

# Mostly taken from: https://github.com/Rapptz/discord.py/blob/master/discord/utils.py#L1209
class ColorFormatter(logging.Formatter):
    LEVELS: List[Tuple[int, Colors]] = [
        (logging.INFO, Colors.green),
        (logging.WARNING, Colors.yellow),
        (logging.ERROR, Colors.red),
        (logging.CRITICAL, Colors.red)
    ]

    FORMATS = {
        level: logging.Formatter(f'{color}[%(levelname)s]{Colors.reset} %(message)s')
        for level, color in LEVELS
    }

    def format(self, record):
        formatter = self.FORMATS.get(record.levelno)
        if formatter is None:
            formatter = self.FORMATS[logging.INFO]

        if record.exc_info:
            text = formatter.formatException(record.exc_info)
            record.exc_text = f'{Colors.red}{text}{Colors.reset}'

        output = formatter.format(record)
        record.exc_text = None

        return output

def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    handler = logging.StreamHandler()
    handler.setFormatter(ColorFormatter())

    logger.addHandler(handler)

async def main():
    bot = Pokecord()
    setup_logging()

    await bot.load_extension('jishaku')

    await bot.load_extension('src.cogs.guilds')
    await bot.load_extension('src.cogs.pokedex')
    await bot.load_extension('src.cogs.pokemons')
    await bot.load_extension('src.cogs.trading')
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