import disnake
from disnake.ext import commands
from disnake import ButtonStyle, Button, ui,Color
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import requests
from bs4 import BeautifulSoup
import re
import math
import yt_dlp as youtube_dl
import asyncio
import datetime
import psutil
import platform
from disnake.utils import get
from disnake import MessageInteraction, InteractionResponseType
import discord
from discord import VoiceChannel
import time
from collections import deque
from bot.config import TOKEN, SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET
from disnake.ui import View, Button
from typing import Optional
import aiohttp
from disnake import Embed
from collections import deque
import googleapiclient.discovery
import os
from disnake import Option
from discord.ext import tasks
from bot.utils.colors import color_map
from disnake.app_commands import OptionType
from collections import defaultdict
import matplotlib.pyplot as plt
import io
from collections import defaultdict
import numpy as np
import seaborn as sns
import json
import random
from bot.utils.welcome import WELCOME_MESSAGES
import logging
from disnake import Option,OptionType, ApplicationCommandInteraction
from random import choice
import textwrap
from collections import defaultdict
import uuid
from bot.utils.prizes import prizes
from disnake import TextChannel
import logging



user_preferences = {}
# Store the currently playing song for each guild
global currently_playing
players = {}
currently_playing = {}
queues = {}
playercontrols = {}
paused_songs = {}
page_data = {}
skip_request = {}
users_played_before = {}
# Global variable for data
data = {}

bot = commands.Bot(command_prefix='/', intents=disnake.Intents.all(), help_command=None)

start_time = datetime.datetime.utcnow()
class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get('title')
        self.url = data.get('url')

# Event that triggers when the bot is ready
@bot.event
async def on_ready():
    print(f"Bot is ready: {bot.user.name}")
    funny_status = "/help | Report any Issues to @daddylad"
    truncated_status = (funny_status[:46] + "...") if len(funny_status) > 49 else funny_status
    await bot.change_presence(activity=disnake.Activity(type=disnake.ActivityType.listening, name=truncated_status))


# Function to get the command signature for a given command
def get_command_signature(command: commands.Command):
    return f'/{command.name} {command.signature}'

# Slash command to show available commands
@bot.slash_command(name="help", description="Show available commands")
async def _help(inter):
    utility_commands = [
        ("/clear", "Clear all messages in the chat"),
        ("/join", "Join the voice channel"),
        ("/info", "Show bot information"),
        ("/ping", "Check the bot's latency"),
        ("/clear_chat", "Clear all messages in text chat and bot dissconnects"),
        ("/avatar", "Show user's avatar"),
        ("/color", "Change the color of a role"),
        ("/pollsetup", "Set up a poll"),
        ("/userinfo", "Show information about a user")
    ]

    bot_utility = [
        ("/setup_role", "Setup a role Reaction"),
        ("/setup_serverstats", "Setup server statistics"),
        ("/setup_commit", "Set up the bot to check for new commits every 5 minutes"),
    ]
    
    voice_commands = [
        ("/Move", "Move users in a voice channel to another voice channel"),
        ("/mute", "Mute a user in voice chat"),
        ("/unmute", "Unmute a user in voice chat")
    ]

    moderation_commands = [
        ("/ban", "Ban a user from the server"),
        ("/kick", "Kick a user from the server")
    ]

    github_commands = [
        ("/getcommits", "Get the latest commits from a GitHub repo")
    ]

    giveaway_commands = [
        ("/giveaway", "Start a giveaway")
    ]


    embed = disnake.Embed(title="Help", description="List of available commands", color=disnake.Color.blue())

    embed.add_field(name="\u200b\nUtility Commands:", value="\u200b", inline=False)
    for name, value in utility_commands:
        embed.add_field(name=name, value=value, inline=False)

    embed.add_field(name="\u200b\nBot Utility Commands:", value="\u200b", inline=False)
    for name, value in bot_utility:
        embed.add_field(name=name, value=value, inline=False)

    embed.add_field(name="\u200b\nVoice Commands:", value="\u200b", inline=False)
    for name, value in voice_commands:
        embed.add_field(name=name, value=value, inline=False)

    embed.add_field(name="\u200b\nModeration Commands:", value="\u200b", inline=False)
    for name, value in moderation_commands:
        embed.add_field(name=name, value=value, inline=False)

    embed.add_field(name="\u200b\nGitHub Commands:", value="\u200b", inline=False)
    for name, value in github_commands:
        embed.add_field(name=name, value=value, inline=False)

    embed.add_field(name="\u200b\nGiveaway Commands:", value="\u200b", inline=False)
    for name, value in giveaway_commands:
        embed.add_field(name=name, value=value, inline=False)

    await inter.response.send_message(embed=embed)

    # Add a blank field to separate the commands from the footer
    embed.add_field(name="\u200b", value="\u200b", inline=False)
    embed.set_footer(text="Made with ❤️ by Parth")
    embed.add_field(name="Support Me", value="[Buy Me a Coffee](https://www.buymeacoffee.com/parthlad)", inline=False)
    embed.add_field(name="Your support means the world to me! ❤️", value="\u200b")
  
    # Send the embed as a response
    await inter.response.send_message(embed=embed)


