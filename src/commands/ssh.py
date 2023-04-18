# -*- coding: utf-8 -*-
# @Author: Ultraxime
# @Date:   2023-03-08 16:58:36
# @Last Modified by:   Ultraxime
# @Last Modified time: 2023-03-18 13:41:17

from typing import Union

from discord.ext.commands import slash_command
from discord.commands import Option
from discord import ApplicationContext, Member, User, ButtonStyle
from discord.ui import View, button, Item

import zmq
import zmq.asyncio
from zmq.asyncio import Socket

from .default import DefaultCommandGroup
from ..ssh_keys import SshKey, SshKeyConverter, SshKeyDict
from .message import Message


class ValidationView(View):

    def __init__(self, on_success, on_failure,
                 *items: Item, timeout: float | None = 180,
                 disable_on_timeout: bool = True):
        self._on_success = on_success
        self._on_failure = on_failure
        super().__init__(*items, timeout=timeout,
                         disable_on_timeout=disable_on_timeout)

    @button(label="Yes", style=ButtonStyle.success)
    async def success_callback(self, _, interaction):
        self.stop()
        await self._on_success()
        self.disable_all_items()
        await interaction.response.edit_message(view=self)

    @button(label="No", style=ButtonStyle.danger)
    async def faillure_callback(self, _, interaction):
        self.stop()
        await self._on_failure()
        self.disable_all_items()
        await interaction.response.edit_message(view=self)

    async def on_timeout(self):
        await self._on_failure()
        await super().on_timeout()


class Ssh(DefaultCommandGroup):
    _socket: Socket

    def __init__(self, bot):
        super().__init__(bot, "ssh-key", description="SSH related commands")
        context = zmq.asyncio.Context()                     # pylint: disable=E0110
        self._socket = context.socket(zmq.REQ)
        self._socket.connect("tcp://" + self._bot.get_param("sockets.ssh.ip")
                             + ":"
                             + str(self._bot.get_param("sockets.ssh.port")))

    @slash_command(name = "del", description = "Removes the given ssh key")
    async def on_del_key(self, ctx: ApplicationContext,
                         key_name: Option(str,
                            description=("Name of the key to be deleted. "
                                         + "Should be of the form "
                                         + "main_name/sub_name/..."))) -> None:
        """
        Called on delete key.

        :param      ctx:       The context
        :type       ctx:       ApplicationContext
        :param      key_name:  The key name
        :type       key_name:  str

        :returns:   Nothing
        :rtype:     None
        """
        self._command_used(ctx, "/ssh-key del", key_name)

        assert isinstance(ctx.author, Union[User, Member])

        if not await self._bot.has_permission(ctx,
                                              ctx.author,
                                              "sys_admin"):
            await ctx.respond(
                "You don,t have the right to perform this command")
            return
        if key_name in await self._list_key():
            async def success():
                if await self._del_key(key_name):
                    await ctx.respond(key_name + " was deleted with success.")
                else:
                    await ctx.respond("An error occured during the deletion of "
                                      + key_name)
            async def failure():
                await ctx.respond(key_name + " was not deleted.")
            await ctx.respond("Do you want to destroy the key "
                              + key_name,
                              view=ValidationView(success, failure))
        else:
            await ctx.respond(key_name + " does not exists.")

    @slash_command(name="add",
                   description="Adds a ssh key")
    async def on_add_key(self, ctx: ApplicationContext,
                         key_name: Option(
                            str,
                            description=(
                                "Name of the key to be added. "
                                + "Should be of the form "
                                + "main_name/sub_name/...")),
                         key: Option(SshKeyConverter,
                                     description="Key to be added")) -> None:
        """
        Called on ssh add key command. Adds a ssh key to the servers (redirect
        and pi) User must be part of the group of system administrator\
        specified in permission.sys_admin in the config file

        :param      ctx:             The context
        :type       ctx:             ApplicationContext
        :param      key:             The key
        :type       key:             str

        :returns:   None
        :rtype:     None

        :raises     AssertionError:  Issues with the typing of the ZMQ lib
        """
        self._command_used(ctx, "/ssh-key add", key_name, key)

        assert isinstance(ctx.author, Union[User, Member])
        assert isinstance(key, SshKey)

        if not await self._bot.has_permission(ctx,
                                              ctx.author,
                                              "sys_admin"):
            await ctx.respond(
                "You don,t have the right to perform this command")
            return
        if key_name in await self._list_key():
            async def success():
                if await self._del_key(key_name):
                    if await self._add_key(key_name, key):
                        await ctx.respond(key_name
                                          + " was added with success.")
                    else:
                        await ctx.respond(
                            "An error occured during the adding of "
                            + key_name)
                else:
                    await ctx.respond(
                        "An error occured during the deletion of " + key_name)
            async def failure():
                await ctx.respond(
                    key_name
                    + " was not added because of "
                    + "a pre-existing key with the same name.")
            await ctx.respond("Do you want to destroy the key "
                              + key_name,
                              view=ValidationView(success, failure))
        elif await self._add_key(key_name, key):
            await ctx.respond(key_name + " was added with success.")
        else:
            await ctx.respond("An error occured during the adding of "
                              + key_name)

    @slash_command(name="list",
                   description="List the ssh keys")
    async def on_list_keys(self, ctx: ApplicationContext) -> None:
        self._command_used(ctx, "/ssh-key list")

        assert isinstance(ctx.author, Union[User, Member])
        if not await self._bot.has_permission(ctx,
                                              ctx.author,
                                              "sys_admin"):
            await ctx.respond(
                "You don,t have the right to perform this command")
            return
        content = await self._list_key()
        if content == "":
            content = "There are no keys."
        msg = Message(content)
        await msg.send(ctx)

    async def _add_key(self, key_name: str, key: SshKey):
        self._socket.send_pyobj({"ADD": SshKeyDict({key_name: key})})
        msg = await self._socket.recv_pyobj()
        match msg:
            case "ACK":
                return True
            case "FAIL":
                return False
            case _:
                raise ValueError(msg + " is not a valid message")

    async def _del_key(self, key_name) -> bool:
        self._socket.send_pyobj({"DEL": key_name})
        msg = await self._socket.recv_pyobj()
        match msg:
            case "ACK":
                return True
            case "FAIL":
                return False
            case _:
                raise ValueError(msg + " is not a valid message")

    async def _list_key(self) -> SshKeyDict:
        print("asking list")
        self._socket.send_pyobj("LIST")
        print("waiting list")
        liste = await self._socket.recv_pyobj()
        print("list received")
        assert isinstance(liste, dict)
        assert len(liste) == 1
        assert isinstance(liste["LIST"], SshKeyDict)
        return liste["LIST"]
