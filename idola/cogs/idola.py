# -*- coding: utf-8 -*-
import logging
import os
import traceback

import discord
from discord.ext import commands, tasks
from discord.ext.commands import has_permissions
from lib.api import IdolaAPI
from lib.bumped import BumpedParser
from lib.twitter_api import TwitterAPI
from lib.util import base_round
from lib.web_visualiser import AfuureusIdolaStatusTool, NNSTJPWebVisualiser

logger = logging.getLogger(f"idola.{__name__}")

IDOLA_USER_AGENT = os.getenv("IDOLA_USER_AGENT")
IDOLA_DEVICE_ID = os.getenv("IDOLA_DEVICE_ID")
IDOLA_DEVICE_TOKEN = os.getenv("IDOLA_DEVICE_TOKEN")
IDOLA_TOKEN_KEY = os.getenv("IDOLA_TOKEN_KEY")
IDOLA_UUID = os.getenv("IDOLA_UUID")

TWITTER_ACCESS_TOKEN_KEY = os.getenv("TWITTER_ACCESS_TOKEN_KEY")
TWITTER_ACCESS_TOKEN_SECRET = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
TWITTER_CONSUMER_KEY = os.getenv("TWITTER_CONSUMER_KEY")
TWITTER_CONSUMER_SECRET = os.getenv("TWITTER_CONSUMER_SECRET")

idola = IdolaAPI(
    IDOLA_USER_AGENT, IDOLA_DEVICE_ID, IDOLA_DEVICE_TOKEN, IDOLA_TOKEN_KEY, IDOLA_UUID,
)


