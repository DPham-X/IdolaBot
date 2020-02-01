import discord
import os
import traceback
from discord.ext import commands, tasks
from idola_api import IdolaAPI


IDOLA_AUTH_KEY = os.getenv('IDOLA_AUTH_KEY')
IDOLA_RES_VER= os.getenv('IDOLA_RES_VER')
IDOLA_APP_VER = os.getenv('IDOLA_APP_VER')

print(f"Idola AuthKey: {IDOLA_AUTH_KEY}")
print(f"Idola ResVer: {IDOLA_RES_VER}")
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

    @commands.command(hidden=True)
    @commands.is_owner()
    async def update_auth_key(self, ctx, auth_key: str):
        try:
            msg = idola.update_auth_key(auth_key)
            await ctx.send(msg)
        except Exception as e:
            print(traceback.format_exc())
            await ctx.send(f"Error: Could not update auth_key - {e}")

    @commands.command(hidden=True)
    @commands.is_owner()
    async def update_res_ver(self, ctx, res_ver: str):
        try:
            msg = idola.update_res_ver(res_ver)
            await ctx.send(msg)
        except Exception as e:
            print(traceback.format_exc())
            await ctx.send(f"Error: Could not update res_ver - {e}")

    @commands.command(hidden=True)
    @commands.is_owner()
    async def save_profiles(self, ctx):
        try:
            idola.save_profile_cache()
            await ctx.send("Profile cache saved")
        except Exception as e:
            print(traceback.format_exc())
            await ctx.send(f"Error: Could not save profile cache - {e}")

    @tasks.loop(seconds=30)
    async def border_status_update(self):
        try:
            border_score = idola.show_top_100_raid_suppression_border_number()
            print(f"{border_score:,d} - SuppressionBorderTop100")
            await self.client.change_presence(
                activity=discord.Game(f"{border_score:,d} - SuppressionBorderTop100")
            )
        except Exception as e:
            print(e, traceback.format_exc())
            await self.client.change_presence(
                activity=discord.Game("Popona is down")
            )

    @commands.command()
    async def arena_border(self, ctx):
        """Shows the Top 100 border for arena"""
        msg = idola.show_top_100_arena_border()
        await ctx.send(msg)

    @arena_border.error
    async def arena_border_error(self, ctx, error):
        print(error)
        print(traceback.format_exc())
        await ctx.send("An error occurred")

    @commands.command()
    async def suppression_border(self, ctx):
        """Shows the Top 100 border for Idola Raid Suppression"""
        msg = idola.show_top_100_raid_suppression_border()
        await ctx.send(msg)

    @suppression_border.error
    async def suppression_border_error(self, ctx, error):
        print(error)
        print(traceback.format_exc())
        await ctx.send("An error occurred")

    @commands.command()
    async def creation_border(self, ctx):
        """Shows the Top 100 border for Idola Raid Creation"""
        msg = idola.show_top_100_raid_creator_border()
        await ctx.send(msg)

    @creation_border.error
    async def creation_border_error(self, ctx, error):
        print(error)
        print(traceback.format_exc())
        await ctx.send("An error occurred")

    @commands.command()
    async def arena_team(self, ctx, profile_id : int):
        """Shows the latest ranked arena team for a given profile_id"""
        arena_team = idola.get_arena_team_composition(profile_id)
        embed = discord.Embed(
            title=f"Team Score: {arena_team['team_score']:,d}",
            description=f"**Idomag**\nLaw: {arena_team['law_idomag']}\nChaos: {arena_team['chaos_idomag']}",
            color=discord.Colour.blue()
        )
        embed.set_author(name=f"{arena_team['player_name']}")
        embed.set_thumbnail(url="https://i0.wp.com/bumped.org/idola/wp-content/uploads/2019/11/character-rappy-thumb.png")

        embed.add_field(name="Law Characters", value=arena_team["law_characters"], inline=True)
        embed.add_field(name="Weapon Symbols", value=arena_team["law_weapon_symbols"], inline=True)
        embed.add_field(name="Soul Symbols", value=arena_team["law_soul_symbols"], inline=True)
        embed.add_field(name="Chaos Characters", value=arena_team["chaos_characters"], inline=True)
        embed.add_field(name="Weapon Symbols", value=arena_team["chaos_weapon_symbols"], inline=True)
        embed.add_field(name="Soul Symbols", value=arena_team["chaos_soul_symbols"], inline=True)
        embed.set_footer(text=78*"\u200b")
        await ctx.send(embed=embed)

    @arena_team.error
    async def arena_team_error(self, ctx, error):
        print(error)
        print(traceback.format_exc())
        await ctx.send("An error occurred")

    @commands.command()
    async def arena_team_name(self, ctx, profile_name):
        """Shows the matching arena_team if they are in the top 100"""
        arena_team = idola.get_arena_team_composition_from_name(profile_name)
        if not arena_team:
            await ctx.send("Could not find a player by that name in the cache, to update the cache run \'arena_team\' using your profile id first")
            return
        embed = discord.Embed(
            title=f"Team Score: {arena_team['team_score']:,d}",
            description=f"**Idomag**\nLaw: {arena_team['law_idomag']}\nChaos: {arena_team['chaos_idomag']}",
            color=discord.Colour.blue()
        )
        embed.set_author(name=f"{arena_team['player_name']}")
        embed.set_thumbnail(url="https://i0.wp.com/bumped.org/idola/wp-content/uploads/2019/11/character-rappy-thumb.png")

        embed.add_field(name="Law Characters", value=arena_team["law_characters"], inline=True)
        embed.add_field(name="Weapon Symbols", value=arena_team["law_weapon_symbols"], inline=True)
        embed.add_field(name="Soul Symbols", value=arena_team["law_soul_symbols"], inline=True)
        embed.add_field(name="Chaos Characters", value=arena_team["chaos_characters"], inline=True)
        embed.add_field(name="Weapon Symbols", value=arena_team["chaos_weapon_symbols"], inline=True)
        embed.add_field(name="Soul Symbols", value=arena_team["chaos_soul_symbols"], inline=True)
        embed.set_footer(text=78*"\u200b")
        await ctx.send(embed=embed)

    @arena_team_name.error
    async def arena_team_name_error(self, ctx, error):
        print(error)
        print(traceback.format_exc())
        await ctx.send("An error occurred")

    @commands.command()
    async def arena_top_100(self, ctx):
        """Shows the Top 100 Arena players"""
        players = idola.show_arena_ranking_top_100_players()
        msg = []
        for profile_id, ranking_information in sorted(
            players.items(),
            key=lambda item: item[1]["arena_score_point"],
        ):
            arena_score_rank = ranking_information["arena_score_rank"]
            arena_score_point = ranking_information["arena_score_point"]
            name = ranking_information["name"]
            msg.insert(
                0,
                f"{arena_score_rank}: {arena_score_point:,d} - {name}({profile_id})"
            )
        for j, chunks in enumerate([msg[i:i+50] for i in range(0, len(msg), 50)]):
            text = "\n".join(chunks)
            embed = discord.Embed(
                title="Idola Arena Top 100" if j == 0 else "\u200b",
                description=f"```{text}```",
                color=discord.Colour.red()
            )
            await ctx.send(embed=embed)

    @arena_top_100.error
    async def arena_top_100_error(self, ctx, error):
        print(error)
        print(traceback.format_exc())
        await ctx.send("An error occurred")

    @commands.command()
    async def suppression_top_100(self, ctx):
        """Shows the Top 100 Idola Raid Suppression players"""
        msg = idola.show_raid_suppression_top_100_players()
        msg = msg.split("\n")
        for j, chunks in enumerate([msg[i:i+50] for i in range(0, len(msg), 50)]):
            text = "\n".join(chunks)
            embed = discord.Embed(
                title="Idola Raid Suppression Top 100" if j == 0 else "\u200b",
                description=f"```{text}```",
                color=discord.Colour.red()
            )
            await ctx.send(embed=embed)

    @suppression_top_100.error
    async def suppression_top_100_error(self, ctx, error):
        print(error)
        print(traceback.format_exc())
        await ctx.send("An error occurred")

    @commands.command()
    async def creation_top_100(self, ctx):
        """Shows the Top 100 Idola Creation players"""
        msg = idola.show_raid_creation_top_100_players()
        msg = msg.split("\n")
        for j, chunks in enumerate([msg[i:i+50] for i in range(0, len(msg), 50)]):
            text = "\n".join(chunks)
            embed = discord.Embed(
                title="Idola Raid Summon Top 100" if j == 0 else "\u200b",
                description=f"```{text}```",
                color=discord.Colour.red()
            )
            await ctx.send(embed=embed)

    @creation_top_100.error
    async def creation_top_100_error(self, ctx, error):
        print(error)
        print(traceback.format_exc())
        await ctx.send("An error occurred")


def setup(client):
    client.add_cog(IDOLA(client))