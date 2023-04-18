# -*- coding: utf-8 -*-
# @Author: Ultraxime
# @Date:   2023-03-08 19:43:44
# @Last Modified by:   Ultraxime
# @Last Modified time: 2023-03-18 13:42:29


from discord.ext.commands import slash_command
from discord import ApplicationContext

from .default import DefaultCog


class Funny(DefaultCog):

    @slash_command(name = "hello", description = "Say hello to the bot")
    async def on_hello(self, ctx: ApplicationContext):
        self._command_used(ctx, "/hello")
        await ctx.respond("Hey!")

    @slash_command(name="ping", description="Plays ping-pong")
    async def on_ping(self, ctx: ApplicationContext):
        """
        Called on ping command.
        Aswer by a pond

        :param      ctx:  The context
        :type       ctx:  Context
        """
        self._command_used(ctx, "/ping")
        await ctx.respond("pong")