async def clear_messages(channel):
    await channel.purge(limit=100)

@bot.slash_command(name="clear", description="Clear all messages in the chat")
async def _clear(inter):
    await clear_messages(inter.channel)
    await inter.response.send_message("Cleared all messages in the chat.", ephemeral=True)


@bot.slash_command(name="ping", description="Check the bot's latency")
async def ping(inter):
    ping_value = round(bot.latency * 1000)

    # Create the embed
    embed = disnake.Embed(title="Pong! :ping_pong:", color=disnake.Color.green())
    embed.add_field(name="Latency", value=f"{ping_value}ms", inline=False)

    # Send the embed as a response
    await inter.response.send_message(embed=embed)


@bot.slash_command(name="info", description="Show bot information")
async def show_info(inter):
    bot_name = bot.user.name
    api_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    uptime = datetime.datetime.utcnow() - start_time
    uptime_str = str(uptime).split(".")[0]
    bot_stats = f"Bot Name: {bot_name}\nAPI Time: {api_time}\nRuntime: {uptime_str}"

    cpu_usage = psutil.cpu_percent()
    memory_usage = psutil.virtual_memory().percent
    system_stats = f"OS: {platform.system()}\nUptime: {uptime}\nRAM: {memory_usage} MB"

    # Calculate ping value
    ping_value = round(bot.latency * 1000)

    # Create the embed
    embed = disnake.Embed(title="The Gaming Parlor Bot (/) Information", color=disnake.Color.blue())


    # Add bot stats information
    bot_stats_box = f"```\n{bot_stats}\n```"
    embed.add_field(name="Bot Stats", value=bot_stats_box, inline=False)

    # Add ping information
    ping_box = f"```\nPing: {ping_value}ms\n```"
    embed.add_field(name="Ping", value=ping_box, inline=False)

    # Add system stats information
    system_stats_box = f"```\n{system_stats}\n```"
    embed.add_field(name="System Stats", value=system_stats_box, inline=False)

    # Set the footer with library information
   # Add a blank field to separate the commands from the footer
    embed.add_field(name="\u200b", value="\u200b", inline=False)
    embed.set_footer(text="Made with ❤️ by Parth")
    embed.add_field(name="Support Me", value="[Buy Me a Coffee](https://www.buymeacoffee.com/parthlad)", inline=False)
    embed.add_field(name="Your support means the world to me! ❤️", value="\u200b")
    # Send the embed as a response
    await inter.response.send_message(embed=embed)


# Drag Members to Different Voice Channel
@bot.slash_command(name="move", description="Move specific users in a voice channel to another voice channel")
async def drag_users(inter, from_channel: disnake.VoiceChannel, to_channel: disnake.VoiceChannel, members: str):
    await inter.response.defer()  # Add a deferral to the response

    member_mentions = re.findall(r"<@!?(\d+)>", members)
    members_to_drag = []
    for member in from_channel.members:
        if str(member.id) in member_mentions:
            members_to_drag.append(member)
    if str(inter.author.id) in member_mentions:
        members_to_drag.append(inter.author)  # Add author of command to members to drag
    elif not members_to_drag:
        await inter.edit_original_message(content="No valid member mentions were provided or no members found in the specified voice channel.")  # Edit the deferred response
        return

    for member in members_to_drag:
        try:
            await member.move_to(to_channel)
        except disnake.HTTPException as e:
            if e.status == 429:
                # If rate limited, wait for the specified time before trying again
                await asyncio.sleep(int(e.headers["Retry-After"]))
                await member.move_to(to_channel)
            else:
                raise e
        await asyncio.sleep(1)  # Add a 1-second delay between commands
    await inter.edit_original_message(content=f"Moved  members.")  # Edit the deferred response

@bot.slash_command(name="clear_chat", description="Clear all messages in the chat and disconnect the bot")
async def clear_chat(inter):
    await inter.response.defer()
    channel = inter.channel

    # Delete all messages in the channel
    await channel.purge()

    # Check if the bot is connected to a voice channel
    voice_client = get(bot.voice_clients, guild=inter.guild)
    if voice_client and voice_client.is_connected():
        # Disconnect the bot
        await voice_client.disconnect()

    # Send a response message indicating the chat has been cleared
    await inter.edit_original_message(content="Chat cleared and bot disconnected.")

# Server stats
server_stats_settings = {}

