"""
MIT License

Copyright (c) 2021 Oliver Ni, Rapptz

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

from typing import Any, List, Optional

import asyncio
import functools

import discord
from discord.ext import commands

from . import Button, Menu, MenuChannel, MenuPages, PageSource

ViewButton = Button[discord.Interaction]

class ViewMenu(Menu):
    message: discord.Message

    def __init__(self, *, auto_defer: bool = True, **kwargs: Any):
        super().__init__(**kwargs)

        self.auto_defer = auto_defer
        self.view: Optional[discord.ui.View] = None

        self.__tasks: List[asyncio.Task[Any]] = []

    async def _button_callback_wrapper(
        self, button: ViewButton, interaction: discord.Interaction
    ) -> None:
        if interaction.user.id not in self.allowed_ids:
            return
    
        if self.auto_defer:
            await interaction.response.defer()

        try:
            if button.lock:
                async with self._lock:
                    if self._running:
                        await button(self, interaction)
            else:
                await button(self, interaction)
        except Exception as exc:
            await self.on_menu_button_error(exc)

    async def _refresh_view(self, button: ViewButton, *, remove: bool = False) -> None:
        if remove:
            self.buttons.pop(button.emoji, None)
        else:
            self.buttons[button.emoji] = button # type: ignore

        await self._edit_view(self.view)

    async def _edit_view(self, view: Optional[discord.ui.View]) -> None:
        try:
            await self.message.edit(view=view)
        except discord.HTTPException:
            raise

    def create_view(self):
        if not self.should_add_reactions():
            return None

        view = discord.ui.View(timeout=self.timeout)
        for i, (emoji, button) in enumerate(self.buttons.items()):
            item = discord.ui.Button(style=discord.ButtonStyle.secondary, emoji=emoji, row=i // 5)
            item.callback = functools.partial(self._button_callback_wrapper, button) # type: ignore

            view.add_item(item)

        self.view = view
        return view

    def add_button(self, button: ViewButton, *, react: bool = False) -> Any:
        super().add_button(button)

        if react:
            if self.__tasks:
                return self._refresh_view(button)
            else:
                return self._dummy_error()

    def remove_button(self, button: ViewButton, *, react: bool = False):
        super().remove_button(button)

        if react:
            if self.__tasks:
                return self._refresh_view(button, remove=True)
            else:
                return self._dummy_error()

    def clear_buttons(self, *, react=False):
        super().clear_buttons()

        if react:
            if self.__tasks:
                return self._edit_view(None)
            else:
                return self._dummy_error()

    async def _internal_loop(self) -> Any:
        assert self.view and self.bot
        self.__timed_out = False
        try:
            self.__timed_out = await self.view.wait()
        except Exception:
            pass
        finally:
            self._event.set()

            try:
                await self.finalize(self.__timed_out)
            except Exception:
                pass
            finally:
                self.__timed_out = False

            if self.bot.is_closed():
                return

            try:
                if self.delete_message_after:
                    return await self.message.delete()

                if self.clear_reactions_after:
                    return await self.message.edit(view=None)
            except Exception:
                pass

    async def start(
        self, 
        ctx: commands.Context[commands.Bot], 
        *, 
        channel: Optional[MenuChannel] = None, # type: ignore
        wait: bool = False
    ):
        try:
            del self.buttons
        except AttributeError:
            pass

        self.bot = bot = ctx.bot
        self.ctx = ctx
        self._author_id = ctx.author.id

        channel: MenuChannel = channel or ctx.channel # type: ignore
        is_guild = hasattr(channel, 'guild') and channel.guild is not None

        me = channel.guild.me if is_guild else ctx.bot.user # type: ignore
        assert me


        permissions = channel.permissions_for(me) # type: ignore
        self._verify_permissions(ctx, channel, permissions)

        self._event.clear()
        msg = self.message
        if msg is None:
            self.message = msg = await self.send_initial_message(ctx, channel)

        if self.should_add_reactions():
            for task in self.__tasks:
                task.cancel()
            self.__tasks.clear()

            self._running = True
            self.__tasks.append(bot.loop.create_task(self._internal_loop()))

            if wait:
                await self._event.wait()

    def send_with_view(self, messageable: discord.abc.Messageable, *args: Any, **kwargs: Any):
        view = self.create_view()
        if not view:
            return messageable.send(*args, **kwargs)
        else:
            return messageable.send(*args, **kwargs, view=view)

    def stop(self):
        self._running = False
        for task in self.__tasks:
            task.cancel()
        self.__tasks.clear()


class ViewMenuPages(MenuPages, ViewMenu):
    def __init__(self, source: PageSource, **kwargs):
        self._source = source
        self.current_page = 0
        super().__init__(source, **kwargs)

    async def send_initial_message(
        self, ctx: commands.Context[commands.Bot], channel: MenuChannel
    ) -> discord.Message:
        page = await self._source.get_page(0)
        kwargs = await self._get_kwargs_from_page(page)

        return await self.send_with_view(channel, **kwargs)
