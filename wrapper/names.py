
class Language:
    def __init__(self, __data, __session) -> None:
        self.__data = __data
        self.__session = __session

        self.name = self.__data.get('name', '')
        self.id = self.__data.get('id', 0)

    @property
    def iso3166(self):
        return self.__data.get('iso3166', '')

    @property
    def iso639(self):
        return self.__data.get('iso639', '')

    def names(self):
        entries = self.__data.get('names', [])
        return [Name(entry, self.__session) for entry in entries]

class Name:
    def __init__(self, __data, __session) -> None:
        self.__data = __data
        self.__session = __session

        self.name = self.__data.get('name', '')

    async def language(self):
        if getattr(self, '_language', None):
            return self._language

        url = self.__data['language']['url']
        async with self.__session.get(url) as resp:
            data = await resp.json()

        self._language = language = Language(data, self.__session)
        return language
