from typing import List, Tuple
import datetime
import asyncio
import aiohttp
import logging
import os

from src.utils import print_with_color, Colors
from src.bot import Pokecord
from src.consts import COGS
from src import database
import config

os.environ["JISHAKU_NO_UNDERSCORE"] = "True"
os.environ["JISHAKU_NO_DM_TRACEBACK"] = "True" 
os.environ["JISHAKU_HIDE"] = "True"

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
    return logger

EXTENSIONS: List[str] = ['jishaku']
for file in COGS.glob('*[!_].py'):
    file = file.with_suffix('')

    EXTENSIONS.append('.'.join(file.parts[-3:]))

async def main():
    logger = setup_logging()
    bot = Pokecord(logger)

    for extension in EXTENSIONS:
        await bot.load_extension(extension)

    pool = await database.connect(config.DATABASE, bot=bot)
    logger.info('Successfully connected to the database.')

    async with pool.acquire() as conn:
        version = await conn.fetchval('SELECT version()')
        logger.info('PostgreSQL version: %s', version)

        with open('src/database/schema.sql', 'r') as f:
            await conn.execute(f.read())

        logger.info('Database schema created.')

    now = datetime.datetime.now()
    logger.info('Starting bot at %s%s%s.', Colors.blue.value, now, Colors.reset.value)
    
    async with aiohttp.ClientSession() as session:
        bot.session = session
        bot.pool = pool

        async with bot:
            await bot.start(config.TOKEN)

try:
    asyncio.run(main())
except KeyboardInterrupt:
    pass