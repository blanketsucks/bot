from typing import Dict, ItemsView, KeysView, Mapping, Tuple, TypeVar, Any, ValuesView

import datetime

K = TypeVar('K')
V = TypeVar('V')

__all__ = 'TTLDict',

class TTLDict(Mapping[K, V]):
    def __init__(self, expiry: datetime.timedelta) -> None:
        self.__expiry = expiry
        self.__storage: Dict[K, Tuple[V, datetime.datetime]] = {}

    @property
    def expiry(self) -> datetime.timedelta:
        return self.__expiry

    @property
    def storage(self) -> Dict[K, Tuple[V, datetime.datetime]]:
        return self.__storage.copy()

    def _purge(self) -> None:
        for key, (_, time) in self.storage.items():
            if (time + self.expiry) <= datetime.datetime.utcnow():
                self.__storage.pop(key)

    def __getitem__(self, key: K) -> V:
        self._purge()
        if key not in self.__storage:
            raise KeyError(key)

        return self.__storage[key][0]

    def __setitem__(self, key: K, value: V) -> None:
        self._purge()
        self.__storage[key] = (value, datetime.datetime.utcnow())

    def __delitem__(self, key: K) -> None:
        self._purge()
        if key not in self.__storage:
            raise KeyError(key)

        del self.__storage[key]

    def __contains__(self, key: K) -> bool:
        return key in self.__storage

    def __len__(self) -> int:
        return len(self.__storage)

    def __iter__(self):
        return iter(self.__storage)

    def keys(self) -> KeysView[K]:
        return self.__storage.keys()

    def values(self) -> ValuesView[V]:
        return ValuesView(self)

    def items(self) -> ItemsView[K, V]:
        return ItemsView(self)

    def get(self, key: K, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default

    def pop(self, key: K, default: Any = None) -> Any:
        try:
            del self[key]
        except KeyError:
            return default

    def setdefault(self, key: K, value: V) -> V:
        if key in self:
            return self[key]
        else:
            self[key] = value
            return value