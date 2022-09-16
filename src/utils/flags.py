from __future__ import annotations

from typing import Any, Dict, List, Literal, Type, Tuple, Union, TYPE_CHECKING

import argparse
import sys
from dataclasses import dataclass, field
from discord.utils import MISSING, evaluate_annotation
from discord.ext import commands

if TYPE_CHECKING:
    from typing_extensions import Self

NoneType = type(None)

class FlagParserError(commands.BadArgument):
    pass

@dataclass
class Flag:
    name: str = MISSING
    annotation: Any = MISSING
    default: Any = MISSING
    nargs: Union[int, str] = MISSING
    aliases: List[str] = field(default_factory=list)
    positional: bool = False
    choices: List[str] = MISSING

    @property
    def required(self) -> bool:
        return self.default is MISSING

def flag(
    *, 
    name: str = MISSING, 
    default: Any = MISSING, 
    aliases: List[str] = MISSING,
    choices: List[str] = MISSING,
    nargs: Union[int, str] = MISSING,
    positional: bool = False
) -> Any:
    return Flag(
        name=name, 
        default=default,
        nargs=nargs, 
        aliases=aliases, 
        choices=choices, 
        positional=positional
    )

class ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str):
        raise FlagParserError(message)

def _walk_flags(bases: Tuple[Type[Any], ...]) -> Tuple[Dict[str, Flag], Dict[str, str]]:
    flags: Dict[str, Flag] = {}
    aliases: Dict[str, str] = {}

    for base in bases:
        if not issubclass(base, FlagParser):
            continue

        flags.update(base.__internal_flags__)
        aliases.update(base.__flag_aliases__)

    return flags, aliases

class FlagParserMeta(type):
    __internal_flags__: Dict[str, Flag]
    __flag_aliases__: Dict[str, str]
    __flag_prefix__: str

    def __new__(cls, name: str, bases: Tuple[Type[Any], ...], attrs: Dict[str, Any], **kwargs: Any):
        flags, aliases = _walk_flags(bases)
        annotations: Dict[str, Any] = attrs.get('__annotations__', {})

        for key, value in annotations.items():
            if key in attrs:
                flag = attrs.pop(key)
                if not isinstance(flag, Flag):
                    raise TypeError(f'{key!r} must be a Flag instance')

                if flag.name is MISSING:
                    flag.name = key
            else:
                flag = Flag(key)

            if flag.positional and flag.aliases is not MISSING:
                raise ValueError('Positional flags cannot have aliases')

            if isinstance(value, str):
                frame = sys._getframe(1)
                value = evaluate_annotation(value, frame.f_globals, frame.f_locals, {})

            if getattr(value, '__origin__', value) is Union:
                args = value.__args__
                if NoneType in args:
                    flag.default = None

                    frame = sys._getframe(1)
                    value = evaluate_annotation(args[0], frame.f_globals, frame.f_locals, {})
                else:
                    raise TypeError('Union types are not supported')

            if getattr(value, '__origin__', value) is Literal:
                flag.choices = value.__args__

            flag.annotation = value
            flags[flag.name] = flag

            if flag.aliases is not MISSING:
                aliases.update({alias: flag.name for alias in flag.aliases})

        attrs['__internal_flags__'] = flags
        attrs['__flag_aliases__'] = aliases
        attrs['__flag_prefix__'] = kwargs.get('prefix', '--')

        return super().__new__(cls, name, bases, attrs)

    def create_argument_parser(cls) -> argparse.ArgumentParser:
        prefix = cls.__flag_prefix__
        parser = ArgumentParser(prefix_chars=prefix)

        for name, flag in cls.__internal_flags__.items():
            if not flag.positional:
                names = [f'{prefix}{name}']
                if flag.aliases is not MISSING:
                    names.extend([f'{prefix}{alias}' for alias in flag.aliases])
            else:
                names = [name]

            add_type = True
            action = MISSING

            if flag.annotation is bool:
                action = 'store_true'

            if (
                (getattr(flag.annotation, '__origin__', flag.annotation) is Literal) or 
                (flag.annotation not in (str, int, float))
            ):
                add_type = False

            kwargs: Dict[str, Any] = {}
            if action is not MISSING:
                kwargs['action'] = action
            if flag.nargs is not MISSING:
                kwargs['nargs'] = flag.nargs
            if flag.default is not MISSING:
                kwargs['default'] = flag.default
            if flag.choices is not MISSING:
                kwargs['choices'] = flag.choices
            if add_type:
                kwargs['type'] = flag.annotation

            parser.add_argument(*names, **kwargs)

        return parser

class FlagParser(metaclass=FlagParserMeta):

    @classmethod
    def get_flags(cls) -> List[Flag]:
        return list(cls.__internal_flags__.values())

    @classmethod
    def default(cls: Type[Self]) -> Self:
        return cls()

    @classmethod
    def parse(cls: Type[Self], args: str) -> Self:
        parser = cls.create_argument_parser()
        namespace = parser.parse_args(args.split())

        self = cls()
        for key, value in namespace.__dict__.items():
            key = cls.__flag_aliases__.get(key, key)
            setattr(self, key, value)

        return self

    @classmethod
    async def convert(cls: Type[Self], _: commands.Context, args: str) -> Self:
        return cls.parse(args)

    def __getattr__(self, _: str) -> None:
        return None
