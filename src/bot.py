# -*- coding: utf-8 -*-
# @Author: Ultraxime
# @Date:   2022-06-27 12:01:53
# @Last Modified by:   Ultraxime
# @Last Modified time: 2023-03-18 13:35:20

"""Module creating a discord bot"""

from collections.abc import Awaitable
from typing import Union
import sys
from asyncio import Future

import zmq
import zmq.asyncio

from discord import Guild, Member, User, TextChannel, ApplicationContext
from discord.ext import commands, tasks
from discord.ext.commands import CommandError, Context


from .config import Config
from .commands import Ssh, Funny


class Bot(commands.Bot):
    """Class representing a discord bot"""
    __config: Config

    def __init__(self):
        self.__config = Config("/config")
        super().__init__(description=self.__config.get("description"),
                         help_command=commands.MinimalHelpCommand())
        self.add_application_command(Ssh(self))
        self.add_cog(Funny(self))

        self.zmq_messages_handler.start()           # pylint: disable=E1101

    def run(self, *args, **kwargs):
        super().run(self.__config.get("bot_token"))#, args, kwargs)

    def get_param(self, param: str):
        """
        Gets the value of a parameter from the bot config.

        :param      param:  The parameter
        :type       param:  str

        :returns:   The parameter.
        :rtype:     Depends on the parameter
        """
        return self.__config.get(param)

    def set_param(self, param: str, value) -> None:
        """
        Sets the value of a parameter into the bot config.

        :param      param:  The parameter
        :type       param:  str
        :param      value:  The value
        :type       value:  Depends on the parameter

        :returns:   None
        :rtype:     None
        """
        return self.__config.set(param, value)

    async def _get_channel(self, channel_name: str = 'log') -> TextChannel:
        channel_id = self.__config.get(f"channels.{channel_name}")

        fall_back = {"report": "log",
                     "error": "warn",
                     "warn": "log"}


        if channel_id is None or channel_id == "":
            if channel_name == 'log':
                raise ValueError(
                    "No id has been specified for the log channel.")
            print(f"No id has been specified for the {channel_name} channel.\n"
                  + f"Falling back on the {fall_back[channel_name]} channel")
            return await self._get_channel(fall_back[channel_name])

        channel_id = int(channel_id)
        channel = self.get_channel(channel_id)

        if channel is None:
            if channel_name == 'log':
                raise ValueError("The log channel does not exist.")
            print(f"The {channel_name} channel does not exist.\n"
                  + f"Falling back on the {fall_back[channel_name]} channel",
                  file=sys.stderr)
            return await self._get_channel(fall_back[channel_name])

        if not isinstance(channel, TextChannel):
            if channel_name == "log":
                raise ValueError("This log channel is not a text channel.")
            print(f"The {channel_name} channel is not a text channel.\n"
                  + f"Falling back on the {fall_back[channel_name]} channel",
                  file=sys.stderr)
            return await self._get_channel(fall_back[channel_name])

        return channel


    async def log(self, msg: str, header: str = "[LOG]") -> None:
        """
        Send a log on discord, through the bot

        :param      msg:         The message
        :type       msg:         str
        :param      header:      The header
        :type       header:      str

        :returns:   None
        :rtype:     None

        :raises     ValueError: \
                    When there is no log channel specified in the config file,\
                     or this channel does not exist
        """
        channel = await self._get_channel("log")

        await channel.send(header + " " + msg)

    async def warn(self, msg: str, header: str = "[WARN]") -> None:
        """
        Send a warn on discord, through the bot

        :param      msg:         The message
        :type       msg:         str
        :param      header:      The header
        :type       header:      str

        :returns:   None
        :rtype:     None
        """
        channel = await self._get_channel("warn")
        await channel.send(header + " " + msg)

    async def error(self, msg: str, header: str = "[ERROR]") -> None:
        """
        Send a error on discord, through the bot

        :param      msg:         The message
        :type       msg:         str
        :param      header:      The header
        :type       header:      str

        :returns:   None
        :rtype:     None
        """
        channel = await self._get_channel("error")
        await channel.send(header + " " + msg)

    async def report(self, msg: str, header: str = "[REPORT]") -> None:
        """
        Send a report on discord, through the bot

        :param      msg:         The message
        :type       msg:         str
        :param      header:      The header
        :type       header:      str

        :returns:   None
        :rtype:     None
        """
        channel = await self._get_channel("report")
        await channel.send(header + " " + msg)

    async def on_ready(self) -> None:
        """
        Called on ready.

        :returns:   None
        :rtype:     None

        :raises     AssertionError:  If the bot has no user
        """
        assert self.user is not None
        print('Logged in as')
        print(self.user.name)
        print(self.user.id)
        print('------')
        await self.log(self.user.name + " is now online.")

    async def on_command_error(self, context: Context, exception: CommandError):
        await context.reply("The command failed.")
        print("error")
        return await super().on_command_error(context, exception)

    @tasks.loop(count=1)
    async def zmq_messages_handler(self) -> None:
        """
        Handler for the reception of ZMQ messages

        :returns:   None
        :rtype:     None

        :raises     AssertionError:  Issues with the typing of the ZMQ lib
        """
        await self.wait_until_ready()
        context = zmq.asyncio.Context()         # pylint: disable=E0110
        socket = context.socket(zmq.REP)
        socket.bind("tcp://*:" + str(self.__config.get("sockets.ssh.port")))
        while not self.is_closed():
            msg = socket.recv_multipart(copy=True)
            assert isinstance(msg, Awaitable)
            await msg
            assert isinstance(msg, Future)
            msg = msg.result()
            print("Recv: ")
            print(msg)
            if len(msg) != 2:
                await socket.send_multipart([b"FAIL", b"Unvalid message"])
                print("[INFO] Received an invalid message",
                      file=sys.stderr)
                print(msg,
                      file=sys.stderr)
            else:
                content = msg[1]
                assert isinstance(content, bytes)
                if msg[0] == b"LOG":
                    await socket.send_multipart([b"ACK"])
                    await self.log(content.decode("utf-8"))
                elif msg[0] == b"WARN":
                    await socket.send_multipart([b"ACK"])
                    await self.warn(content.decode("utf-8"))
                elif msg[0] == b"ERROR":
                    await socket.send_multipart([b"ACK"])
                    await self.error(content.decode("utf-8"))
                elif msg[0] == b"REPORT":
                    await socket.send_multipart([b"ACK"])
                    await self.report(content.decode("utf-8"))
                else:
                    await socket.send_multipart([b"FAIL", b"Unvalid message"])
                    print("[INFO] Received an invalid message",
                          file=sys.stderr)
                    print(msg,
                          file=sys.stderr)

    async def has_permission(self,
                             context: ApplicationContext,
                             user: Union[Member, User],
                             permission: str) -> bool:
        """
        Determines if the user has the permission.

        :param      context:             The context
        :type       context:             Context
        :param      user:            The user
        :type       user:            Union[Member, User]
        :param      role_id:         The role identifier
        :type       role_id:         Union[Member, User]

        :returns:   True if permission, False otherwise.
        :rtype:     bool

        :raises     AssertionError:  Non respect of the types
        """
        if isinstance(user, User):
            return False
        assert isinstance(user, Member)

        role_id = self.get_param("permission." + permission)
        if role_id is None or role_id == "":
            return True
        guild = context.guild
        assert isinstance(guild, Guild)
        role = guild.get_role(int(role_id))

        if role is None:
            await context.send("Error: The permission id does not exist.")
            return True

        return role in user.roles
