# -*- coding: utf-8 -*-
# @Author: Ultraxime
# @Date:   2023-03-10 18:50:03
# @Last Modified by:   Ultraxime
# @Last Modified time: 2023-03-18 13:45:11

from __future__ import annotations

from collections.abc import MutableMapping
from typing import Optional, Union, Dict, List
from enum import Enum, auto


class KeyMode(Enum):
    DSA = auto()
    ECDSA = auto()
    ECDSA_SK = auto()
    ED25519 = auto()
    ED25519_SK = auto()
    RSA = auto()

    @classmethod
    def _missing_(cls, value: str):
        value = value.upper().replace(" ", "_")
        assert issubclass(cls, Enum)
        for member in cls:
            if member.name == value:
                return member
        return super()._missing_(value)

    def __repr__(self) -> str:
        return "ssh-" + self.name.lower()

    def __str__(self) -> str:
        return self.__repr__()


class SshKey:
    # pylint: disable=R0903
    _mode: KeyMode
    _key: str
    _comment: Optional[str]

    def __init__(self, mode: KeyMode,
                 key: str, comment: Optional[str] = None) -> None:
        self._mode = mode
        i = len(key)-1
        while i > 0 and key[i] == ' ':
            i -= 1
        self._key = key[:i+1]
        if comment is not None:
            i = len(comment)-1
            while i > 0 and comment[i] == ' ':
                i -= 1
            self._comment = comment[:i+1]
        else:
            self._comment = None

    def __repr__(self) -> str:
        return (str(self._mode) + " "
                + self._key
                + ((" " + self._comment) if self._comment is not None else ""))

    def __str__(self) -> str:
        return self.__repr__()

    @classmethod
    def convert(cls, value: str) -> SshKey:
        args = value.split(" ")
        if len(args) < 2:
            raise ValueError(value + " is not a valid ssh key.")
        mode = KeyMode(args[0][4:])
        key = args[1]
        comment = ""
        for word in args[2:]:
            comment += word + " "
        if comment == "":
            comment = None
        return cls(mode, key, comment)

    def __eq__(self, other: SshKey):
        return (self._mode == other._mode             # pylint: disable=W0212
                and self._key == other._key           # pylint: disable=W0212
                and self._comment == other._comment)  # pylint: disable=W0212

    def __ne__(self, other: SshKey):
        return not self.__eq__(other)


try:
    from discord.ext.commands import Converter
    from discord import ApplicationContext

    class SshKeyConverter(Converter):

        async def convert(self, ctx: ApplicationContext, arg: str) -> SshKey:
            args = arg.split(" ")
            if len(args) < 2:
                await ctx.respond(arg + " is not a valid ssh key.")
                raise ValueError(arg + " is not a valid ssh key.")
            try:
                mode = KeyMode(args[0][4:])
            except ValueError:
                await ctx.respond(
                    args[0][4:]
                    + " is not a valid mode for a ssh key.")
                raise
            key = args[1]
            comment = ""
            for word in args[2:]:
                comment += word + " "
            if comment == "":
                comment = None
            return SshKey(mode, key, comment)
except ModuleNotFoundError:
    pass


