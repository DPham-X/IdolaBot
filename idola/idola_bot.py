# -*- coding: utf-8 -*-
import logging
import os

from discord.ext import commands
from dotenv import find_dotenv, load_dotenv

# Logging
logFormatter = logging.Formatter("%(asctime)s — %(name)s — %(levelname)s — %(message)s")
logger = logging.getLogger("idola")

fileHandler = logging.FileHandler("idola_bot.log")
fileHandler.setFormatter(logFormatter)
logger.addHandler(fileHandler)

consoleHandler = logging.StreamHandler()
consoleHandler.setFormatter(logFormatter)
logger.addHandler(consoleHandler)

logger.setLevel(logging.DEBUG)

# Discord env variables
load_dotenv(find_dotenv())
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
if not DISCORD_TOKEN:
    raise RuntimeError("DISCORD_TOKEN must be defined")
DISCORD_PREFIX = os.getenv("DISCORD_PREFIX")
if not DISCORD_PREFIX:
    raise Exception("Discord prefix must be defined")

# Start discord bot
bot = commands.Bot(command_prefix=DISCORD_PREFIX, description="""IDOLA BOT""")
bot.load_extension("cogs.idola")
logger.info("Starting IDOLA Discord ...")
bot.run(DISCORD_TOKEN)
