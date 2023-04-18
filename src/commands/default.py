# -*- coding: utf-8 -*-
# @Author: Ultraxime
# @Date:   2023-03-09 13:15:06
# @Last Modified by:   Ultraxime
# @Last Modified time: 2023-03-17 15:05:01

from __future__ import annotations
from typing import TYPE_CHECKING
from discord import SlashCommandGroup


from discord.ext.commands import Cog
from discord import ApplicationContext

if TYPE_CHECKING:
    from ..bot import Bot


class DefaultCog(Cog):
    _bot: Bot

    def __init__(self, bot):
        self._bot = bot

    def _command_used(self, ctx: ApplicationContext, cmd: str, *args):
        arg_str = ""
        for arg in args:
            arg_str += " " + str(arg)
        print(ctx.author.name + " issued " + cmd + arg_str)


class DefaultCommandGroup(SlashCommandGroup):
    _bot: Bot

    def __init__(self, bot, name, **kwargs):
        self._bot = bot
        super().__init__(name, **kwargs)

    def _command_used(self, ctx: ApplicationContext, cmd: str, *args):
        arg_str = ""
        for arg in args:
            arg_str += " " + str(arg)
        print(ctx.author.name + " issued " + cmd + arg_str)
