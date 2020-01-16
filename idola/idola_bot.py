import discord
import os
import random
import sys
from discord.ext.commands.errors import CommandNotFound
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

bot = commands.Bot(command_prefix="!idola ", description="""IDOLA BOT""")
bot.load_extension("cogs.idola")
bot.run(TOKEN)