@bot.slash_command(
    name="setup_serverstats",
    description="Set up server stats"
)
async def setup_serverstats(ctx: disnake.ApplicationCommandInteraction):
    server_id = ctx.guild.id

    # Check if the server has already been set up
    if server_id in server_stats_settings:
        await ctx.send("Server stats are already set up for this server.")
        return

    # Prompt the user for the desired settings
    await ctx.send("Let's set up the server stats display.")
    await ctx.send("Please select your preference for server stats:\n1. Voice Chat\n2. Text Chat")

    def check(message):
        return message.author.id == ctx.author.id and message.channel.id == ctx.channel.id

    try:
        preference_message = await bot.wait_for('message', timeout=60.0, check=check)
    except asyncio.TimeoutError:
        await ctx.send("Timeout. Please try again.")
        return

    preference = preference_message.content.lower()

    if preference not in ['1', '2']:
        await ctx.send("Invalid preference. Please select either '1' or '2'.")
        return

    # Create new channels based on the preference
    member_channel = None
    bot_channel = None
    total_channel = None
    category = None
    if preference == '1':
        # Voice Chat
        category = await ctx.guild.create_category("📊 ▬ SERVER STATS ▬ 📊")
        member_channel = await ctx.guild.create_voice_channel(f"Members-{ctx.guild.member_count}", category=category)
        bot_channel = await ctx.guild.create_voice_channel(f"Bots-{sum(member.bot for member in ctx.guild.members)}", category=category)
        total_channel = await ctx.guild.create_voice_channel(f"Total-{ctx.guild.member_count + sum(member.bot for member in ctx.guild.members)}", category=category)
    elif preference == '2':
        # Text Chat
        category = await ctx.guild.create_category("📊 ▬ SERVER STATS ▬ 📊")
        member_channel = await ctx.guild.create_text_channel(f"Members-{ctx.guild.member_count}", category=category)
        bot_channel = await ctx.guild.create_text_channel(f"Bots-{sum(member.bot for member in ctx.guild.members)}", category=category)
        total_channel = await ctx.guild.create_text_channel(f"Total-{ctx.guild.member_count + sum(member.bot for member in ctx.guild.members)}", category=category)

    if not member_channel or not bot_channel or not total_channel:
        await ctx.send("Failed to create the channels. Please make sure the bot has the required permissions.")
        return

    # Set channel permissions to lock them
    overwrites = {
        ctx.guild.default_role: disnake.PermissionOverwrite(connect=False)  # Lock the channels
    }
    await member_channel.edit(overwrites=overwrites)
    await bot_channel.edit(overwrites=overwrites)
    await total_channel.edit(overwrites=overwrites)

    # Store the server stats settings
    server_stats_settings[server_id] = {
        'category_id': category.id,
        'member_channel_id': member_channel.id,
        'bot_channel_id': bot_channel.id,
        'total_channel_id': total_channel.id
    }


    await ctx.send(f"Server stats have been set up successfully. Channels created: {member_channel.mention}, {bot_channel.mention}, {total_channel.mention}")

@bot.event
async def on_member_join(member):
    guild = member.guild
    server_id = guild.id

    if server_id in server_stats_settings:
        category_id = server_stats_settings[server_id]['category_id']
        member_channel_id = server_stats_settings[server_id]['member_channel_id']
        bot_channel_id = server_stats_settings[server_id]['bot_channel_id']
        total_channel_id = server_stats_settings[server_id]['total_channel_id']

        category = guild.get_channel(category_id)
        member_channel = guild.get_channel(member_channel_id)
        bot_channel = guild.get_channel(bot_channel_id)
        total_channel = guild.get_channel(total_channel_id)

        if member_channel and bot_channel and total_channel and category:
            member_count = guild.member_count
            bot_count = sum(member.bot for member in guild.members)
            total_count = member_count + bot_count

            # Edit the channel names with the updated counts
            await member_channel.edit(name=f"Members-{member_count}")
            await bot_channel.edit(name=f"Bots-{bot_count}")
            await total_channel.edit(name=f"Total-{total_count}")

            member_embed = disnake.Embed(title="Member Count", color=disnake.Color.blurple())
            member_embed.add_field(name="Count", value=str(member_count))

            bot_embed = disnake.Embed(title="Bot Count", color=disnake.Color.blurple())
            bot_embed.add_field(name="Count", value=str(bot_count))

            total_embed = disnake.Embed(title="Total Count", color=disnake.Color.blurple())
            total_embed.add_field(name="Count", value=str(total_count))

            await member_channel.send(embed=member_embed)
            await bot_channel.send(embed=bot_embed)
            await total_channel.send(embed=total_embed)


