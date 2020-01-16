import discord
import os
from discord.ext import commands, tasks
from idola_api import IdolaAPI


IDOLA_AUTH_KEY = os.getenv('IDOLA_AUTH_KEY')
IDOLA_RES_VER= os.getenv('IDOLA_RES_VER')
IDOLA_APP_VER = os.getenv('IDOLA_APP_VER')

print(f"Idola Version: {IDOLA_APP_VER}")

idola = IdolaAPI(auth_key=IDOLA_AUTH_KEY, res_ver=IDOLA_RES_VER, app_ver=IDOLA_APP_VER)


class IDOLA(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_ready(self):
        GUILD = "IDOLATest"
        await self.client.change_presence(activity=discord.Game("Ready!"))
        for guild in self.client.guilds:
            if guild.name == GUILD:
                break

        print(
            f'{self.client.user} is connected to the following guild:\n'
            f'{guild.name}(id: {guild.id})'
        )
        self.border_status_update.start()

    @tasks.loop(seconds=5, reconnect=True)
    async def border_status_update(self):
        border_score = idola.show_top_100_raid_suppression_border_number()
        await self.client.change_presence(
            activity=discord.Game(f"{border_score:,d} - SuppressionBorderTop100")
        )

    @commands.command()
    async def arena_border(self, ctx):
        """Shows the Top 100 border for arena"""
        msg = idola.show_top_100_arena_border()
        await ctx.send(msg)

    @commands.command()
    async def suppression_border(self, ctx):
        """Shows the Top 100 border for Idola Raid Suppression"""
        msg = idola.show_top_100_raid_suppression_border()
        await ctx.send(msg)

    @commands.command()
    async def creation_border(self, ctx):
        """Shows the Top 100 border for Idola Raid Creation"""
        msg = idola.show_top_100_raid_creator_border()
        await ctx.send(msg)

    @commands.command()
    async def arena_team(self, ctx, profile_id : int):
        """Shows the latest ranked arena team for a given profile_id"""
        msg = idola.show_arena_team_composition(profile_id)
        await ctx.send(msg)

    @arena_team.error
    async def arena_team_error(self, ctx, error):
        print(error)
        await ctx.send("Please provide a valid id")

    @commands.command()
    async def arena_top_100(self, ctx):
        """Shows the Top 100 Arena players"""
        msg = idola.show_arena_ranking_top_100_players()
        msg = msg.split("\n")
        for chunks in [msg[i:i+50] for i in range(0, len(msg), 50)]:
            await ctx.send("\n".join(chunks))

    @commands.command()
    async def suppression_top_100(self, ctx):
        """Shows the Top 100 Idola Raid Suppression players"""
        msg = idola.show_raid_suppression_top_100_players()
        msg = msg.split("\n")
        for chunks in [msg[i:i+50] for i in range(0, len(msg), 50)]:
            await ctx.send("\n".join(chunks))

    @commands.command()
    async def creation_top_100(self, ctx):
        """Shows the Top 100 Idola Creation players"""
        msg = idola.show_raid_creation_top_100_players()
        msg = msg.split("\n")
        for chunks in [msg[i:i+50] for i in range(0, len(msg), 50)]:
            await ctx.send("\n".join(chunks))


def setup(client):
    client.add_cog(IDOLA(client))