# -*- coding: utf-8 -*-
# @Author: Ultraxime
# @Date:   2022-06-27 12:01:53
# @Last Modified by:   Ultraxime
# @Last Modified time: 2023-03-07 19:04:32

"""Module creating a discord bot"""

from collections.abc import Awaitable
from typing import Union
import sys
from asyncio import Future

import zmq
import zmq.asyncio

from discord import Guild, Member, User
from discord.ext import commands, tasks
from discord.ext.commands import Context

from src.config import Config


class Bot(commands.Bot):
    """Class representing a discord bot"""
    __config: Config

    def __init__(self):
        self.__config = Config("/config")
        super().__init__(command_prefix=self.__config.get("prefix"),
                         description=self.__config.get("description"))
        self.add_command(self.on_ping)
        self.add_command(self.on_prefix_update)
        self.add_command(self.on_image_build)

        self.zmq_messages_handler.start()

    def run(self, *args, **kwargs):
        super().run(self.__config.get("bot_token"), args, kwargs)

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
        channel_id = self.__config.get("channels.log")

        if channel_id is None or channel_id == "":
            raise ValueError("No id has been specified for the log channel.")

        channel_id = int(channel_id)
        channel = self.get_channel(channel_id)

        if channel is None:
            raise ValueError("The log channel does not exist.")

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
        channel_id = self.__config.get("channels.warn")

        if channel_id is None or channel_id == "":
            print("No id has been specified for the warn channel.\n"
                  + "Falling back on the log channel")
            await self.log(msg, header)
            return

        channel_id = int(channel_id)
        channel = self.get_channel(channel_id)

        if channel is None:
            print("The warn channel does not exist.\n"
                  + "Falling back on the log channel",
                  file=sys.stderr)
            await self.log(msg, header)
            return

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
        channel_id = self.__config.get("channels.error")

        if channel_id is None or channel_id == "":
            print("No id has been specified for the error channel.\n"
                  + "Falling back on the warn channel")
            await self.warn(msg, header)
            return

        channel_id = int(channel_id)
        channel = self.get_channel(channel_id)

        if channel is None:
            print("The error channel does not exist.\n"
                  + "Falling back on the warn channel",
                  file=sys.stderr)
            await self.warn(msg, header)
            return

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
        channel_id = self.__config.get("channels.report")

        if channel_id is None or channel_id == "":
            print("No id has been specified for the report channel.\n"
                  + "Falling back on the log channel")
            await self.log(msg, header)
            return

        channel_id = int(channel_id)
        channel = self.get_channel(channel_id)

        if channel is None:
            print("The report channel does not exist.\n"
                  + "Falling back on the log channel",
                  file=sys.stderr)
            await self.log(msg, header)
            return

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

    @staticmethod
    @commands.command(name="ping", help="Plays ping-pong")
    async def on_ping(ctx: Context):
        """
        Called on ping command.
        Aswer by a pond

        :param      ctx:  The context
        :type       ctx:  Context
        """
        await ctx.send("pong")

    @staticmethod
    @commands.command(name="update_prefix",
                      help="Update the prefix of the commands")
    async def on_prefix_update(ctx: Context, prefix: str) -> None:
        """
        Called on prefix update command.
        Update the prefix of the bot.
        User must be part of the group of discord administrator\
            specified in permission.discord in the config file

        :param      ctx:             The context
        :type       ctx:             Context
        :param      prefix:          The prefix
        :type       prefix:          str

        :returns:   None
        :rtype:     None

        :raises     AssertionError:  Issue with an overriding
        """
        assert isinstance(ctx.bot, Bot)
        assert isinstance(ctx.author, Union[User, Member])
        if not await Bot.has_permission(ctx,
                                        ctx.author,
                                        ctx.bot.get_param("permission.discord")):
            await ctx.reply("You don,t have the right to perform this command")
            return
        ctx.bot.command_prefix = prefix
        ctx.bot.set_param('prefix', prefix)
        await ctx.send('Command prefix updated at ' + prefix)

    @staticmethod
    @commands.command(name="ssh_add_key",
                      help="Adds a ssh key")
    async def on_ssh_add_key(ctx: Context, key: str) -> None:
        """
        Called on ssh add key command. Adds a ssh key to the servers (redirect
        and pi) User must be part of the group of system administrator\
        specified in permission.sys_admin in the config file
        
        :param      ctx:             The context
        :type       ctx:             Context
        :param      key:             The key
        :type       key:             str
        
        :returns:   None
        :rtype:     None
        
        :raises     AssertionError:  Issues with the typing of the ZMQ lib
        """
        assert isinstance(ctx.bot, Bot)
        assert isinstance(ctx.author, Union[User, Member])
        if not await Bot.has_permission(ctx,
                                        ctx.author,
                                        ctx.bot.get_param("permission.sys_admin")):
            await ctx.reply("You don,t have the right to perform this command")
            return
        print("Starting adding the key")
        await ctx.send("Starting image builder")
        context = zmq.asyncio.Context()
        socket = context.socket(zmq.REQ)
        socket.connect("tcp://" + ctx.bot.get_param("maintainer")
                       + ":" + str(ctx.bot.get_param("socket_port")))
        await socket.send_multipart([b"Ssh Add Key", image.encode("utf-8")])
        msg = socket.recv_multipart()
        assert isinstance(msg, Awaitable)
        await msg
        assert isinstance(msg, Future)
        msg = msg.result()
        if len(msg) != 1:
            decoded = ""
            for part in msg:
                assert isinstance(part, bytes)
                decoded += part.decode("utf-8") + ", "
            decoded = decoded[:-2] + "."
            print("Error: " + decoded,
                  file=sys.stderr)

            await ctx.send("Adding the key returned an error: " + decoded)
        else:
            content = msg[0]
            assert isinstance(content, bytes)
            if content == b"ACK":
                print("Adding the key finished with success")
                await ctx.send("Adding the key finished with success")
            else:
                print("Error: " + content.decode("utf-8"),
                      file=sys.stderr)
                await ctx.send("Adding the key returned an error: "
                               + content.decode("utf-8"))

    @tasks.loop(count=1)
    async def zmq_messages_handler(self) -> None:
        """
        Handler for the reception of ZMQ messages

        :returns:   None
        :rtype:     None

        :raises     AssertionError:  Issues with the typing of the ZMQ lib
        """
        await self.wait_until_ready()
        context = zmq.asyncio.Context()
        socket = context.socket(zmq.REP)
        socket.bind("tcp://*:" + str(self.__config.get("socket_port")))
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

    @staticmethod
    async def has_permission(ctx: Context,
                             user: Union[Member, User],
                             role_id: Union[str, int]) -> bool:
        """
        Determines if the user has the permission.

        :param      ctx:             The context
        :type       ctx:             Context
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

        if role_id is None or role_id == "":
            return True
        guild = ctx.guild
        assert isinstance(guild, Guild)
        role = guild.get_role(int(role_id))

        if role is None:
            await ctx.send("Error: The permission id does not exist.")
            return True

        return role in user.roles