@bot.slash_command(
    name="serverstats",
    description="Display server statistics"
)
async def serverstats(ctx: disnake.ApplicationCommandInteraction):
    guild = ctx.guild
    member_count = guild.member_count
    bot_count = sum(member.bot for member in guild.members)
    total_count = member_count + bot_count

    cpu_usage = psutil.cpu_percent()
    memory_usage = psutil.virtual_memory().percent

    embed = disnake.Embed(title="📊 ▬ SERVER STATS ▬ 📊", color=disnake.Color.blurple())
    embed.add_field(name="Member Count", value=str(member_count))
    embed.add_field(name="Bot Count", value=str(bot_count))
    embed.add_field(name="Total Count", value=str(total_count))
    embed.add_field(name="Text Channels", value=str(len(guild.text_channels)))
    embed.add_field(name="Voice Channels", value=str(len(guild.voice_channels)))
    embed.add_field(name="CPU Usage", value=f"{cpu_usage}%")
    embed.add_field(name="Memory Usage", value=f"{memory_usage}%")

    await ctx.send(embed=embed)

setups = {}

@bot.slash_command(name="setup_role", description="Begin setting up a custom message")
@commands.has_guild_permissions(administrator=True)
async def setup_role(ctx):
    if ctx.guild.id not in setups:
        setups[ctx.guild.id] = []
    setups[ctx.guild.id].append({
        "step": "title",
        "title": "",
        "description": "",
        "roles": [],
        "emojis": [],
        "message_id": None,
        "include_roles": False,
        "color": ""
    })
    await ctx.send("Please enter the title for the message:")

@bot.event
async def on_message(message):
    if message.author == bot.user or message.guild.id not in setups:
        return

    setup = setups[message.guild.id][-1]

    if setup["step"] == "title":
        setup["title"] = message.content
        setup["step"] = "description"
        await message.channel.send("Please enter the description for the message:")
    elif setup["step"] == "description":
        setup["description"] = message.content
        setup["step"] = "color"
        await message.channel.send("Please enter the color name for the embed:")
    elif setup["step"] == "color":
        setup["color"] = message.content.lower()
        setup["step"] = "roles"
        await message.channel.send("Do you want to include role reactions? (yes/no):")
    elif setup["step"] == "roles":
        if message.content.lower() == "yes":
            setup["include_roles"] = True
            setup["step"] = "role_list"
            await message.channel.send("Please mention the roles for the role message (separated by spaces):")
        else:
            setup["include_roles"] = False
            setup["step"] = "channel"
            await message.channel.send("Please mention the channel where you want to post the message, or provide a name for a new channel:")
    elif setup["step"] == "role_list":
        role_order = [int(role_id) for role_id in re.findall(r'<@&(\d+)>', message.content)]
        setup["roles"] = sorted(message.role_mentions, key=lambda r: role_order.index(r.id))
        setup["step"] = "emoji_list"
        await message.channel.send("Please enter the emojis for each role (separated by spaces, in the same order as the roles):")
    elif setup["step"] == "emoji_list":
        setup["emojis"] = message.content.split()
        setup["step"] = "channel"
        await message.channel.send("Please mention the channel where you want to post the message, or provide a name for a new channel:")
    elif setup["step"] == "channel":
        if message.channel_mentions:
            setup_channel = message.channel_mentions[0]
        else:
            overwrites = {
                message.guild.default_role: disnake.PermissionOverwrite(read_messages=False),
                message.guild.me: disnake.PermissionOverwrite(read_messages=True)
            }
            setup_channel = await message.guild.create_text_channel(message.content, overwrites=overwrites)
        setup["step"] = None
      
        color_map = retrieve_color_map()
        color_hex = color_map.get(setup["color"], 0x000000)

        embed = disnake.Embed(title=setup["title"], description=setup["description"], color=color_hex)
        message_sent = await setup_channel.send(embed=embed)
        setup["message_id"] = message_sent.id

        if setup["include_roles"]:
            for emoji in setup["emojis"]:
                await message_sent.add_reaction(emoji)
        else:
            for emoji in setup["emojis"]:
                await message_sent.add_reaction(emoji)

def retrieve_color_map():
    return color_map

@bot.event
async def on_raw_reaction_add(payload):
    if payload.member.bot or payload.guild_id not in setups:
        return

    for setup in setups[payload.guild_id]:
        if setup['message_id'] != payload.message_id:
            continue

        emoji = str(payload.emoji)
        if emoji in setup["emojis"]:
            idx = setup["emojis"].index(emoji)
            role = disnake.utils.get(payload.member.guild.roles, id=setup["roles"][idx].id)
            if role in payload.member.roles:
                await payload.member.remove_roles(role)
            else:
                await payload.member.add_roles(role)
            break

@bot.event
async def on_raw_reaction_remove(payload):
    guild = bot.get_guild(payload.guild_id)
    if guild is None or payload.guild_id not in setups:
        return

    member = guild.get_member(payload.user_id)
    if member is None or member.bot:
        return

    for setup in setups[payload.guild_id]:
        if setup['message_id'] != payload.message_id:
            continue

        emoji = str(payload.emoji)
        if emoji in setup["emojis"]:
            idx = setup["emojis"].index(emoji)
            role = disnake.utils.get(guild.roles, id=setup["roles"][idx].id)
            if role in member.roles:
                await member.remove_roles(role)
            break


