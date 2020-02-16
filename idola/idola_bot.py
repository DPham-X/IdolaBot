# -*- coding: utf-8 -*-
import os

from discord.ext import commands
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())
TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = os.getenv("DISCORD_PREFIX")
if not PREFIX:
    raise Exception("Discord prefix must be defined")

bot = commands.Bot(command_prefix=PREFIX, description="""IDOLA BOT""")
bot.load_extension("cogs.idola")
bot.run(TOKEN)