class IDOLA(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.bumped_api = BumpedParser()
        self.twitter_api = None
        if (
            TWITTER_ACCESS_TOKEN_KEY
            and TWITTER_ACCESS_TOKEN_SECRET
            and TWITTER_ACCESS_TOKEN_SECRET
            and TWITTER_CONSUMER_SECRET
        ):
            self.twitter_api = TwitterAPI(
                access_token_key=TWITTER_ACCESS_TOKEN_KEY,
                access_token_secret=TWITTER_ACCESS_TOKEN_SECRET,
                consumer_key=TWITTER_CONSUMER_KEY,
                consumer_secret=TWITTER_CONSUMER_SECRET,
            )
        self.border_fails = 0

        self.arena_border_50_channel = os.getenv("ARENA_BORDER_50_CHANNEL")
        self.arena_border_100_channel = os.getenv("ARENA_BORDER_100_CHANNEL")
        self.arena_border_500_channel = os.getenv("ARENA_BORDER_500_CHANNEL")
        self.arena_border_1000_channel = os.getenv("ARENA_BORDER_1000_CHANNEL")
        self.suppression_border_100_channel = os.getenv(
            "SUPPRESSION_BORDER_100_CHANNEL"
        )
        self.suppression_border_1000_channel = os.getenv(
            "SUPPRESSION_BORDER_1000_CHANNEL"
        )
        self.suppression_border_5000_channel = os.getenv(
            "SUPPRESSION_BORDER_5000_CHANNEL"
        )
        self.creation_border_100_channel = os.getenv("CREATION_BORDER_100_CHANNEL")
        self.creation_border_1000_channel = os.getenv("CREATION_BORDER_1000_CHANNEL")
        self.creation_border_5000_channel = os.getenv("CREATION_BORDER_5000_CHANNEL")

        self.border_message_channel = os.getenv("BORDER_MESSAGE_CHANNEL")

        self.twitter_channel = os.getenv("IDOLA_TWITTER_CHANNEL")

    async def send_embed_error(self, ctx, message):
        embed = discord.Embed(
            title="Error", description=f"{message}", color=discord.Colour.red(),
        )
        logger.error(f"Sent error message: {message}")
        await ctx.send(embed=embed)

    async def send_embed_info(self, ctx, message):
        embed = discord.Embed(
            title="Info", description=f"{message}", color=discord.Colour.green(),
        )
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_ready(self):
        await self.client.change_presence(activity=discord.Game("Ready!"))
        for guild in self.client.guilds:
            logger.info(
                f"{self.client.user} is connected to the following guild:\n"
                f"{guild.name}(id: {guild.id})"
            )

        # Start looping tasks
        self.relog.start()
        self.border_status_update.start()
        self.border_channel_update.start()
        self.border_pinned_update.start()
        self.periodic_save.start()
        self.get_tweets.start()

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        exception_message = traceback.format_exception(
            type(error), error, error.__traceback__
        )
        logger.error("".join(exception_message))

        if isinstance(error, commands.errors.CommandNotFound):
            await self.send_embed_error(
                ctx,
                f"Unknown command. See {self.client.command_prefix}help to get the list of available commands",
            )
            return

        if isinstance(error, commands.UserInputError):
            await self.send_embed_error(ctx, "Invalid input")
            return

        if isinstance(error, commands.MissingPermissions):
            await self.send_embed_error(ctx, "You don't have permission to do that")
            return

        await self.send_embed_error(ctx, "An unexpected error occurred")

    @commands.command(hidden=True)
    @commands.is_owner()
    async def restart(self, ctx):
        try:
            idola.start()
            await self.send_embed_info(ctx, "IdolaBot has been restarted")
        except Exception as e:
            logger.exception(e)
            await self.send_embed_error(
                ctx, "An error occurred, IdolaBot could not be restarted"
            )

    @commands.command()
    @has_permissions(administrator=True)
    async def update_bumped(self, ctx):
        """[Admin] Refreshes Weapon and Soul Symbol information from Bumped database"""
        try:
            await self.send_embed_info(ctx, "Updating database from bumped website")
            await self.bumped_api.start()
            await self.send_embed_info(ctx, "Finished updating bumped database")
        except Exception as e:
            logger.exception(e)
            await self.send_embed_error(
                ctx, f"An error occurred whilst trying to update bumped database: {e}"
            )

    @commands.command(hidden=True)
    @commands.is_owner()
    async def save_profiles(self, ctx):
        try:
            idola.save_profile_cache()
            idola.save_discord_profile_ids()
            await self.send_embed_info(ctx, "Profile cache saved")
        except Exception as e:
            logger.exception(e)
            await self.send_embed_error(ctx, f"Could not save profile cache - {e}")

    @tasks.loop(hours=1)
    async def periodic_save(self):
        try:
            idola.save_profile_cache()
            idola.save_discord_profile_ids()
        except Exception as e:
            logger.exception(e)

    @tasks.loop(minutes=5)
    async def border_status_update(self):
        try:
            border_score = idola.get_top_100_raid_suppression_border()
            logger.info(f"{border_score:,d} - SuppressionBorderTop100")
            await self.client.change_presence(
                activity=discord.Game(f"{border_score:,d} - SuppressionBorderTop100")
            )
        except Exception as e:
            logger.exception(e)

    @tasks.loop(hours=4)
    async def relog(self):
        logger.info("Relogging")
        idola.start()

    @tasks.loop(minutes=5)
    async def get_tweets(self):
        try:
            await self._get_tweets()
        except Exception as e:
            logger.exception(e)

    async def _get_tweets(self):
        """ Gets tweets from @sega_idola"""
        if not self.twitter_api:
            return

        if not self.twitter_channel:
            logger.info(f"TWITTER_CHANNEL not defined")
            return

        logger.info("Getting tweets")
        tweets = self.twitter_api.get_tweets()
        channel = self.client.get_channel(int(self.twitter_channel))
        if not tweets:
            logger.info("No new tweets")
            return

        for tweet in tweets:
            embed = discord.Embed(
                title="\u200b",
                description=self.twitter_api.translate(tweet.full_text),
                color=discord.Colour.blue(),
            )
            embed.set_author(
                name=f"{tweet.user.name} (@{tweet.user.screen_name})",
                url=f"https://twitter.com/{tweet.user.screen_name}",
                icon_url=tweet.user.profile_image_url_https,
            )
            if tweet.media:
                image_url = tweet.media[0].media_url_https
                if image_url:
                    embed.set_image(url=image_url)
            if not tweet.retweeted_status:
                embed.add_field(name="Likes", value=tweet.favorite_count)
            else:
                embed.add_field(
                    name="Retweeted", value=tweet.retweet_count,
                )
            embed.set_footer(
                icon_url="https://images-ext-1.discordapp.net/external/bXJWV2Y_F3XSra_kEqIYXAAsI3m1meckfLhYuWzxIfI/https/abs.twimg.com/icons/apple-touch-icon-192x192.png",
                text="Twitter",
            )
            await channel.send(embed=embed)

    @tasks.loop(minutes=5)
    async def border_pinned_update(self):
        try:
            if not self.border_message_channel:
                return

            channel = self.client.get_channel(int(self.border_message_channel))
            logger.info(f"Updating pinned message in {channel.name}")
            pinned_messages = await channel.pins()
            border_message = None
            for pinned_message in pinned_messages:
                if pinned_message.author.id == self.client.user.id:
                    border_message = pinned_message
                    logger.info(
                        f"Updating existing pinned message with ID {border_message.id}"
                    )
                    break

            embed = discord.Embed(title="Idola Borders", color=discord.Colour.blue())

            # Arena
            border_score_point_100 = idola.get_top_100_arena_border()
            border_score_point_500 = idola.get_top_500_arena_border()
            border_score_point_1000 = idola.get_top_1000_arena_border()

            border_output = (
                f"🥇100: {border_score_point_100:,d} points\n"
                if border_score_point_100
                else "🥇100: Unknown\n"
            )
            border_output += (
                f"🥇500: {border_score_point_500:,d} points\n"
                if border_score_point_500
                else "🥇500: Unknown\n"
            )
            border_output += (
                f"🥇1000: {border_score_point_1000:,d} points\n"
                if border_score_point_1000
                else "🥇1000: Unknown\n"
            )
            embed.add_field(
                name="Idola Arena Border", value=border_output, inline=False
            )

            # Suppression
            border_score_point_100 = idola.get_top_100_raid_suppression_border()
            border_score_point_500 = idola.get_top_500_raid_suppression_border()
            border_score_point_1000 = idola.get_top_1000_raid_suppression_border()
            border_score_point_5000 = idola.get_top_5000_raid_suppression_border()

            border_output = (
                f"🥇100: {border_score_point_100:,d} points\n"
                if border_score_point_100
                else "🥇100: Unknown\n"
            )
            border_output += (
                f"🥇500: {border_score_point_500:,d} points\n"
                if border_score_point_500
                else "🥇500: Unknown\n"
            )
            border_output += (
                f"🥇1000: {border_score_point_1000:,d} points\n"
                if border_score_point_1000
                else "🥇1000: Unknown\n"
            )
            border_output += (
                f"🥇5000: {border_score_point_5000:,d} points\n"
                if border_score_point_5000
                else "🥇5000: Unknown\n"
            )
            embed.add_field(
                name="Idola Raid Suppression Border", value=border_output, inline=False
            )

            # Creation
            border_score_point_100 = idola.get_top_100_raid_creation_border()
            border_score_point_500 = idola.get_top_500_raid_creation_border()
            border_score_point_1000 = idola.get_top_1000_raid_creation_border()
            border_score_point_5000 = idola.get_top_5000_raid_creation_border()

            border_output = (
                f"🥇100: {border_score_point_100:,d} points\n"
                if border_score_point_100
                else "🥇100: Unknown\n"
            )
            border_output += (
                f"🥇500: {border_score_point_500:,d} points\n"
                if border_score_point_500
                else "🥇500: Unknown\n"
            )
            border_output += (
                f"🥇1000: {border_score_point_1000:,d} points\n"
                if border_score_point_1000
                else "🥇1000: Unknown\n"
            )
            border_output += (
                f"🥇5000: {border_score_point_5000:,d} points\n"
                if border_score_point_5000
                else "🥇5000: Unknown\n"
            )
            embed.add_field(
                name="Idola Creation Border", value=border_output, inline=False
            )

            # Time
            current_time = idola.get_current_time()
            end_date = idola.get_raid_event_end_date()
            time_left = idola.datetime_difference(current_time, end_date)

            embed.add_field(name="Time Left", value=time_left, inline=False)
            embed.add_field(
                name="Current Time",
                value=idola.datetime_jp_format(current_time),
                inline=True,
            )
            embed.add_field(
                name="Ending at", value=idola.datetime_jp_format(end_date), inline=True
            )

            if border_message is None:
                await border_message.edit(embed=embed)
            else:
                border_message = await channel.send(embed=embed)
                await border_message.pin()
        except Exception as e:
            logger.exception(e)

    @tasks.loop(minutes=5)
    async def border_channel_update(self):
        logger.info("Updating channel borders")
        try:
            # Arena
            if self.arena_border_50_channel:
                arena_border_score_50 = idola.get_top_50_arena_border()
                channel = self.client.get_channel(int(self.arena_border_50_channel))
                await channel.edit(
                    name=f"🏆50: {arena_border_score_50:,d}"
                    if arena_border_score_50
                    else f"🏆50: Unknown"
                )
            if self.arena_border_100_channel:
                arena_border_score_100 = idola.get_top_100_arena_border()
                channel = self.client.get_channel(int(self.arena_border_100_channel))
                await channel.edit(
                    name=f"🥇100: {arena_border_score_100:,d}"
                    if arena_border_score_100
                    else f"🥇100: Unknown"
                )
            if self.arena_border_500_channel:
                arena_border_score_500 = idola.get_top_500_arena_border()
                channel = self.client.get_channel(int(self.arena_border_500_channel))
                await channel.edit(
                    name=f"🥈500: {arena_border_score_500:,d}"
                    if arena_border_score_500
                    else f"🥈500: Unknown"
                )
            if self.arena_border_1000_channel:
                arena_border_score_1000 = idola.get_top_1000_arena_border()
                channel = self.client.get_channel(int(self.arena_border_1000_channel))
                await channel.edit(
                    name=f"🥉1K: {arena_border_score_1000:,d}"
                    if arena_border_score_1000
                    else f"🥉1K: Unknown"
                )
            # Suppression
            if self.suppression_border_100_channel:
                raid_suppression_border_100 = (
                    idola.get_top_100_raid_suppression_border()
                )
                channel = self.client.get_channel(
                    int(self.suppression_border_100_channel)
                )
                await channel.edit(
                    name=f"🥇100: {raid_suppression_border_100:,d}"
                    if raid_suppression_border_100
                    else f"🥇100: Unknown"
                )
            if self.suppression_border_1000_channel:
                raid_suppression_border_1000 = (
                    idola.get_top_1000_raid_suppression_border()
                )
                channel = self.client.get_channel(
                    int(self.suppression_border_1000_channel)
                )
                await channel.edit(
                    name=f"🥈1K: {raid_suppression_border_1000:,d}"
                    if raid_suppression_border_1000
                    else f"🥈1K: Unknown"
                )
            if self.suppression_border_5000_channel:
                raid_suppression_border_5000 = (
                    idola.get_top_5000_raid_suppression_border()
                )
                channel = self.client.get_channel(
                    int(self.suppression_border_5000_channel)
                )
                await channel.edit(
                    name=f"🥉5K: {raid_suppression_border_5000:,d}"
                    if raid_suppression_border_5000
                    else f"🥉5K: Unknown"
                )
            # Creation
            if self.creation_border_100_channel:
                raid_creation_border_100 = idola.get_top_100_raid_creation_border()
                channel = self.client.get_channel(int(self.creation_border_100_channel))
                await channel.edit(
                    name=f"🥇100: {raid_creation_border_100:,d}"
                    if raid_creation_border_100
                    else f"🥇100: Unknown"
                )
            if self.creation_border_1000_channel:
                raid_creation_border_1000 = idola.get_top_1000_raid_creation_border()
                channel = self.client.get_channel(
                    int(self.creation_border_1000_channel)
                )
                await channel.edit(
                    name=f"🥈1K: {raid_creation_border_1000:,d}"
                    if raid_creation_border_1000
                    else f"🥈1K: Unknown"
                )
            if self.creation_border_5000_channel:
                raid_creation_border_5000 = idola.get_top_5000_raid_creation_border()
                channel = self.client.get_channel(
                    int(self.creation_border_5000_channel)
                )
                await channel.edit(
                    name=f"🥉5K: {raid_creation_border_5000:,d}"
                    if raid_creation_border_5000
                    else f"🥉5K: Unknown"
                )
        except Exception as e:
            logger.exception(e)

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

        embed = discord.Embed(title="Idola Arena Border", color=discord.Colour.blue(),)
        embed.set_thumbnail(
            url="https://raw.githubusercontent.com/iXyk/IdolaBot/master/idola/lib/assets/arena.png"
        )
        embed.add_field(
            name="Top 50",
            value=f"{border_score_point_50:,d} points"
            if border_score_point_50
            else "Unknown",
            inline=True,
        )
        embed.add_field(
            name="Top 100",
            value=f"{border_score_point_100:,d} points"
            if border_score_point_100
            else "Unknown",
            inline=True,
        )
        embed.add_field(
            name="Top 500",
            value=f"{border_score_point_500:,d} points"
            if border_score_point_500
            else "Unknown",
            inline=True,
        )
        embed.add_field(
            name="Top 1000",
            value=f"{border_score_point_1000:,d} points"
            if border_score_point_1000
            else "Unknown",
            inline=True,
        )
        embed.add_field(name="Time Left", value=time_left, inline=False)
        embed.add_field(
            name="Current Time",
            value=idola.datetime_jp_format(current_time),
            inline=True,
        )
        embed.add_field(
            name="Ending at", value=idola.datetime_jp_format(end_date), inline=True,
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
            title="Idola Raid Suppression Border", color=discord.Colour.blue(),
        )
        embed.set_thumbnail(
            url="https://raw.githubusercontent.com/iXyk/IdolaBot/master/idola/lib/assets/raid.png"
        )
        embed.add_field(
            name="Top 100",
            value=f"{border_score_point_100:,d} points"
            if border_score_point_100
            else "Unknown",
            inline=True,
        )
        embed.add_field(
            name="Top 500",
            value=f"{border_score_point_500:,d} points"
            if border_score_point_500
            else "Unknown",
            inline=True,
        )
        embed.add_field(
            name="Top 1000",
            value=f"{border_score_point_1000:,d} points"
            if border_score_point_1000
            else "Unknown",
            inline=True,
        )
        embed.add_field(
            name="Top 2000",
            value=f"{border_score_point_2000:,d} points"
            if border_score_point_2000
            else "Unknown",
            inline=True,
        )
        embed.add_field(
            name="Top 5000",
            value=f"{border_score_point_5000:,d} points"
            if border_score_point_5000
            else "Unknown",
            inline=True,
        )
        embed.add_field(name="Time Left", value=time_left, inline=False)
        embed.add_field(
            name="Current Time",
            value=idola.datetime_jp_format(current_time),
            inline=True,
        )
        embed.add_field(
            name="Ending at", value=idola.datetime_jp_format(end_date), inline=True,
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
            title="Idola Raid Creation Border", color=discord.Colour.blue()
        )
        embed.set_thumbnail(
            url="https://raw.githubusercontent.com/iXyk/IdolaBot/master/idola/lib/assets/raid.png"
        )
        embed.add_field(
            name="Top 100",
            value=f"{border_score_point_100:,d} points"
            if border_score_point_100
            else "Unknown",
            inline=True,
        )
        embed.add_field(
            name="Top 500",
            value=f"{border_score_point_500:,d} points"
            if border_score_point_500
            else "Unknown",
            inline=True,
        )
        embed.add_field(
            name="Top 1000",
            value=f"{border_score_point_1000:,d} points"
            if border_score_point_1000
            else "Unknown",
            inline=True,
        )
        embed.add_field(
            name="Top 2000",
            value=f"{border_score_point_2000:,d} points"
            if border_score_point_2000
            else "Unknown",
            inline=True,
        )
        embed.add_field(
            name="Top 5000",
            value=f"{border_score_point_5000:,d} points"
            if border_score_point_5000
            else "Unknown",
            inline=True,
        )
        embed.add_field(name="Time Left", value=time_left, inline=False)
        embed.add_field(
            name="Current Time",
            value=idola.datetime_jp_format(current_time),
            inline=True,
        )
        embed.add_field(
            name="Ending at", value=idola.datetime_jp_format(end_date), inline=True,
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
    async def arena_team(self, ctx, arena_id=None):
        """Shows the latest ranked arena team for a given profile_id/profile_name"""
        if arena_id is None:
            discord_id = ctx.message.author.id
            arena_id = idola.get_profile_id_from_discord_id(int(discord_id))
            if arena_id is None:
                await self.send_embed_error(
                    ctx,
                    "Your arena_team has not been registered. Use `register_profile` to register your team. Or enter a profile id.",
                )
                return

        arena_team = None
        try:
            arena_team = idola.get_arena_team_composition_from_name(str(arena_id))
        except KeyError:
            pass

        if not arena_team:
            try:
                arena_team = idola.get_arena_team_composition(int(arena_id))
            except (KeyError, ValueError):
                pass

        if not arena_team:
            await self.send_embed_error(
                ctx,
                "Could not find a player by that name.\n"
                "To update the cache run '!arena_team' with your profile id first.\n"
                'To find a name that contains spaces use quotes around your profile name. (Eg. !arena_team "<profile_name>")\n'
                "Note: Profile names are CASE-SENSITIVE",
            )
            return

        try:
            nnstjp_link = NNSTJPWebVisualiser.generate_shareable_link(
                arena_team["party_info"]
            )
            nnstjp_formatted_link = f"NNSTJP: [{nnstjp_link}]({nnstjp_link})"
        except Exception as e:
            logger.exception(e)
            nnstjp_formatted_link = "Unavailable"

        embed = discord.Embed(
            title=f"Team Score: {arena_team['team_score']:,d}",
            description=f"**Idomag**\nLaw: {arena_team['law_idomag']}\nChaos: {arena_team['chaos_idomag']}",
            color=discord.Colour.blue(),
        )
        embed.set_author(name=f"{arena_team['player_name']}")
        embed.set_thumbnail(url=arena_team["avatar_url"])

        embed.add_field(
            name="Law Characters", value=arena_team["law_characters"], inline=True,
        )
        embed.add_field(
            name="Weapon Symbols", value=arena_team["law_weapon_symbols"], inline=True,
        )
        embed.add_field(
            name="Soul Symbols", value=arena_team["law_soul_symbols"], inline=True,
        )
        embed.add_field(
            name="Chaos Characters", value=arena_team["chaos_characters"], inline=True,
        )
        embed.add_field(
            name="Weapon Symbols",
            value=arena_team["chaos_weapon_symbols"],
            inline=True,
        )
        embed.add_field(
            name="Soul Symbols", value=arena_team["chaos_soul_symbols"], inline=True,
        )
        embed.add_field(
            name=78 * "\u200b", value=f"{nnstjp_formatted_link}\n",
        )
        await ctx.send(embed=embed)

    @commands.command()
    async def arena_top_100(self, ctx):
        """Shows the Top 100 Arena players"""
        players = idola.show_arena_ranking_top_100_players()
        msg = []
        for profile_id, ranking_information in sorted(
            players.items(), key=lambda item: item[1]["arena_score_point"],
        ):
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

    @commands.command(aliases=["brigade_top_100"])
    async def guild_top_100(self, ctx):
        """Show the Top 100 brigade"""
        msg = idola.show_top_100_guilds()
        msg = msg.split("\n")
        for j, chunks in enumerate([msg[i : i + 50] for i in range(0, len(msg), 50)]):
            text = "\n".join(chunks)
            embed = discord.Embed(
                title="Idola Brigade Battle Top 100" if j == 0 else "\u200b",
                description=f"```{text}```",
                color=discord.Colour.blue(),
            )
            await ctx.send(embed=embed)

    @commands.command(aliases=["brigade_by_range"])
    async def guild_by_range(self, ctx, start: int, end: int):
        """Show top brigades in the leaderboards by range"""
        round_start = base_round(int(start), base=20)
        rounded_end = base_round(int(end), base=20)
        msg = idola.show_top_guilds_by_range(round_start, rounded_end)
        msg = msg.split("\n")
        for j, chunks in enumerate([msg[i : i + 50] for i in range(0, len(msg), 50)]):
            text = "\n".join(chunks)
            embed = discord.Embed(
                title=f"Idola Brigade Battle {start} to {end}" if j == 0 else "\u200b",
                description=f"```{text}```",
                color=discord.Colour.blue(),
            )
            await ctx.send(embed=embed)

    @commands.command(aliases=["guild_info", "brigade", "brigade_info"])
    async def guild(self, ctx, guild_id: int):
        """Shows brigade information"""
        guild_info = idola.get_guild_info(guild_id)
        guild_memberlist = idola.get_guild_memberlist(guild_id)

        arena_top_500 = idola.show_arena_ranking_top_500_players()

        guild_memberlist_msg = "```"
        for guild_member in guild_memberlist:
            user_name = guild_member["user_name"]
            user_rank = guild_member["user_rank"]
            user_id = guild_member["user_id"]

            arena_rank_text = ""
            arena_rank = 0
            if user_id in arena_top_500:
                arena_rank = arena_top_500.get(user_id, {}).get("arena_score_rank", "")
                arena_rank_text = f"A:{arena_rank}"

            guild_memberlist_msg += f"{user_rank:0>3}: {user_name}({user_id}) "
            if arena_rank:
                guild_memberlist_msg += arena_rank_text
            guild_memberlist_msg += "\n"
        guild_memberlist_msg += "```"

        embed = discord.Embed(
            title=guild_info["guild_name"],
            description=guild_info["introduction"],
            color=discord.Colour.blue(),
        )
        embed.add_field(
            name="Leader", value=guild_info["leader_user_name"], inline=True
        )
        embed.add_field(name="Display ID", value=guild_info["display_id"], inline=True)
        embed.add_field(name="Members", value=guild_info["membership"], inline=True)
        embed.add_field(
            name="est",
            value=idola.datetime_jp_format(
                idola.epoch_to_datetime(guild_info["established_at"])
            ),
            inline=True,
        )
        embed.add_field(name="MemberList", value=guild_memberlist_msg, inline=False)
        await ctx.send(embed=embed)

    @commands.command(aliases=["find_brigade_by_name"])
    async def find_guild_by_name(self, ctx, guild_name):
        """Search for open brigades by their brigade name"""
        guild_search_result = idola.get_guild_from_guild_name(guild_name)
        if not guild_search_result:
            await self.send_embed_error(
                ctx, "Could not find brigade by that name, they may be full"
            )
            return
        message = []
        for i, guild in enumerate(guild_search_result[:10]):
            message.append(
                f"{i+1:0>2}: {guild['guild_name']} | DisplayID: {guild['display_id']} | GuildID: {guild['guild_id']}"
            )

        embed = discord.Embed(
            title="Search results..",
            description=f"Searching for '{guild_name}'",
            color=discord.Colour.green(),
        )
        embed.add_field(
            name="Found the following guilds..", value="\n".join(message),
        )
        await ctx.send(embed=embed)

    @commands.command(aliases=["find_brigade_by_id"])
    async def find_guild_by_id(self, ctx, display_id):
        """Search for open brigades by their Display ID"""
        guild_search_result = idola.get_guild_id_from_display_id(display_id)
        if not guild_search_result:
            await self.send_embed_error(
                ctx, "Could not find brigade by that name, they may be full"
            )
            return
        message = []
        for i, guild in enumerate(guild_search_result[:10]):
            message.append(
                f"{i+1:0>2}: {guild['guild_name']} | DisplayID: {guild['display_id']} | GuildID: {guild['guild_id']}"
            )

        embed = discord.Embed(
            title="Search results..",
            description=f"Searching for '{display_id}'",
            color=discord.Colour.green(),
        )
        embed.add_field(
            name="Found the following guilds..", value="\n".join(message),
        )
        await ctx.send(embed=embed)

    @commands.command()
    async def arena_roll(self, ctx, profile_id=None):
        """Shows what your next symbol roll will be using your arena team"""
        if profile_id is None:
            discord_id = ctx.message.author.id
            profile_id = idola.get_profile_id_from_discord_id(int(discord_id))
            if profile_id is None:
                await self.send_embed_error(
                    ctx,
                    "Your arena_team has not been registered. Use `register_profile` to register your team. Or enter a profile id.",
                )
                return
        player_name, char_option = idola.get_arena_next_options(int(profile_id))
        embed = discord.Embed(
            title=player_name, description="\u200b", color=discord.Colour.blue()
        )
        embed.set_author(name="Arena Roll")
        for char in char_option:
            embed.add_field(
                name="\u200b", value=f"__**{char['character_name']}**__", inline=False
            )
            embed.add_field(
                name=char["weapon_symbol"],
                value=char["weapon_next_option"],
                inline=False,
            )
            embed.add_field(
                name=char["soul_symbol"], value=char["soul_next_option"], inline=False
            )
        await ctx.send(embed=embed)

    @commands.command()
    async def weapon(self, ctx, *args):
        """Get Weapon Symbol information from Bumped"""
        input_weapon_name = " ".join(args)
        weapon_name = self.bumped_api.get_unfuzzed_weapon_name(input_weapon_name)
        if not weapon_name:
            await self.send_embed_error(ctx, "Could not find weapon in Bumped database")
            return
        weapon = self.bumped_api.weapon_symbols.get(weapon_name, None)
        embed = discord.Embed(
            title=f"{weapon.en_name} | {weapon.jp_name}",
            description=f"Closest match for '{input_weapon_name}'",
            color=discord.Colour.blue(),
        )
        embed.set_thumbnail(url=weapon.icon_url)
        embed.add_field(name="Base Stats", value=weapon.base_stats, inline=True)
        embed.add_field(name="Arena/Raid Stats", value=weapon.arena_stats, inline=True)
        embed.add_field(name="Effect", value=weapon.effect, inline=False)
        embed.add_field(
            name=78 * "\u200b", value=f"[{weapon.url}]({weapon.url})",
        )
        await ctx.send(embed=embed)

    @commands.command()
    async def soul(self, ctx, *args):
        """Get Soul Symbol information from Bumped"""
        input_soul_name = " ".join(args)
        soul_name = self.bumped_api.get_unfuzzed_soul_name(input_soul_name)
        if not soul_name:
            await self.send_embed_error(ctx, "Could not find soul in Bumped database")
            return
        soul = self.bumped_api.soul_symbols.get(soul_name, None)
        embed = discord.Embed(
            title=f"{soul.en_name} | {soul.jp_name}",
            description=f"Closest match for '{input_soul_name}'",
            color=discord.Colour.blue(),
        )
        embed.set_thumbnail(url=soul.icon_url)
        embed.add_field(name="Base Stats", value=soul.base_stats, inline=True)
        if soul.arena_stats:
            embed.add_field(
                name="Arena/Raid Stats", value=soul.arena_stats, inline=True
            )
        else:
            embed.add_field(name="Requirements", value=soul.requirements, inline=True)
        embed.add_field(name="Effect", value=soul.effect, inline=False)
        embed.add_field(
            name=78 * "\u200b", value=f"[{soul.url}]({soul.url})",
        )
        await ctx.send(embed=embed)


def setup(client):
    client.add_cog(IDOLA(client))