#Random commands that are use full


@bot.slash_command(description='Show color information.', options=[
    disnake.Option(name='color_name', description='Enter a color name', type=OptionType.string, required=True)
])
async def color(inter: disnake.ApplicationCommandInteraction, color_name: str):
    color_name = color_name.lower()
    if color_name not in color_map:
        await inter.response.send_message("Please provide a valid color name.")
        return

    color_hex_value = color_map[color_name]
    color_embed = disnake.Embed(title=f"Color: {color_name.capitalize()}", 
                                description=f"HEX: #{color_hex_value:06X}\nRGB: ({color_hex_value>>16}, {(color_hex_value>>8)&0xFF}, {color_hex_value&0xFF})",
                                color=color_hex_value)
    await inter.response.send_message(embed=color_embed)


@bot.slash_command(name="avatar", description="Get a user's avatar", 
                   options=[Option("user", "The user to get the avatar of", type=6, required=False)])
async def avatar(ctx, user: disnake.User = None):
    if user is None:  # if no member is mentioned
        user = ctx.author  # set member as the author

    embed = disnake.Embed(
        title = f"{user.name}'s avatar",
        color = disnake.Color.blue()
    )
    embed.set_image(url=user.display_avatar.url)
    await ctx.send(embed=embed)

@bot.slash_command(description='Check user info and ban history')
@disnake.ext.commands.has_permissions(administrator=True)
async def userinfo(ctx: disnake.ApplicationCommandInteraction, member: disnake.Member):
    # Get user info
    created_at = member.created_at.strftime('%a, %b %d, %Y %I:%M %p')
    joined_at = member.joined_at.strftime('%a, %b %d, %Y %I:%M %p')
    roles = [role.mention for role in member.roles if role != ctx.guild.default_role]

    # Get user's key permissions
    key_permissions = {'kick_members', 'ban_members', 'administrator', 'manage_channels', 'manage_guild',
                    'view_audit_log', 'manage_messages', 'mention_everyone', 'manage_roles', 'manage_webhooks',
                    'manage_emojis'}

    # Get user's key permissions, only if they are in the set defined above
    permissions = [perm[0].replace("_", " ").title() for perm in member.guild_permissions if perm[1] and perm[0] in key_permissions]

    # Get ban history
    async for ban_entry in ctx.guild.bans():
        if ban_entry.user.id == member.id:
            break
    else:
        ban_entry = None

    if ban_entry:
        ban_info = f'Banned at: {ban_entry.created_at}\nReason: {ban_entry.reason}'
    else:
        ban_info = 'No ban history found'

    # Create embed
    embed = disnake.Embed(color=disnake.Color.blue())
    
    # Show avatar and username#discriminator
    if member.avatar:
        embed.set_author(name=f'{member}', icon_url=member.avatar.url)
    else:
        embed.set_author(name=f'{member}')
    embed.set_thumbnail(url=member.avatar.url)
    embed.add_field(name='Joined', value=f'{joined_at}', inline=True)
    embed.add_field(name='Registered', value=f'{created_at}', inline=True)
    embed.add_field(name=f'Roles [{len(roles)}]', value=', '.join(roles) or "None", inline=False)
    
    # Add Key Permissions field if there are any
    if permissions:
        embed.add_field(name='Key Permissions', value=', '.join(permissions), inline=False)
    
    embed.add_field(name='Ban History', value=ban_info, inline=False)
    
    # Add Acknowledgements field if member is server owner
    if member == ctx.guild.owner:
        embed.add_field(name='Acknowledgements', value='Server Owner', inline=False)

    # Footer with ID, Requested by and Requested at
    embed.set_footer(text=f'ID: {member.id} | Requested by {ctx.author.name} | {datetime.datetime.now().strftime("Today at %I:%M %p")}')
    
    await ctx.response.send_message(embed=embed)

@userinfo.error
async def userinfo_error(ctx, error):
    if isinstance(error, disnake.commands.MissingPermissions):
        await ctx.send("You do not have permission to use this command.")
    else:
        raise error

#Ban command 
@bot.slash_command(description='Ban a user from the server.')
@commands.has_permissions(administrator=True)
async def ban(inter: disnake.ApplicationCommandInteraction, user: disnake.Member, reason: str = "No reason provided."):
    await user.ban(reason=reason)
    await inter.response.send_message(f'{user.name} has been banned from the server. Reason: {reason}')
    
    ban_log_channel_id = get_log_channel_id(inter.guild.id, 'ban')
    if ban_log_channel_id:
        ban_log_channel = bot.get_channel(ban_log_channel_id)
        await ban_log_channel.send(f"{user} has been banned from the server. Reason: {reason}")

