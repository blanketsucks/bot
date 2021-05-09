from typing import Any, List, Mapping
import aiohttp

URL = 'http://api.mymemory.translated.net/get'

class Match:
    def __init__(self, data: Mapping[str, Any]) -> None:
        self.id: int = data['id']
        self.segment: str = data['segment']
        self.translation: str = data['translation']
        self.source: str = data['source']
        self.target: str = data['target']
        self.quality: int = data.get('quality', 0)

    def __repr__(self) -> None:
        return '<Match quality={0.quality} source={0.source!r} target={0.target!r}>'.format(self)

class Text(str):
    def __new__(cls, data: Mapping[str, Any]) -> None:
        self = super().__new__(cls, data['responseData']['translatedText'])
        self._data = data

        return self

    @property
    def matches(self) -> List[Match]:
        return [Match(match) for match in self._data['matches']]

class Translator:
    DEFAULT = 'en'

    def __init__(self, language: str, *, session: aiohttp.ClientSession=None) -> None:
        if not session:
            session = aiohttp.ClientSession()

        self.language = language
        self.session = session

    async def translate(self, text: str) -> Text:
        language = '{0}|{1}'.format(self.DEFAULT, self.language)
        params = {
            'q': text, 
            'langpair': language
        }

        async with self.session.get(URL, params=params) as resp:
            data = await resp.json()
            return Text(data)

    async def close(self):
        await self.session.close()

    