# -*- coding: utf-8 -*-
import os
import random
import sys

from discord.ext import commands
from discord.ext.commands.errors import CommandNotFound
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())
TOKEN = os.getenv("DISCORD_TOKEN")

bot = commands.Bot(command_prefix="!idola ", description="""IDOLA BOT""")
bot.load_extension("cogs.idola")
bot.run(TOKEN)