@bot.slash_command(description='Kick a user from the server.')
@commands.has_permissions(administrator=True)
async def kick(inter: disnake.ApplicationCommandInteraction, user: disnake.Member, reason: str = "No reason provided."):
    await user.kick(reason=reason)
    await inter.response.send_message(f'{user.name} has been kicked from the server. Reason: {reason}')

    kick_log_channel_id = get_log_channel_id(inter.guild.id, 'kick')
    if kick_log_channel_id:
        kick_log_channel = bot.get_channel(kick_log_channel_id)
        await kick_log_channel.send(f"{user} has been kicked from the server. Reason: {reason}")

@bot.slash_command(description='Mute a user in the server.')
@commands.has_permissions(administrator=True)
async def mute(inter: disnake.ApplicationCommandInteraction, user: disnake.Member, duration: str, reason: str = "No reason provided."):
    # Mute the user by assigning the "Muted" role or applying necessary permission changes
    # Adjust the implementation based on your bot's mute functionality

    await inter.response.send_message(f'{user.name} has been muted for {duration}. Reason: {reason}')

    mute_log_channel_id = get_log_channel_id(inter.guild.id, 'mute')
    if mute_log_channel_id:
        mute_log_channel = bot.get_channel(mute_log_channel_id)
        await mute_log_channel.send(f"{user} has been muted for {duration}. Reason: {reason}")
#Unmute 
@bot.slash_command(description='Unmute a previously muted user.')
@commands.has_permissions(administrator=True)
async def unmute(self, inter: disnake.ApplicationCommandInteraction, user: disnake.Member):
    # Unmute the user by removing the "Muted" role or reverting the necessary permission changes
    # Adjust the implementation based on your bot's mute functionality

    await inter.response.send_message(f'{user.name} has been unmuted.')
#Manage Role
@bot.slash_command(description='Manage roles within the server.')
@commands.has_permissions(administrator=True)
async def role(self, inter: disnake.ApplicationCommandInteraction, action: str, user: disnake.Member, role: disnake.Role):
    if action == 'add':
        await user.add_roles(role)
        await inter.response.send_message(f'{user.name} has been given the role: {role.name}')
    elif action == 'remove':
        await user.remove_roles(role)
        await inter.response.send_message(f'{user.name} no longer has the role: {role.name}')
    else:
        await inter.response.send_message('Invalid action. Please provide either "add" or "remove".')
polls = defaultdict(dict)

@bot.slash_command(
    description="Setup a new poll",
    options=[
        Option("channel", "Mention of the channel to create the poll in", 3, required=True),
        Option("question", "The poll question", 3, required=True),
        Option("option_1", "Option 1", 3, required=True),
        Option("option_2", "Option 2", 3, required=True),
        Option("option_3", "Option 3", 3, required=False),
        Option("option_4", "Option 4", 3, required=False),
        Option("option_5", "Option 5", 3, required=False),
        Option("option_6", "Option 6", 3, required=False),
        Option("option_7", "Option 7", 3, required=False),
        Option("option_8", "Option 8", 3, required=False),
        Option("option_9", "Option 9", 3, required=False),
        Option("option_10", "Option 10", 3, required=False),
    ]
)
async def pollsetup(ctx, channel: str, question: str, option_1: str, option_2: str, option_3: str = None,
                    option_4: str = None, option_5: str = None, option_6: str = None, option_7: str = None,
                    option_8: str = None, option_9: str = None, option_10: str = None):
    channel_id = int(channel.strip('<#>'))  # Extract the ID from the mention

    channel = bot.get_channel(int(channel_id))
    if channel is None:
        await ctx.send("Invalid channel ID.")
        return

    options = [opt for opt in (option_1, option_2, option_3, option_4, option_5, option_6, option_7, option_8, option_9, option_10) if opt is not None]

    poll_embed = disnake.Embed(title=f"**{question}**", color=disnake.Color.blue())

    number_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

    for index, option in enumerate(options, start=1):
        poll_embed.add_field(name=f"{number_emojis[index-1]} {option}", value="\u200B", inline=False)
    poll_embed.set_footer(text=f"Requested by: {ctx.author.name}")

    message = await channel.send(embed=poll_embed)

    for emoji in number_emojis[:len(options)]:
        await message.add_reaction(emoji)

    polls[channel.id] = (message.id, options)

