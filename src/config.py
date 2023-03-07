# -*- coding: utf-8 -*-
# @Author: Ultraxime
# @Date:   2022-05-13 12:43:56
# @Last Modified by:   Ultraxime
# @Last Modified time: 2022-07-19 16:27:04

"""Module use for the Config file managemnt"""

import os
import shutil
import yaml


DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                   "../default_config/")


class Config:
    """
    Class representing a configuration file
    """
    __content: dict
    __path: str

    def __init__(self,
                 path: str):
        self.__path = path
        if not os.path.exists(path):
            self.create()
        with open(path, 'r', encoding="utf-8") as file:
            self.__content = yaml.safe_load(file)

    def create(self) -> None:
        """
        Create the config file from the default one

        :returns:   None
        :rtype:     None
        """
        shutil.copyfile(os.path.join(DEFAULT_CONFIG_PATH,
                                     "discord-bot.yml"),
                        self.__path)

    def save(self) -> None:
        """
        Save the modification done to the config file

        :returns:   None
        :rtype:     None
        """
        with open(self.__path, 'w', encoding="utf-8") as file:
            yaml.safe_dump(self.__content, file)

    @staticmethod
    def __access(content: dict, keys: list[str]):
        if len(keys) > 1:
            return Config.__access(content[keys[0]], keys[1::])
        return content[keys[0]]

    def get(self, key: str):
        """
        Gets the value for specified key.

        :param      key:  The key
        :type       key:  str

        :returns:   the value associated to the key
        :rtype:     depends on the key
        """
        keys = key.split('.')
        try:
            return self.__access(self.__content, keys)
        except KeyError:
            if self.__path != os.path.join(DEFAULT_CONFIG_PATH,
                                           "discord-bot.yml"):
                try:
                    value = Config(os.path.join(DEFAULT_CONFIG_PATH,
                                                "discord-bot.yml")).get(key)
                    self.set(key, value)
                    return value
                except KeyError:
                    pass
            raise

    @staticmethod
    def __place(content: dict, keys: list[str], value) -> None:
        if len(keys) > 1:
            Config.__place(content[keys[0]], keys[1::], value)
        else:
            content[keys[0]] = value

    def set(self, key: str, value) -> None:
        """
        Set the value associated to the key

        :param      key:    The new value
        :type       key:    str
        :param      value:  The value
        :type       value:  depends on the key

        :returns:   None
        :rtype:     None
        """
        keys = key.split('.')
        self.__place(self.__content, keys, value)
        self.save()

    @staticmethod
    def __add_key(content: dict, keys: list[str]) -> dict:
        if len(keys) > 1:
            return Config.__add_key(Config.__add_key(content, [keys[0]]),
                                    keys[1::])
        if keys[0] in content:
            return content[keys[0]]

        content[keys[0]] = {}
        return content[keys[0]]

    def add_key(self, key: str) -> None:
        """
        Adds a key to the config file.

        :param      key:  The key
        :type       key:  str

        :returns:   None
        :rtype:     None
        """
        keys = key.split('.')
        self.__add_key(self.__content, keys)
        self.save()

    @staticmethod
    def __has(content: dict, keys: list[str]) -> bool:
        if len(keys) > 0:
            return keys[0] in content and Config.__has(content[keys[0]],
                                                       keys[1::])
        return True

    def __contains__(self, key: str) -> bool:
        keys = key.split('.')
        return self.__has(self.__content, keys)
