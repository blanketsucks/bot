import asyncio
from utils.translator import Translator
import timeit

from pprint import pprint as print

loop = asyncio.get_event_loop()

@timeit.timeit
def main():
    translator = Translator('japanese')
    data = loop.run_until_complete(translator.translate('hello, world!'))
    print(data.matches[-1].translation)