async def fetch_poll_results(ctx, channel: disnake.TextChannel, message_id: str):
    try:
        message_id = int(message_id)
    except ValueError:
        await ctx.send('Invalid message ID.')
        return None, None

    if channel.id not in polls or message_id != polls[channel.id][0]:
        await ctx.send('This message does not correspond to an active poll.')
        return None, None

    saved_message_id, options = polls[channel.id]

    try:
        message = await channel.fetch_message(message_id)
    except discord.NotFound:
        await ctx.send('Message not found. Please provide a valid message ID.')
        return None, None

    results = defaultdict(int)
    number_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    for reaction in message.reactions:
        if str(reaction.emoji) in number_emojis:
            index = number_emojis.index(str(reaction.emoji))
            results[index] += reaction.count - 1

    ordered_results = [results[i] for i in range(len(options))]
    return ordered_results, options


giveaways = {}  # Initialize the giveaways dictionary to store giveaway details

@bot.slash_command(description="Setup a giveaway")
@commands.has_permissions(administrator=True)
async def giveaway(ctx, channel: disnake.TextChannel, *custom_message_lines: str, prize1: str = "", prize2: str = "", prize3: str = "", prize4: str = "", prize5: str = "", prize6: str = "", prize7: str = "", prize8: str = "", prize9: str = "", prize10: str = ""):
    custom_message = "\n".join(custom_message_lines)  # Join the custom_message_lines into a single string
    prize_names = [prize for prize in [prize1, prize2, prize3, prize4, prize5, prize6, prize7, prize8, prize9, prize10] if prize]
    if not prize_names:
        await ctx.send("Please specify at least one prize.")
        return

    # Check if all specified prizes are valid
    for prize_name in prize_names:
        if prize_name not in prizes:
            await ctx.send(f"{prize_name} is not a valid prize. Valid prizes are: {', '.join(prizes.keys())}")
            return

    giveaway_id = str(uuid.uuid4())  # Generate a unique ID

    embed = disnake.Embed(title="🎉 **GIVEAWAY** 🎉", description=custom_message, color=0x00FF00)
    embed.add_field(name="Prizes", value="\n".join(prize_names), inline=False)
    embed.set_footer(text="React with 🎁 to participate!")

    giveaway_message = await channel.send(embed=embed)
    await giveaway_message.add_reaction("🎁")

    # Save the giveaway details
    giveaways[giveaway_id] = (channel.id, giveaway_message.id, prize_names)

    await ctx.send(f"The giveaway with ID `{giveaway_id}` has started!")

@bot.slash_command(description="End a giveaway")
@commands.has_permissions(administrator=True)
async def end_giveaway(ctx, giveaway_id: str, key1: str = "", key2: str = "", key3: str = "", key4: str = "", key5: str = "", key6: str = "", key7: str = "", key8: str = "", key9: str = "", key10: str = ""):
    if giveaway_id not in giveaways:
        await ctx.send("That giveaway does not exist.")
        return

    channel_id, giveaway_message_id, prize_names = giveaways[giveaway_id]
    del giveaways[giveaway_id]

    keys = [key for key in [key1, key2, key3, key4, key5, key6, key7, key8, key9, key10] if key]
    if len(keys) != len(prize_names):
        await ctx.send(f"Please provide exactly {len(prize_names)} keys, one for each prize.")
        return

    # Get the channel and the giveaway message
    try:
        channel = bot.get_channel(channel_id)
        giveaway_message = await channel.fetch_message(giveaway_message_id)
    except disnake.NotFound:
        await ctx.send("The giveaway message was not found.")
        return

          # Get the users who reacted with 🎁
    users = set()
    for reaction in giveaway_message.reactions:
        if str(reaction.emoji) == "🎁":
            async for user in reaction.users():
                if not user.bot:
                    users.add(user)

    if not users:
        await ctx.send("No one participated in the giveaway.")
        return

    if len(users) < len(prize_names):
        await ctx.send(f"There are not enough participants to choose a winner for each prize. Only {len(users)} user(s) participated in the giveaway.")
        return

    # Choose a random winner for each prize
    winners = random.sample(list(users), k=len(prize_names))  # Convert the users set to a list




    for prize_name, key, winner in zip(prize_names, keys, winners):
        # Retrieve the prize message based on the prize name
        message = prizes[prize_name].format(key=key)

        # Display the message to the user
        await winner.send(message)

        await ctx.send(f"🎉 Congratulations {winner.mention}! You won the **{prize_name}** giveaway!")



#git hub commits 
@bot.slash_command(name='getcommits', description='Get the latest commits from a GitHub repo')
async def getcommits(interaction, user: str, repo: str):
    # Use GitHub API to get commits
    url = f"https://api.github.com/repos/{user}/{repo}/commits"
    response = requests.get(url)

    if response.status_code == 200:
        commits = json.loads(response.text)
        commit_message = ""

        # Let's get the 5 latest commits
        for commit in commits[:5]:
            commit_message += f"Author: {commit['commit']['author']['name']}\nMessage: {commit['commit']['message']}\nUrl: {commit['html_url']}\n\n"

        # Send message in chat
        await interaction.response.send_message(commit_message)

    else:
        await interaction.response.send_message("Couldn't get the commits. Please make sure the repo and the username are correct.")

