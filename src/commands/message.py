# -*- coding: utf-8 -*-
# @Author: Ultraxime
# @Date:   2023-03-16 17:48:12
# @Last Modified by:   Ultraxime
# @Last Modified time: 2023-03-16 18:34:43

from discord.commands.context import ApplicationContext
from typing import List

class Message:
    _content: List[str]

    def __init__(self, content):
        if not isinstance(content, str):
            content = str(content)
        self._content = []
        last_line = -1
        next_line = -1
        i = 0
        while i < len(content):
            if content[i] == '\n':
                if i - last_line < 2000:
                    next_line = i
                else:
                    self._content.append(content[last_line+1:next_line])
                    last_line = next_line
                    next_line = i
            i += 1
        self._content.append(content[last_line+1:])

        if self._content == []:
            self._content = [" "]

    async def send(self, ctx: ApplicationContext):
        await ctx.respond(self._content[0])

        for msg in self._content[1:]:
            await ctx.send(msg)
