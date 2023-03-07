#!/bin/python3

# -*- coding: utf-8 -*-
# @Author: Ultraxime
# @Date:   2022-06-27 11:25:50
# @Last Modified by:   Ultraxime
# @Last Modified time: 2022-08-04 18:11:34

"""Main execution script"""

import sys
from src.bot import Bot

if __name__ == "__main__":
    if len(sys.argv) == 2:
        if sys.argv[1] == "healthcheck":
            sys.exit(0)

        if sys.argv[1] == "start":
            bot = Bot()
            bot.run()

sys.exit(1)
