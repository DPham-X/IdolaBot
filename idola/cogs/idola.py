# -*- coding: utf-8 -*-
import os
import traceback

import discord
from discord.ext import commands, tasks

from lib.api import IdolaAPI


IDOLA_USER_AGENT = os.getenv("IDOLA_USER_AGENT")
IDOLA_APP_VER = os.getenv("IDOLA_APP_VER")
IDOLA_DEVICE_ID = os.getenv("IDOLA_DEVICE_ID")
IDOLA_DEVICE_TOKEN = os.getenv("IDOLA_DEVICE_TOKEN")
IDOLA_TOKEN_KEY = os.getenv("IDOLA_TOKEN_KEY")
IDOLA_UUID = os.getenv("IDOLA_UUID")

idola = IdolaAPI(
    IDOLA_USER_AGENT,
    IDOLA_APP_VER,
    IDOLA_DEVICE_ID,
    IDOLA_DEVICE_TOKEN,
    IDOLA_TOKEN_KEY,
    IDOLA_UUID,
)


class IDOLA(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.border_fails = 0

    @commands.Cog.listener()
    async def on_ready(self):
        GUILD = "IDOLATest"
        await self.client.change_presence(activity=discord.Game("Ready!"))
        for guild in self.client.guilds:
            if guild.name == GUILD:
                break

        print(f"{self.client.user} is connected to the following guild:\n" f"{guild.name}(id: {guild.id})")

        self.relog.start()
        self.border_status_update.start()
        self.border_channel_update.start()

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        traceback.print_exception(type(error), error, error.__traceback__)
        await ctx.send("An error occurred")

    @commands.command(hidden=True)
    @commands.is_owner()
    async def save_profiles(self, ctx):
        try:
            idola.save_profile_cache()
            await ctx.send("Profile cache saved")
        except Exception as e:
            print(traceback.format_exc())
            await ctx.send(f"Error: Could not save profile cache - {e}")

    @tasks.loop(seconds=60)
    async def border_status_update(self):
        try:
            border_score = idola.get_top_100_raid_suppression_border()
            print(f"{border_score:,d} - SuppressionBorderTop100")
            await self.client.change_presence(activity=discord.Game(f"{border_score:,d} - SuppressionBorderTop100"))
        except Exception as e:
            print(e, traceback.format_exc())
            await self.client.change_presence(activity=discord.Game("Popona is down"))

    @tasks.loop(hours=4)
    async def relog(self):
        print("Relogging started")
        idola.start()

    @tasks.loop(seconds=120)
    async def border_channel_update(self):
        print("Updating channel borders")
        try:
            arena_border_score_100 = idola.get_top_100_arena_border()
            arena_border_score_500 = idola.get_top_500_arena_border()
            arena_border_score_1000 = idola.get_top_1000_arena_border()
            raid_suppression_border_100 = idola.get_top_100_raid_suppression_border()
            raid_suppression_border_1000 = idola.get_top_1000_raid_suppression_border()
            raid_suppression_border_5000 = idola.get_top_5000_raid_suppression_border()
            raid_creation_border_100 = idola.get_top_100_raid_creation_border()
            raid_creation_border_1000 = idola.get_top_1000_raid_creation_border()
            raid_creation_border_5000 = idola.get_top_5000_raid_creation_border()

            # Arena
            channel = self.client.get_channel(677346136176197662)
            await channel.edit(name=f"🥇100: {arena_border_score_100:,d}")
            channel = self.client.get_channel(677860796751151106)
            await channel.edit(name=f"🥈500: {arena_border_score_500:,d}")
            channel = self.client.get_channel(677860638663376927)
            await channel.edit(name=f"🥉1K: {arena_border_score_1000:,d}")

            # Suppression
            channel = self.client.get_channel(677346267231158283)
            await channel.edit(name=f"🥇100: {raid_suppression_border_100:,d}")
            channel = self.client.get_channel(677346847781552137)
            await channel.edit(name=f"🥈1K: {raid_suppression_border_1000:,d}")
            channel = self.client.get_channel(677346863271247930)
            await channel.edit(name=f"🥉5K: {raid_suppression_border_5000:,d}")

            # Creation
            channel = self.client.get_channel(677347022541422612)
            await channel.edit(name=f"🥇100: {raid_creation_border_100:,d}")
            channel = self.client.get_channel(677347036001206322)
            await channel.edit(name=f"🥈1K: {raid_creation_border_1000:,d}")
            channel = self.client.get_channel(677347053902233602)
            await channel.edit(name=f"🥉5K: {raid_creation_border_5000:,d}")
            self.border_fails = 0
        except Exception as e:
            print(traceback.format_exc())
            if self.border_fails == 5:
                # Arena
                channel = self.client.get_channel(677346136176197662)
                await channel.edit(name=f"🥇100: Unknown")
                channel = self.client.get_channel(677860796751151106)
                await channel.edit(name=f"🥈500: Unknown")
                channel = self.client.get_channel(677860638663376927)
                await channel.edit(name=f"🥉1K: Unknown")

                # Suppression
                channel = self.client.get_channel(677346267231158283)
                await channel.edit(name=f"🥇100: Unknown")
                channel = self.client.get_channel(677346847781552137)
                await channel.edit(name=f"🥈1K: Unknown")
                channel = self.client.get_channel(677346863271247930)
                await channel.edit(name=f"🥉5K: Unknown")

                # Creation
                channel = self.client.get_channel(677347022541422612)
                await channel.edit(name=f"🥇100: Unknown")
                channel = self.client.get_channel(677347036001206322)
                await channel.edit(name=f"🥈1K: Unknown")
                channel = self.client.get_channel(677347053902233602)
                await channel.edit(name=f"🥉5K: Unknown")
                self.border_fails = 0
            else:
                self.border_fails += 1

    @commands.command(hidden=True)
    @commands.is_owner()
    async def restart(self, ctx):
        try:
            idola.start()
            await ctx.send("IdolaBot has been restarted")
        except Exception as e:
            print(e, traceback.format_exc())
            await ctx.send("An error occurred, IdolaBot could not be restarted")

    @commands.command()
    async def arena_border(self, ctx):
        """Shows the Top 100 border for arena"""
        border_score_point_100 = idola.get_top_100_arena_border()
        border_score_point_500 = idola.get_top_500_arena_border()
        border_score_point_1000 = idola.get_top_1000_arena_border()

        current_time = idola.get_current_time()
        end_date = idola.get_raid_event_end_date()
        time_left = idola.datetime_difference(current_time, end_date)

        embed = discord.Embed(
            title="Idola Arena Border",
            color=discord.Colour.blue(),
        )
        embed.set_thumbnail(
            url="https://raw.githubusercontent.com/iXyk/IdolaBot/master/idola/lib/assets/arena.png"
        )
        embed.add_field(
            name="Top 100",
            value=f"{border_score_point_100:,d} points",
            inline=True,
        )
        embed.add_field(
            name="Top 500",
            value=f"{border_score_point_500:,d} points",
            inline=True,
        )
        embed.add_field(
            name="Top 1000",
            value=f"{border_score_point_1000:,d} points",
            inline=True,
        )
        embed.add_field(
            name="Time Left",
            value=time_left,
            inline=False
        )
        embed.add_field(
            name="Current Time",
            value=idola.datetime_jp_format(current_time),
            inline=True,
        )
        embed.add_field(
            name="Ending at",
            value=idola.datetime_jp_format(end_date),
            inline=True,
        )
        await ctx.send(embed=embed)

    @commands.command()
    async def suppression_border(self, ctx):
        """Shows the border for Idola Raid Suppression"""
        border_score_point_100 = idola.get_top_100_raid_suppression_border()
        border_score_point_500 = idola.get_top_500_raid_suppression_border()
        border_score_point_1000 = idola.get_top_1000_raid_suppression_border()
        border_score_point_5000 = idola.get_top_5000_raid_suppression_border()

        current_time = idola.get_current_time()
        end_date = idola.get_raid_event_end_date()
        time_left = idola.datetime_difference(current_time, end_date)

        embed = discord.Embed(
            title="Idola Raid Suppression Border",
            color=discord.Colour.blue(),
        )
        embed.set_thumbnail(
            url="https://raw.githubusercontent.com/iXyk/IdolaBot/master/idola/lib/assets/raid.png"
        )
        embed.add_field(
            name="Top 100",
            value=f"{border_score_point_100:,d} points",
            inline=True,
        )
        embed.add_field(
            name="Top 500",
            value=f"{border_score_point_500:,d} points",
            inline=True,
        )
        embed.add_field(
            name="Top 1000",
            value=f"{border_score_point_1000:,d} points",
            inline=True,
        )
        embed.add_field(
            name="Top 5000",
            value=f"{border_score_point_5000:,d} points",
            inline=True,
        )
        embed.add_field(
            name="Time Left",
            value=time_left,
            inline=False
        )
        embed.add_field(
            name="Current Time",
            value=idola.datetime_jp_format(current_time),
            inline=True,
        )
        embed.add_field(
            name="Ending at",
            value=idola.datetime_jp_format(end_date),
            inline=True,
        )
        await ctx.send(embed=embed)

    @commands.command()
    async def creation_border(self, ctx):
        """Shows the border for Idola Raid Creation"""
        border_score_point_100 = idola.get_top_100_raid_creation_border()
        border_score_point_500 = idola.get_top_500_raid_creation_border()
        border_score_point_1000 = idola.get_top_1000_raid_creation_border()
        border_score_point_5000 = idola.get_top_5000_raid_creation_border()

        current_time = idola.get_current_time()
        end_date = idola.get_raid_event_end_date()
        time_left = idola.datetime_difference(current_time, end_date)

        embed = discord.Embed(
            title="Idola Raid Creation Border",
            color=discord.Colour.blue()
        )
        embed.set_thumbnail(url="https://raw.githubusercontent.com/iXyk/IdolaBot/master/idola/lib/assets/raid.png")
        embed.add_field(
            name="Top 100",
            value=f"{border_score_point_100:,d} points",
            inline=True,
        )
        embed.add_field(
            name="Top 500",
            value=f"{border_score_point_500:,d} points",
            inline=True,
        )
        embed.add_field(
            name="Top 1000",
            value=f"{border_score_point_1000:,d} points",
            inline=True,
        )
        embed.add_field(
            name="Top 5000",
            value=f"{border_score_point_5000:,d} points",
            inline=True,
        )
        embed.add_field(
            name="Time Left",
            value=time_left,
            inline=False
        )
        embed.add_field(
            name="Current Time",
            value=idola.datetime_jp_format(current_time),
            inline=True,
        )
        embed.add_field(
            name="Ending at",
            value=idola.datetime_jp_format(end_date),
            inline=True,
        )
        await ctx.send(embed=embed)

    @commands.command()
    async def arena_team(self, ctx, profile_id: int):
        """Shows the latest ranked arena team for a given profile_id"""
        arena_team = idola.get_arena_team_composition(profile_id)
        embed = discord.Embed(
            title=f"Team Score: {arena_team['team_score']:,d}",
            description=f"**Idomag**\nLaw: {arena_team['law_idomag']}\nChaos: {arena_team['chaos_idomag']}",
            color=discord.Colour.blue(),
        )
        embed.set_author(name=f"{arena_team['player_name']}")
        embed.set_thumbnail(url=arena_team["avatar_url"])

        embed.add_field(
            name="Law Characters",
            value=arena_team["law_characters"],
            inline=True,
        )
        embed.add_field(
            name="Weapon Symbols",
            value=arena_team["law_weapon_symbols"],
            inline=True,
        )
        embed.add_field(
            name="Soul Symbols",
            value=arena_team["law_soul_symbols"],
            inline=True,
        )
        embed.add_field(
            name="Chaos Characters",
            value=arena_team["chaos_characters"],
            inline=True,
        )
        embed.add_field(
            name="Weapon Symbols",
            value=arena_team["chaos_weapon_symbols"],
            inline=True,
        )
        embed.add_field(
            name="Soul Symbols",
            value=arena_team["chaos_soul_symbols"],
            inline=True,
        )
        embed.set_footer(text=78 * "\u200b")
        await ctx.send(embed=embed)

    @commands.command()
    async def arena_team_name(self, ctx, profile_name):
        """Shows the matching arena_team using their name if the profile_id has already been cached"""
        arena_team = idola.get_arena_team_composition_from_name(profile_name)
        if not arena_team:
            await ctx.send(
                "Could not find a player by that name in the cache, to update the cache run 'arena_team' using your profile id first"
            )
            return
        embed = discord.Embed(
            title=f"Team Score: {arena_team['team_score']:,d}",
            description=f"**Idomag**\nLaw: {arena_team['law_idomag']}\nChaos: {arena_team['chaos_idomag']}",
            color=discord.Colour.blue(),
        )
        embed.set_author(name=f"{arena_team['player_name']}")
        embed.set_thumbnail(url=arena_team["avatar_url"])

        embed.add_field(
            name="Law Characters",
            value=arena_team["law_characters"],
            inline=True,
        )
        embed.add_field(
            name="Weapon Symbols",
            value=arena_team["law_weapon_symbols"],
            inline=True,
        )
        embed.add_field(
            name="Soul Symbols",
            value=arena_team["law_soul_symbols"],
            inline=True,
        )
        embed.add_field(
            name="Chaos Characters",
            value=arena_team["chaos_characters"],
            inline=True,
        )
        embed.add_field(
            name="Weapon Symbols",
            value=arena_team["chaos_weapon_symbols"],
            inline=True,
        )
        embed.add_field(
            name="Soul Symbols",
            value=arena_team["chaos_soul_symbols"],
            inline=True,
        )
        embed.set_footer(text=78 * "\u200b")
        await ctx.send(embed=embed)

    @commands.command()
    async def arena_top_100(self, ctx):
        """Shows the Top 100 Arena players"""
        players = idola.show_arena_ranking_top_100_players()
        msg = []
        for profile_id, ranking_information in sorted(players.items(), key=lambda item: item[1]["arena_score_point"],):
            arena_score_rank = ranking_information["arena_score_rank"]
            arena_score_point = ranking_information["arena_score_point"]
            name = ranking_information["name"]
            msg.insert(
                0, f"{arena_score_rank}: {arena_score_point:,d} - {name}({profile_id})",
            )
        for j, chunks in enumerate([msg[i : i + 50] for i in range(0, len(msg), 50)]):
            text = "\n".join(chunks)
            embed = discord.Embed(
                title="Idola Arena Top 100" if j == 0 else "\u200b",
                description=f"```{text}```",
                color=discord.Colour.blue(),
            )
            await ctx.send(embed=embed)

    @commands.command()
    async def suppression_top_100(self, ctx):
        """Shows the Top 100 Idola Raid Suppression players"""
        msg = idola.show_raid_suppression_top_100_players()
        msg = msg.split("\n")
        for j, chunks in enumerate([msg[i : i + 50] for i in range(0, len(msg), 50)]):
            text = "\n".join(chunks)
            embed = discord.Embed(
                title="Idola Raid Suppression Top 100" if j == 0 else "\u200b",
                description=f"```{text}```",
                color=discord.Colour.blue(),
            )
            await ctx.send(embed=embed)

    @commands.command()
    async def creation_top_100(self, ctx):
        """Shows the Top 100 Idola Creation players"""
        msg = idola.show_raid_creation_top_100_players()
        msg = msg.split("\n")
        for j, chunks in enumerate([msg[i : i + 50] for i in range(0, len(msg), 50)]):
            text = "\n".join(chunks)
            embed = discord.Embed(
                title="Idola Raid Creation Top 100" if j == 0 else "\u200b",
                description=f"```{text}```",
                color=discord.Colour.blue(),
            )
            await ctx.send(embed=embed)


def setup(client):
    client.add_cog(IDOLA(client))
