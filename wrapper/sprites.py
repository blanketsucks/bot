from typing import Any, Mapping


class Sprite:
    def __init__(self, __data: Mapping[str, Any], other) -> None:
        self.__data = __data
        self.__other = other

    def __repr__(self) -> str:
        return '<Sprite>'

    @property
    def front(self):
        return self.__data.get('front_default', '')

    @property
    def front_female(self):
        return self.__other.get('front_female', '')

    @property
    def shiny(self):
        return self.__other.get('front_shiny', '')
    
    @property
    def shiny_female(self):
        return self.__other.get('front_shiny', '')
