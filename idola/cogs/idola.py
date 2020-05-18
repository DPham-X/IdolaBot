# -*- coding: utf-8 -*-
import os
import traceback

import discord
from discord.ext import commands, tasks

from lib.api import IdolaAPI
from lib.bumped import BumpedParser
from lib.web_visualiser import AfuureusIdolaStatusTool, NNSTJPWebVisualiser

IDOLA_USER_AGENT = os.getenv("IDOLA_USER_AGENT")
IDOLA_DEVICE_ID = os.getenv("IDOLA_DEVICE_ID")
IDOLA_DEVICE_TOKEN = os.getenv("IDOLA_DEVICE_TOKEN")
IDOLA_TOKEN_KEY = os.getenv("IDOLA_TOKEN_KEY")
IDOLA_UUID = os.getenv("IDOLA_UUID")

idola = IdolaAPI(
    IDOLA_USER_AGENT,
    IDOLA_DEVICE_ID,
    IDOLA_DEVICE_TOKEN,
    IDOLA_TOKEN_KEY,
    IDOLA_UUID,
)


class IDOLA(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.bumped_api = BumpedParser()

        self.border_fails = 0

        self.arena_border_50_channel = os.getenv("ARENA_BORDER_50_CHANNEL")
        self.arena_border_100_channel = os.getenv("ARENA_BORDER_100_CHANNEL")
        self.arena_border_500_channel = os.getenv("ARENA_BORDER_500_CHANNEL")
        self.arena_border_1000_channel = os.getenv("ARENA_BORDER_1000_CHANNEL")
        self.suppression_border_100_channel = os.getenv("SUPPRESSION_BORDER_100_CHANNEL")
        self.suppression_border_1000_channel = os.getenv("SUPPRESSION_BORDER_1000_CHANNEL")
        self.suppression_border_5000_channel = os.getenv("SUPPRESSION_BORDER_5000_CHANNEL")
        self.creation_border_100_channel = os.getenv("CREATION_BORDER_100_CHANNEL")
        self.creation_border_1000_channel = os.getenv("CREATION_BORDER_1000_CHANNEL")
        self.creation_border_5000_channel = os.getenv("CREATION_BORDER_5000_CHANNEL")

        self.border_message_channel = os.getenv("BORDER_MESSAGE_CHANNEL")

    async def send_embed_error(self, ctx, message):
        embed = discord.Embed(
            title="Error",
            description=f"{message}",
            color=discord.Colour.red(),
        )
        await ctx.send(embed=embed)

    async def send_embed_info(self, ctx, message):
        embed = discord.Embed(
            title="Info",
            description=f"{message}",
            color=discord.Colour.green(),
        )
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_ready(self):
        await self.client.change_presence(activity=discord.Game("Ready!"))
        for guild in self.client.guilds:
            print(f"{self.client.user} is connected to the following guild:\n" f"{guild.name}(id: {guild.id})")

        # Start looping tasks
        self.relog.start()
        self.border_status_update.start()
        self.border_channel_update.start()
        self.border_pinned_update.start()
        self.periodic_save.start()

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        traceback.print_exception(type(error), error, error.__traceback__)
        await self.send_embed_error(ctx, "An unexpected error occurred")

    @commands.command(hidden=True)
    @commands.is_owner()
    async def restart(self, ctx):
        try:
            idola.start()
            await self.send_embed_info(ctx, "IdolaBot has been restarted")
        except Exception as e:
            print(e, traceback.format_exc())
            await self.send_embed_error(ctx, "An error occurred, IdolaBot could not be restarted")

    @commands.command(hidden=True)
    @commands.is_owner()
    async def update_bumped(self, ctx):
        try:
            await self.send_embed_info(ctx, "Updating database from bumped website")
            await self.bumped_api.start()
            await self.send_embed_info(ctx, "Finished updating bumped database")
        except Exception as e:
            print(e, traceback.format_exc())
            await self.send_embed_error(ctx, "An error occurred whilst trying to update bumped database")

    @commands.command(hidden=True)
    @commands.is_owner()
    async def save_profiles(self, ctx):
        try:
            idola.save_profile_cache()
            idola.save_discord_profile_ids()
            await self.send_embed_info(ctx, "Profile cache saved")
        except Exception as e:
            print(traceback.format_exc())
            await self.send_embed_error(ctx, f"Could not save profile cache - {e}")

    @tasks.loop(hours=1)
    async def periodic_save(self):
        try:
            idola.save_profile_cache()
            idola.save_discord_profile_ids()
        except Exception as e:
            print(traceback.format_exc())

    @tasks.loop(seconds=60)
    async def border_status_update(self):
        try:
            border_score = idola.get_top_100_raid_suppression_border()
            print(f"{border_score:,d} - SuppressionBorderTop100")
            await self.client.change_presence(activity=discord.Game(f"{border_score:,d} - SuppressionBorderTop100"))
        except Exception as e:
            print(e, traceback.format_exc())

    @tasks.loop(hours=4)
    async def relog(self):
        print("Relogging")
        idola.start()

    @tasks.loop(seconds=180)
    async def border_pinned_update(self):
        try:
            if not self.border_message_channel:
                return

            channel = self.client.get_channel(int(self.border_message_channel))
            print(f"Updating pinned message in {channel.name}")
            pinned_messages = await channel.pins()
            border_message = None
            for pinned_message in pinned_messages:
                if pinned_message.author.id == self.client.user.id:
                    border_message = pinned_message
                    print(f"Updating existing pinned message with ID {border_message.id}")
                    break

            embed = discord.Embed(title="Idola Borders", color=discord.Colour.blue())

            #Arena
            border_score_point_100 = idola.get_top_100_arena_border()
            border_score_point_500 = idola.get_top_500_arena_border()
            border_score_point_1000 = idola.get_top_1000_arena_border()

            border_output=f"🥇100: {border_score_point_100:,d} points\n" if border_score_point_100 else "🥇100: Unknown\n"
            border_output+=f"🥇500: {border_score_point_500:,d} points\n" if border_score_point_500 else "🥇500: Unknown\n"
            border_output+=f"🥇1000: {border_score_point_1000:,d} points\n" if border_score_point_1000 else "🥇1000: Unknown\n"
            embed.add_field(name="Idola Arena Border", value=border_output, inline=False)

            #Suppression
            border_score_point_100 = idola.get_top_100_raid_suppression_border()
            border_score_point_500 = idola.get_top_500_raid_suppression_border()
            border_score_point_1000 = idola.get_top_1000_raid_suppression_border()
            border_score_point_5000 = idola.get_top_5000_raid_suppression_border()

            border_output=f"🥇100: {border_score_point_100:,d} points\n" if border_score_point_100 else "🥇100: Unknown\n"
            border_output+=f"🥇500: {border_score_point_500:,d} points\n" if border_score_point_500 else "🥇500: Unknown\n"
            border_output+=f"🥇1000: {border_score_point_1000:,d} points\n" if border_score_point_1000 else "🥇1000: Unknown\n"
            border_output+=f"🥇5000: {border_score_point_5000:,d} points\n" if border_score_point_5000 else "🥇5000: Unknown\n"
            embed.add_field(name="Idola Raid Suppression Border", value=border_output, inline=False)

            #Creation
            border_score_point_100 = idola.get_top_100_raid_creation_border()
            border_score_point_500 = idola.get_top_500_raid_creation_border()
            border_score_point_1000 = idola.get_top_1000_raid_creation_border()
            border_score_point_5000 = idola.get_top_5000_raid_creation_border()

            border_output=f"🥇100: {border_score_point_100:,d} points\n" if border_score_point_100 else "🥇100: Unknown\n"
            border_output+=f"🥇500: {border_score_point_500:,d} points\n" if border_score_point_500 else "🥇500: Unknown\n"
            border_output+=f"🥇1000: {border_score_point_1000:,d} points\n" if border_score_point_1000 else "🥇1000: Unknown\n"
            border_output+=f"🥇5000: {border_score_point_5000:,d} points\n" if border_score_point_5000 else "🥇5000: Unknown\n"
            embed.add_field(name="Idola Creation Border", value=border_output, inline=False)

            #Time
            current_time = idola.get_current_time()
            end_date = idola.get_raid_event_end_date()
            time_left = idola.datetime_difference(current_time, end_date)

            embed.add_field(name="Time Left", value=time_left, inline=False )
            embed.add_field(name="Current Time", value=idola.datetime_jp_format(current_time), inline=True)
            embed.add_field(name="Ending at", value=idola.datetime_jp_format(end_date), inline=True)

            if not border_message == None:
                await border_message.edit(embed=embed)
            else:
                border_message = await channel.send(embed=embed)
                await border_message.pin()
        except Exception as e:
            print(traceback.format_exc())

    @tasks.loop(seconds=120)
    async def border_channel_update(self):
        print("Updating channel borders")
        try:
            # Arena
            if self.arena_border_50_channel:
                arena_border_score_50 = idola.get_top_50_arena_border()
                channel = self.client.get_channel(int(self.arena_border_50_channel))
                await channel.edit(name=f"🏆50: {arena_border_score_50:,d}" if arena_border_score_50 else f"🏆50: Unknown")
            if self.arena_border_100_channel:
                arena_border_score_100 = idola.get_top_100_arena_border()
                channel = self.client.get_channel(int(self.arena_border_100_channel))
                await channel.edit(name=f"🥇100: {arena_border_score_100:,d}" if arena_border_score_100 else f"🥇100: Unknown")
            if self.arena_border_500_channel:
                arena_border_score_500 = idola.get_top_500_arena_border()
                channel = self.client.get_channel(int(self.arena_border_500_channel))
                await channel.edit(name=f"🥈500: {arena_border_score_500:,d}" if arena_border_score_500 else f"🥈500: Unknown")
            if self.arena_border_1000_channel:
                arena_border_score_1000 = idola.get_top_1000_arena_border()
                channel = self.client.get_channel(int(self.arena_border_1000_channel))
                await channel.edit(name=f"🥉1K: {arena_border_score_1000:,d}" if arena_border_score_1000 else f"🥉1K: Unknown")
            # Suppression
            if self.suppression_border_100_channel:
                raid_suppression_border_100 = idola.get_top_100_raid_suppression_border()
                channel = self.client.get_channel(int(self.suppression_border_100_channel))
                await channel.edit(name=f"🥇100: {raid_suppression_border_100:,d}" if raid_suppression_border_100 else f"🥇100: Unknown")
            if self.suppression_border_1000_channel:
                raid_suppression_border_1000 = idola.get_top_1000_raid_suppression_border()
                channel = self.client.get_channel(int(self.suppression_border_1000_channel))
                await channel.edit(name=f"🥈1K: {raid_suppression_border_1000:,d}" if raid_suppression_border_1000 else f"🥈1K: Unknown")
            if self.suppression_border_5000_channel:
                raid_suppression_border_5000 = idola.get_top_5000_raid_suppression_border()
                channel = self.client.get_channel(int(self.suppression_border_5000_channel))
                await channel.edit(name=f"🥉5K: {raid_suppression_border_5000:,d}" if raid_suppression_border_5000 else f"🥉5K: Unknown")
            # Creation
            if self.creation_border_100_channel:
                raid_creation_border_100 = idola.get_top_100_raid_creation_border()
                channel = self.client.get_channel(int(self.creation_border_100_channel))
                await channel.edit(name=f"🥇100: {raid_creation_border_100:,d}" if raid_creation_border_100 else f"🥇100: Unknown")
            if self.creation_border_1000_channel:
                raid_creation_border_1000 = idola.get_top_1000_raid_creation_border()
                channel = self.client.get_channel(int(self.creation_border_1000_channel))
                await channel.edit(name=f"🥈1K: {raid_creation_border_1000:,d}" if raid_creation_border_1000 else f"🥈1K: Unknown")
            if self.creation_border_5000_channel:
                raid_creation_border_5000 = idola.get_top_5000_raid_creation_border()
                channel = self.client.get_channel(int(self.creation_border_5000_channel))
                await channel.edit(name=f"🥉5K: {raid_creation_border_5000:,d}" if raid_creation_border_5000 else f"🥉5K: Unknown")
        except Exception as e:
            print(traceback.format_exc())

    @commands.command()
    async def arena_border(self, ctx):
        """Shows the border for arena"""
        border_score_point_50 = idola.get_top_50_arena_border()
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
            name="Top 50",
            value=f"{border_score_point_50:,d} points" if border_score_point_50 else "Unknown",
            inline=True,
        )
        embed.add_field(
            name="Top 100",
            value=f"{border_score_point_100:,d} points" if border_score_point_100 else "Unknown",
            inline=True,
        )
        embed.add_field(
            name="Top 500",
            value=f"{border_score_point_500:,d} points" if border_score_point_500 else "Unknown",
            inline=True,
        )
        embed.add_field(
            name="Top 1000",
            value=f"{border_score_point_1000:,d} points" if border_score_point_1000 else "Unknown",
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
        border_score_point_2000 = idola.get_top_2000_raid_suppression_border()
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
            value=f"{border_score_point_100:,d} points" if border_score_point_100 else "Unknown",
            inline=True,
        )
        embed.add_field(
            name="Top 500",
            value=f"{border_score_point_500:,d} points" if border_score_point_500 else "Unknown",
            inline=True,
        )
        embed.add_field(
            name="Top 1000",
            value=f"{border_score_point_1000:,d} points" if border_score_point_1000 else "Unknown",
            inline=True,
        )
        embed.add_field(
            name="Top 2000",
            value=f"{border_score_point_2000:,d} points" if border_score_point_2000 else "Unknown",
            inline=True,
        )
        embed.add_field(
            name="Top 5000",
            value=f"{border_score_point_5000:,d} points" if border_score_point_5000 else "Unknown",
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
        border_score_point_2000 = idola.get_top_2000_raid_creation_border()
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
            value=f"{border_score_point_100:,d} points" if border_score_point_100 else "Unknown",
            inline=True,
        )
        embed.add_field(
            name="Top 500",
            value=f"{border_score_point_500:,d} points" if border_score_point_500 else "Unknown",
            inline=True,
        )
        embed.add_field(
            name="Top 1000",
            value=f"{border_score_point_1000:,d} points" if border_score_point_1000 else "Unknown",
            inline=True,
        )
        embed.add_field(
            name="Top 2000",
            value=f"{border_score_point_2000:,d} points" if border_score_point_2000 else "Unknown",
            inline=True,
        )
        embed.add_field(
            name="Top 5000",
            value=f"{border_score_point_5000:,d} points" if border_score_point_5000 else "Unknown",
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
    async def register_profile(self, ctx, profile_id: int):
        """Register an idola profile_id to your discord profile"""
        discord_id = ctx.message.author.id
        if idola.register_discord_profile_id(discord_id, profile_id):
            await self.send_embed_info(ctx, "Successfully registered ID")
        else:
            await self.send_embed_error(ctx, "There was a problem registering your ID")

    @commands.command()
    async def arena_team(self, ctx, profile_id=None):
        """Shows the latest ranked arena team for a given profile_id"""
        if profile_id is None:
            discord_id = ctx.message.author.id
            profile_id = idola.get_profile_id_from_discord_id(int(discord_id))
            if profile_id is None:
                await self.send_embed_error(ctx, "Your arena_team has not been registered. Use `register_profile` to register your team. Or enter a profile id.")
                return

        try:
            arena_team = idola.get_arena_team_composition(int(profile_id))
        except KeyError:
            await self.send_embed_error(ctx, f"Unable to find the arena_team for profile id: '{profile_id}', ensure that it is correct.")
            return

        try:
            nnstjp_link = NNSTJPWebVisualiser.generate_shareable_link(arena_team["party_info"])
            nnstjp_formatted_link = f"NNSTJP: [{nnstjp_link}]({nnstjp_link})"
        except Exception as e:
            print(e, traceback.format_exc())
            nnstjp_formatted_link ="Unavailable"

        try:
            afuu_link = AfuureusIdolaStatusTool.generate_shareable_link(arena_team["party_info"])
            afuu_formatted_link = f"Afuureus: [{afuu_link}]({afuu_link})"
        except Exception as e:
            print(e, traceback.format_exc())
            afuu_formatted_link ="Unavailable"

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
        embed.add_field(
            name=78 * "\u200b",
            value=f"{nnstjp_formatted_link}\n{afuu_formatted_link}",
        )
        await ctx.send(embed=embed)

    @commands.command()
    async def arena_team_name(self, ctx, profile_name):
        """Shows the matching arena_team using their name if the profile_id has already been cached"""
        arena_team = idola.get_arena_team_composition_from_name(profile_name)
        if not arena_team:
            await self.send_embed_error(ctx,
                "Could not find a player by that name in the cache.\n"
                "To update the cache run '!arena_team' with your profile id first.\n"
                "To find a name that contains spaces use quotes around your profile name. (Eg. !arena_team_name \"<profile_name>\")"
            )
            return

        try:
            nnstjp_link = NNSTJPWebVisualiser.generate_shareable_link(arena_team["party_info"])
            nnstjp_formatted_link = f"NNSTJP: [{nnstjp_link}]({nnstjp_link})"
        except Exception as e:
            print(e, traceback.format_exc())
            nnstjp_formatted_link ="Unavailable"

        try:
            afuu_link = AfuureusIdolaStatusTool.generate_shareable_link(arena_team["party_info"])
            afuu_formatted_link = f"Afuureus: [{afuu_link}]({afuu_link})"
        except Exception as e:
            print(e, traceback.format_exc())
            afuu_formatted_link ="Unavailable"

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
        embed.add_field(
            name=78 * "\u200b",
            value=f"{nnstjp_formatted_link}\n{afuu_formatted_link}",
        )
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

    @commands.command()
    async def arena_roll(self, ctx, profile_id=None):
        """Shows what your next symbol roll will be using your arena team"""
        if profile_id is None:
            discord_id = ctx.message.author.id
            profile_id = idola.get_profile_id_from_discord_id(int(discord_id))
            if profile_id is None:
                await self.send_embed_error(ctx,
                    "Your arena_team has not been registered. Use `register_profile` to register your team. Or enter a profile id."
                )
                return
        player_name, char_option = idola.get_arena_next_options(int(profile_id))
        embed=discord.Embed(
            title=player_name,
            description="\u200b",
            color=discord.Colour.blue()
        )
        embed.set_author(name="Arena Roll")
        for char in char_option:
            embed.add_field(name="\u200b", value=f"__**{char['character_name']}**__", inline=False)
            embed.add_field(name=char["weapon_symbol"], value=char["weapon_next_option"], inline=False)
            embed.add_field(name=char["soul_symbol"], value=char["soul_next_option"], inline=False)
        await ctx.send(embed=embed)

    @commands.command()
    async def weapon(self, ctx, weapon_name: str):
        """Get Weapon Symbol information from Bumped"""
        weapon_name = self.bumped_api.get_unfuzzed_weapon_name(weapon_name)
        if not weapon_name:
            await self.send_embed_error(ctx, 'Could not find weapon in Bumped database')
            return
        weapon = self.bumped_api.weapon_symbols.get(weapon_name, None)
        embed=discord.Embed(
            title=f"{weapon.en_name} | {weapon.jp_name}",
            description=f"Closest match for '{weapon_name}'",
            color=discord.Colour.blue()
        )
        embed.set_thumbnail(url=weapon.icon_url)
        embed.add_field(name="Base Stats", value=weapon.base_stats, inline=True)
        embed.add_field(name="Arena/Raid Stats", value=weapon.arena_stats, inline=True)
        embed.add_field(name="Effect", value=weapon.effect, inline=False)
        embed.add_field(
            name=78 * "\u200b",
            value=f"[{weapon.url}]({weapon.url})",
        )
        await ctx.send(embed=embed)

    @commands.command()
    async def soul(self, ctx, soul_name: str):
        """Get Soul Symbol information from Bumped"""
        soul_name = self.bumped_api.get_unfuzzed_soul_name(soul_name)
        if not soul_name:
            await self.send_embed_error(ctx, 'Could not find soul in Bumped database')
            return
        soul = self.bumped_api.soul_symbols.get(soul_name, None)
        embed=discord.Embed(
            title=f"{soul.en_name} | {soul.jp_name}",
            description=f"Closest match for '{soul_name}'",
            color=discord.Colour.blue()
        )
        embed.set_thumbnail(url=soul.icon_url)
        embed.add_field(name="Base Stats", value=soul.base_stats, inline=True)
        if soul.arena_stats:
            embed.add_field(name="Arena/Raid Stats", value=soul.arena_stats, inline=True)
        else:
            embed.add_field(name="Requirements", value=soul.requirements, inline=True)
        embed.add_field(name="Effect", value=soul.effect, inline=False)
        embed.add_field(
            name=78 * "\u200b",
            value=f"[{soul.url}]({soul.url})",
        )
        await ctx.send(embed=embed)


def setup(client):
    client.add_cog(IDOLA(client))