@bot.slash_command(name='setup_commit', description='Set up the bot to check for new commits every 5 minutes')
async def setup_commit(interaction, user: str, repo: str, channels: str):
    channel_names = channels.split(',')
    for channel_name in channel_names:
        channel = discord.utils.get(interaction.guild.channels, name=channel_name)
        if channel is not None:
            check_commits.start(user, repo, channel.id)
    await interaction.response.send_message(f"Bot is now checking for new commits in {user}/{repo} every 5 minutes and posting updates in the specified channels.")


logging.basicConfig(level=logging.INFO)



latest_commit_sha = None

@tasks.loop(minutes=5)
async def check_commits(user, repo, channel_id):
    global latest_commit_sha

    # Use GitHub API to get commits
    url = f"https://api.github.com/repos/{user}/{repo}/commits"
    response = requests.get(url)

    if response.status_code == 200:
        commits = json.loads(response.text)

        # Let's get the latest commit
        commit = commits[0]
        if commit['sha'] != latest_commit_sha:
            latest_commit_sha = commit['sha']

            # Create embed
            embed = Embed(title=f"New commit in {user}/{repo}")
            embed.add_field(name="Author", value=commit['commit']['author']['name'])
            embed.add_field(name="Message", value=commit['commit']['message'])
            embed.add_field(name="URL", value=commit['html_url'])
            embed.set_image(url=f"https://opengraph.githubassets.com/{commit['sha']}/{user}/{repo}")

            # Send message in chat
            channel = bot.get_channel(channel_id)
            await channel.send(embed=embed)

    else:
        channel = bot.get_channel(channel_id)
        await channel.send("Couldn't get the commits. Please make sure the repo and the username are correct.")


intents = discord.Intents.default()
intents.typing = False
intents.presences = False


# Load log channels data
def load_log_channels_data():
    try:
        with open("channels.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

# Save log channels data
def save_log_channels_data(data):
    with open("channels.json", "w") as f:
        json.dump(data, f, indent=4)

def get_log_channel_id(guild_id, action):
    data = load_log_channels_data()
    return data.get(f"{guild_id}_{action}")

def save_log_channel_id(guild_id, action, channel_id):
    data = load_log_channels_data()
    data[f"{guild_id}_{action}"] = channel_id
    save_log_channels_data(data)

@bot.event
async def on_member_join(member):
    join_log_channel_id = get_log_channel_id(member.guild.id, 'join')
    if join_log_channel_id:
        join_log_channel = bot.get_channel(join_log_channel_id)
        
        message = random.choice(WELCOME_MESSAGES).format(member=member.mention, server=member.guild.name)
        
        embed = Embed(title="🎮 New Player Alert 🎮",
                      description=message,
                      color=Color.lighter_gray())  
        embed.set_thumbnail(url=member.display_avatar.url)
        
        await join_log_channel.send(embed=embed)

@bot.event
async def on_member_remove(member):
    leave_log_channel_id = get_log_channel_id(member.guild.id, 'leave')
    if leave_log_channel_id:
        leave_log_channel = bot.get_channel(leave_log_channel_id)
        await leave_log_channel.send(f"{member} has left the server.")

@bot.slash_command(description="Set up log channels")
async def setup_logs(
    inter: disnake.ApplicationCommandInteraction, 
    join_log_channel: disnake.TextChannel, 
    leave_log_channel: disnake.TextChannel,
    ban_log_channel: disnake.TextChannel, 
    kick_log_channel: disnake.TextChannel,
    mute_log_channel: disnake.TextChannel
):
    save_log_channel_id(inter.guild.id, 'join', join_log_channel.id)
    save_log_channel_id(inter.guild.id, 'leave', leave_log_channel.id)
    save_log_channel_id(inter.guild.id, 'ban', ban_log_channel.id)
    save_log_channel_id(inter.guild.id, 'kick', kick_log_channel.id)
    save_log_channel_id(inter.guild.id, 'mute', mute_log_channel.id)
    await inter.response.send_message("Join, leave, ban, kick and mute logs configured successfully.")
      
@bot.event
async def on_error(event, *args, **kwargs):
    import traceback
    error_message = traceback.format_exc()
    print(f"An error occurred: {error_message}")

# Run the bot
async def main():
    await bot.start(TOKEN)

if __name__ == "__main__":
    try:
        with open('data.json', 'r') as f:
            data.update(json.load(f))
        print("Data loaded successfully.")
    except FileNotFoundError:
        print("Data file does not exist, starting fresh.")
    except json.JSONDecodeError:
        print("Failed to decode data, starting fresh.")

    asyncio.run(main())
# Run the bot
bot.run(TOKEN)