class SshKeyDict(MutableMapping):
    _content: Dict[str, Union[SshKeyDict, SshKey]]

    def __init__(self, dic: Dict[str, Union[Dict, SshKey]]):
        self._content = {}
        for full_key, value in dic.items():
            key = full_key.split('/')[0]
            if key != full_key:
                value = {full_key[len(key)+1:]: value}
            if isinstance(value, SshKey):
                self._content[key] = value
            else:
                self._content[key] = SshKeyDict(value)

    def __contains__(self, full_key: str) -> bool:
        if full_key == "":
            raise KeyError("Empty keys are not allowed")

        key = full_key.split("/")[0]
        if key == full_key:
            return key in self._content

        remaining_key = full_key[len(key)+1:]
        if key in self._content:
            next_content = self[key]
            if isinstance(next_content, SshKeyDict):
                return remaining_key in next_content
        return False

    def __len__(self) -> int:
        return len(self._content)

    def __getitem__(self, key: str) -> Union[SshKey, SshKeyDict]:
        return self._content[key]

    def __iter__(self):
        return iter(self._content)

    def __setitem__(self, key: str, value: Union[SshKey, SshKeyDict]):
        self._content[key] = value

    def __delitem__(self, key: str) -> None:
        self._content.__delitem__(key)

    @classmethod
    def open(cls, filename: str = "/authorized_key") -> SshKeyDict:
        def _aux(content: List[str]) -> Union[SshKeyDict, SshKey]:
            if content == []:
                return cls({})
            line = content.pop()
            if line[0] == "#":
                count = 0
                while line[count] == "#":
                    count += 1
                dic = cls({})
                while line[:count+1] == "#"*count + " ":
                    dic[line[count+1:-1]] = _aux(content)
                    try:
                        line = content.pop()
                        while line == "\n":
                            line = content.pop()
                    except IndexError:
                        return dic
                content.append(line)
                return dic
            return SshKey.convert(line[:-1])
        with open(filename, "r", encoding="utf-8") as file:
            content = file.readlines()
            content.reverse()
            content = _aux(content)
            if isinstance(content, SshKey):
                return cls({"": content})
            return content

    def __repr__(self, index: int = 0) -> str:
        index += 1
        res = ""
        for key, value in self.items():
            res += "#"*index + " " + key + "\n"
            if isinstance(value, SshKeyDict):
                res += value.__repr__(index)
            else:
                res += str(value) + "\n"
            res += "\n"
        return res

    def __str__(self) -> str:
        return self.__repr__()

    def write(self, filename: str = "/authorized_key"):
        with open(filename, "w", encoding="utf-8") as file:
            file.write(str(self))

    def add(self, addition: SshKeyDict) -> bool:
        for key, value in addition.items():
            if key in self:
                old_value = self[key]
                if isinstance(value, SshKeyDict):
                    if isinstance(old_value, SshKeyDict):
                        if not old_value.add(value):
                            return False
                    else:
                        return False
                elif isinstance(old_value, SshKeyDict):
                    return False
                else:
                    self[key] = value
            else:
                self[key] = value
        return True

    def remove(self, key_name: str) -> bool:
        key_begin = key_name.split('/')[0]
        if key_begin not in self:
            return False
        value = self[key_begin]

        if key_begin == key_name:
            if isinstance(value, SshKey):
                del self[key_begin]
                return True
            return False
        if isinstance(value, SshKeyDict):
            if value.remove(key_name[len(key_begin)+1:]):
                if len(value) == 0:
                    del self[key_begin]
                return True
            return False
        return False

    def diff(self, old_dict: SshKeyDict
             ) -> Dict[str, Union[SshKeyDict, List[str]]]:
        deleted = []
        added = SshKeyDict({})
        for key, value in self.items():
            if key in old_dict:
                old_value = old_dict[key]
                if isinstance(value, SshKey):
                    if isinstance(old_value, SshKey):
                        if old_value != value:
                            deleted.append(key)
                            added[key] = value
                    else:
                        for key_name in old_value.list_key():
                            deleted.append(key + "/" + key_name)
                        added[key] = value
                else:
                    if isinstance(old_value, SshKey):
                        deleted.append(key)
                        added[key] = value
                    else:
                        tmp = value.diff(old_value)
                        for key_name in tmp["DEL"]:
                            assert isinstance(key_name, str)
                            deleted.append(key + "/" + key_name)
                        added_tmp = tmp["ADD"]
                        assert isinstance(added_tmp, SshKeyDict)
                        if len(added_tmp) > 0:
                            added[key] = added_tmp
            else:
                added[key] = value
        for key, value in old_dict.items():
            if key not in self:
                if isinstance(value, SshKey):
                    deleted.append(key)
                else:
                    for key_name in value.list_key():
                        deleted.append(key + "/" + key_name)
        return {"DEL": deleted,
                "ADD": added}

    def list_key(self) -> List[str]:
        ret = []
        for key, value in self.items():
            if isinstance(value, SshKey):
                ret.append(key)
            else:
                for key_name in value.list_key():
                    ret.append(key + "/" + key_name)
        return ret
