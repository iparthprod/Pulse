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
from epicstore_api import EpicGamesStoreAPI
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

# Set up Spotify API credentials
spotify_credentials = SpotifyClientCredentials(client_id=SPOTIPY_CLIENT_ID, client_secret=SPOTIPY_CLIENT_SECRET)
spotify = spotipy.Spotify(client_credentials_manager=spotify_credentials)

bot = commands.Bot(command_prefix='/', intents=disnake.Intents.all(), help_command=None)

start_time = datetime.datetime.utcnow()
class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get('title')
        self.url = data.get('url')

@classmethod
async def create_source(cls, bot, url, loop, page, download=False):
    ytdl = youtube_dl.YoutubeDL({'format': 'bestaudio/best', 'noplaylist': 'True'})

    if download:
        ytdl.params['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '320',
        }]

    loop = loop or asyncio.get_event_loop()

    # Add page number to search query
    url = f'{url} page {page}'

    data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=download))
    if 'entries' in data:
        # If it's a playlist, select the first entry
        data = data['entries'][0]

    ffmpeg_options = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn',
    }

    source = await discord.FFmpegPCMAudio(data['url'], **ffmpeg_options)
    return cls(source, data=data)

class Queue:
    def __init__(self):
        self._queue = deque()
        self.current_song = None
        self.is_playing = False

    def add(self, item):
        self._queue.append(item)

    def dequeue(self):
        return self._queue.popleft()

    def remove_song(self, index):
        if 0 <= index < len(self._queue):
            self._queue.pop(index)

    def clear_queue(self):
        self._queue.clear()

    def is_empty(self):
        return not self._queue

    async def play_next_song(self, bot, guild_id):
        if not self.is_empty() and not self.is_playing:
            self.is_playing = True
            next_song = self.dequeue()
            print(f'Playing next song: {next_song}')  # Debug print statement
            self.current_song = next_song

            voice_client = bot.voice_clients[guild_id]
            source = await YTDLSource.create_source(bot, next_song['url'], loop=bot.loop, download=False)

            async def after_playback(error, guild_id):
                if error:
                    print(f"Error in playback: {error}")

                # Check if there was a skip request
                if skip_request.get(guild_id):
                    # Reset the skip request flag
                    skip_request[guild_id] = False
                    return

                # Get the next song to play
                queue = queues.get(guild_id)
                if queue and not queue.is_empty():
                    next_song = queue.dequeue()
                    print(f'Playing next song: {next_song}')  # Debug print statement

                    voice_client = bot.voice_clients[guild_id]
                    source = await YTDLSource.create_source(bot, next_song['url'], loop=bot.loop, download=False)
                    voice_client.play(source, after=lambda e: asyncio.create_task(after_playback(e, guild_id)))

                    # Update the currently playing song
                    queue.current_song = next_song
                else:
                    # No more songs in the queue
                    currently_playing.pop(guild_id, None)
                    playercontrols.pop(guild_id, None)
                    if guild_id in players:
                        players[guild_id].stop()
                        del players[guild_id]
                    queues.pop(guild_id, None)

                    # Remove the currently playing song from the queue
                    queue.current_song = None


    def size(self):
        return len(self._queue)

    @property
    def queue(self):
        return self._queue


class PlayerControls(disnake.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(disnake.ui.Button(style=disnake.ButtonStyle.red, emoji="⏯️", custom_id="play_pause"))
        self.add_item(disnake.ui.Button(style=disnake.ButtonStyle.red, emoji="⏭️", custom_id="skip"))
        self.add_item(disnake.ui.Button(style=disnake.ButtonStyle.red, emoji="💌", custom_id="send_dm"))
        self.add_item(disnake.ui.Button(style=disnake.ButtonStyle.red, emoji="🗑️", custom_id="clear_chat"))  # Clear button
        self.add_item(disnake.ui.Button(style=disnake.ButtonStyle.red, emoji="📑", custom_id="show_queue"))
        self.add_item(disnake.ui.Button(style=disnake.ButtonStyle.red, emoji="🧹", custom_id="clear_queue"))  # Clear queue button
class VolumeControl(ui.View):
    def __init__(self):
        super().__init__()

class ControlsView(PlayerControls):
    def __init__(self):
        super().__init__()
        self.add_item(VolumeButton('🔉', -25))
        self.add_item(VolumeButton('🔊', 25))

class VolumeButton(ui.Button):
    def __init__(self, label, volume_delta):
        super().__init__(style=ButtonStyle.secondary, label=label)
        self.volume_delta = volume_delta

    async def callback(self, interaction: disnake.MessageInteraction):
        # Defer the interaction
        await interaction.response.defer()

        voice_client = interaction.guild.voice_client
        if voice_client and voice_client.source:
            new_volume = voice_client.source.volume + self.volume_delta / 100
            new_volume = max(0, min(new_volume, 2))  # Ensure the volume is between 0 and 2
            voice_client.source.volume = new_volume
            try:
                await interaction.edit_original_message(content=f"Volume: {new_volume * 100:.0f}%")
            except disnake.errors.InteractionResponded:
                pass
        else:
            try:
                await interaction.response.send_message("Nothing is playing right now.")
            except disnake.errors.InteractionResponded:
                pass

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queues = {}  # Initialize queues at the class level
        self.logger = logging.getLogger('Music')  # Create a logger for this class

    async def _play(self, inter, *, song):
        guild_id = inter.guild.id

        try:
            if guild_id not in self.queues:
                self.queues[guild_id] = Queue(guild_id)

            if inter.guild.voice_client.is_playing():
                self.logger.debug(f'Adding song to queue for guild {guild_id}')
                await get_youtube_song(inter, song, add_to_queue=True)  # Add to queue if a song is playing
            else:
                self.logger.debug(f'Playing song immediately for guild {guild_id}')
                await get_youtube_song(inter, song, add_to_queue=False)  # Play immediately if no song is playing
        except Exception as e:
            self.logger.error(f'Error in _play for guild {guild_id}: {e}', exc_info=True)

    async def play_next(self, inter):
        guild_id = inter.guild.id
        if guild_id in self.queues:
            queue = self.queues[guild_id]
            if not queue.is_empty():
                bot_instance = inter.bot
                await queue.play_next_song(bot_instance, guild_id)
                return
        currently_playing.pop(guild_id, None)
        players[guild_id].stop()
        del players[guild_id]
        self.queues.pop(guild_id, None)

        async def play_next_song(self, bot, guild_id):
            try:
                if guild_id in self.queues:
                    queue = self.queues[guild_id]
                    if not queue.is_empty():
                        next_song = queue.dequeue()
                        queue.current_song = next_song

                        voice_client = bot.voice_clients[guild_id]
                        source = await YTDLSource.create_source(bot, next_song['url'], loop=bot.loop, download=False)
                        voice_client.play(source, after=lambda _: asyncio.ensure_future(asyncio.sleep(1), self.play_next_song(bot, guild_id)))

                        # Remove the currently playing song from the queue after starting to play the next song
                        queue.current_song = None
                    else:
                        currently_playing.pop(guild_id, None)
                        players[guild_id].stop()
                        del players[guild_id]
                        self.queues.pop(guild_id, None)
                else:
                    currently_playing.pop(guild_id, None)
                    players[guild_id].stop()
                    del players[guild_id]
                    self.queues.pop(guild_id, None)
            except Exception as e:
                self.logger.error(f'Error in play_next_song for guild {guild_id}: {e}', exc_info=True)



    @commands.command()
    async def join(self, ctx):
        channel = ctx.author.voice.channel
        voice_client = disnake.utils.get(ctx.bot.voice_clients, guild=ctx.guild)

        if voice_client and voice_client.is_connected():
            await voice_client.move_to(channel)
        else:
            voice_client = await channel.connect()

        # Ensure the bot is self-deafened
        await ctx.guild.change_voice_state(channel=channel, self_deaf=True)

        await ctx.send(f'Joined {channel}')

# Function to join the voice channel the user is in
async def join_voice_channel(inter):
    channel = inter.author.voice.channel
    guild_id = inter.guild.id
    voice_client = disnake.utils.get(bot.voice_clients, guild=inter.guild)

    if voice_client:
        if voice_client.is_connected():
            await voice_client.move_to(channel)
        else:
            await channel.connect()
            voice_client = disnake.utils.get(bot.voice_clients, guild=inter.guild)
    else:
        await channel.connect()
        voice_client = disnake.utils.get(bot.voice_clients, guild=inter.guild)

    if voice_client and voice_client.is_playing():
        voice_client.stop()  # Stop the currently playing audio before setting the volume

    voice_client.volume = 20  # Set the default user volume to 20

class VolumeButton(ui.Button):
    def __init__(self, label, volume_delta):
        super().__init__(style=ButtonStyle.secondary, label=label)
        self.volume_delta = volume_delta

    async def callback(self, interaction: disnake.MessageInteraction):
        # Defer the interaction
        await interaction.response.defer()

        voice_client = interaction.guild.voice_client
        if voice_client and voice_client.source:
            new_volume = voice_client.source.volume + self.volume_delta / 100
            new_volume = max(0, min(new_volume, 2))  # Ensure the volume is between 0 and 2
            voice_client.source.volume = new_volume
            try:
                await interaction.edit_original_message(content=f"Volume: {new_volume * 100:.0f}%")
            except disnake.errors.InteractionResponded:
                pass
        else:
            try:
                await interaction.response.send_message("Nothing is playing right now.")
            except disnake.errors.InteractionResponded:
                pass

# Set the default volume to 25
default_volume = 25 / 100  # Convert to a decimal value between 0 and 1

# Create an instance of the VolumeButton with the default volume
volume_button = VolumeButton(label="Volume", volume_delta=default_volume)

# Function to get the command signature for a given command
def get_command_signature(command: commands.Command):
    return f'/{command.name} {command.signature}'

async def play_song(ctx, info):
    if info is None:
        await ctx.send("Error: Unable to fetch the song URL.")
        return

    url = info['url']
    title = info['title']
    youtube_url = get_youtube_url(info['id'])
    thumbnail = info['thumbnail']
    duration = format_duration(info['duration'])
    requested_by = ctx.author.name

    print(f"Attempting to play URL: {url}")  # Debugging

    voice_client = ctx.guild.voice_client

    if voice_client.is_playing():
        voice_client.stop()

    FFMPEG_OPTIONS = {
        'options': '-vn',
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    }
# c:/ffmpeg/bin/ffmpeg.exe for windows and /usr/bin/ffmpeg for linux : assuming those are the directory 
    source = disnake.FFmpegPCMAudio(url, **FFMPEG_OPTIONS, executable='c:/ffmpeg/bin/ffmpeg.exe') # chanage the path here
    volume_transformer = disnake.PCMVolumeTransformer(source)
    
    # After the current song ends, it will play the next song in the queue.
    voice_client.play(volume_transformer, after=lambda e: bot.loop.create_task(play_next_song(ctx)))

    # Create the Song object
    song = Song(info['id'], title, youtube_url, thumbnail, duration, requested_by)

    # Update the currently playing song
    currently_playing[ctx.guild.id] = song

    # Store the message view
    embed = disnake.Embed(title="Now Playing", color=disnake.Color.green())
    embed.add_field(name="Title", value=f"[{title}]({youtube_url})", inline=False)
    embed.add_field(name="Duration", value=duration, inline=False)
    embed.set_thumbnail(url=thumbnail)
    embed.set_footer(text=f"Requested by: {requested_by}")
    view = ControlsView()
    await ctx.send(embed=embed, view=view)

def get_youtube_url(video_id):
    return f"https://www.youtube.com/watch?v={video_id}"


# Function to fetch playlist information using YouTube Data API
async def fetch_playlist_info(playlist_id):
    api_key = os.getenv('YOUTUBE_API_KEY')  # Replace with your YouTube Data API key

    youtube = googleapiclient.discovery.build('youtube', 'v3', developerKey=api_key)
    request = youtube.playlistItems().list(
        part='snippet',
        playlistId=playlist_id,
        maxResults=50  # Adjust the maximum number of results as needed
    )

    try:
        response = await request.execute()
        playlist_info = {
            'tracks': []
        }

        for item in response.get('items', []):
            track_info = item['snippet']
            song = {
                'id': track_info['resourceId']['videoId'],
                'title': track_info['title'],
                'url': f"https://www.youtube.com/watch?v={track_info['resourceId']['videoId']}",
                'thumbnail': track_info['thumbnails']['default']['url'],
                'duration': 'Unknown',  # You can fetch the duration using additional API calls if needed
                'requested_by': 'Unknown'  # Set the requested_by field as needed
            }
            playlist_info['tracks'].append(song)

        return playlist_info

    except googleapiclient.errors.HttpError as e:
        print(f"Error fetching playlist information: {e}")
        return None


async def get_youtube_song(inter, search_query, add_to_queue=True):
    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'default_search': 'ytsearch:',
            'extractor_args': {
                'youtube': {'noplaylist': True},
                'soundcloud': {},
            },
        }

        # Initialize a counter for the page number
        page_number = 1

        # Loop until you've fetched the desired number of songs
        while len(queues[inter.guild.id]) < 100:
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                # Append the page number to the search query
                info = ydl.extract_info(f'{search_query} page {page_number}', download=False)
                if 'entries' in info:
                    info = info['entries'][0]

            if info is None:
                return False, "Error: Unable to fetch the song URL."

            if add_to_queue:
                queues[inter.guild.id].add(info)
                if not inter.guild.voice_client.is_playing() and not inter.guild.voice_client.is_paused():
                    await play_song(inter, info)
            else:
                if not inter.guild.voice_client.is_playing() and not inter.guild.voice_client.is_paused():
                    await play_song(inter, info)
                else:
                    await show_queue(inter.guild.id, inter.channel)  # Show the updated queue

            # Increment the page number
            page_number += 1

        return True, ""  # No error occurred

    except Exception as e:
        error_message = f"An error occurred while getting the song: {str(e)}"
        return False, error_message




async def show_queue(guild_id, channel):
    queue = queues[guild_id]
    if not queue.is_empty():
        song_list = [f"{song['title']} - {format_duration(song['duration'])}" for song in queue.get_all()]
        await channel.send("Current Queue:\n" + "\n".join(song_list))
    else:
        await channel.send("The queue is empty.")


def format_duration(duration):
    minutes = duration // 60
    seconds = duration % 60
    return f"{minutes:02d}:{seconds:02d}"



@bot.slash_command(name="replay", description="Replay the last song")
async def _replay(inter):
    global queues

    if inter.guild.id not in queues or len(queues[inter.guild.id]) == 0:
        await inter.response.send_message("No song has been played yet to replay.")
        return

    song = queues[inter.guild.id].replay_song()
    if song is None:
        await inter.response.send_message("No song has been played yet to replay.")
        return

    await play_song(inter, song)

async def play_next(inter):
    guild_id = inter.guild.id
    if guild_id in queues:
        queue = queues[guild_id]
        if not queue.is_empty():
            bot_instance = inter.bot
            await queue.play_next_song(bot_instance, guild_id)
            return
    currently_playing.pop(guild_id, None)
    playercontrols.pop(guild_id, None)
    players[guild_id].stop()
    del players[guild_id]
    queues.pop(guild_id, None)





@bot.slash_command(name="play_next", description="Skip to the next song in the queue")
async def _play_next(inter):
    await play_next(inter)

# Slash command to join the voice channel
@bot.slash_command(name="join", description="Join the voice channel")
async def _join(inter):
    # Check if the user is in a voice channel
    if not inter.author.voice or not inter.author.voice.channel:
        await inter.response.send_message("You need to be in a voice channel to join.")
        return
    # Join the voice channel
    await join_voice_channel(inter)
    
    await inter.response.send_message("Joined the voice channel.")

# Global dictionary to keep track of users who have used /play command
users_played_before = {}

@bot.slash_command(name="play", description="Play a song from YouTube or Spotify")
async def _play(inter: disnake.CommandInteraction, song_url: str):
    # Check if the user is in a voice channel
    if not inter.author.voice or not inter.author.voice.channel:
        await inter.response.send_message("You need to be in a voice channel to play a song.")
        return

    await inter.response.defer()  # Defer the response

    # Create the queue for the guild if it doesn't exist
    if inter.guild.id not in queues:
        queues[inter.guild.id] = Queue()

    # Join the voice channel
    await join_voice_channel(inter)

    guild_id = inter.guild.id

    if 'spotify.com' in song_url:
        if 'playlist' in song_url:
            playlist = spotify.playlist_items(song_url)
            for item in playlist['items']:
                track = item['track']
                song_name = track['name']
                song_artist = track['artists'][0]['name']
                search_query = f"{song_name} {song_artist}"
                song_status, error_message = await get_youtube_song(inter, search_query, add_to_queue=True)
                if not song_status:  # If there's an error in retrieving the song
                    print(f"Skipping song '{song_name}' due to error: {error_message}")  # Print debug message and skip the song
                    continue  # Skip to the next song
                await asyncio.sleep(1)  # pause for 1 second

            if (guild_id in queues and not queues[guild_id].is_empty() and 
                guild_id in players and not players[guild_id].is_playing()):
                await play_song(inter)

        else:
            track = spotify.track(song_url)
            song_name = track['name']
            song_artist = track['artists'][0]['name']
            search_query = f"{song_name} {song_artist}"
            song_status, error_message = await get_youtube_song(inter, search_query, add_to_queue=True)
            if not song_status:  # If there's an error in retrieving the song
                print(f"Skipping song '{song_name}' due to error: {error_message}")  # Print debug message and skip the song
                return
            if (guild_id in queues and not queues[guild_id].is_empty() and 
                guild_id in players and not players[guild_id].is_playing()):
                await play_song(inter)
    else:
        song_status, error_message = await get_youtube_song(inter, song_url, add_to_queue=True)
        if not song_status:  # If there's an error in retrieving the song
            print(f"Skipping song '{song_url}' due to error: {error_message}")  # Print debug message and skip the song
            return
        if (guild_id in queues and not queues[guild_id].is_empty() and 
            guild_id in players and not players[guild_id].is_playing()):
            await play_song(inter)



        # Check if this is the first time the user has used the /play command
    if inter.author.id not in users_played_before or not users_played_before[inter.author.id]:
        # If it's the first time, send an embed message explaining what each button does
        embed = disnake.Embed(title="🎵 Music Controls 🎵", description="It's your first time using `/play`. Here's what each button does:", color=disnake.Color.green())
        embed.add_field(name="⏯️ - **Play or pause the song**", value="\u200b", inline=False)
        embed.add_field(name="⏭️ - **Skip to the next song**", value="\u200b", inline=False)
        embed.add_field(name="💌 - **Send a DM with the YouTube song link**", value="\u200b", inline=False)
        embed.add_field(name="🗑️ - **Clear the chat and disconnect the bot**", value="\u200b", inline=False)
        embed.add_field(name="📑 - **Show the current songs in the queue**", value="\u200b", inline=False)
        embed.add_field(name="🧹 - **Clear the queue and disconnect the bot**", value="\u200b", inline=False)
        embed.add_field(name="🔉 - **Decrease the volume by 25%**", value="\u200b", inline=False)
        embed.add_field(name="🔊 - **Increase the volume by 25%**", value="\u200b", inline=False)
        embed.set_footer(text="Enjoy your music session! 🎧")

            
        await inter.followup.send(embed=embed)
            # And mark this user as having used the /play command before
        users_played_before[inter.author.id] = True


async def play_next_song(inter):
    # Check if there are any songs in the queue
    if not queues[inter.guild.id].is_empty():
        # Get the next song
        next_song = queues[inter.guild.id].dequeue()

        # Play the song
        await play_song(inter, next_song)

    embed = disnake.Embed(title="Now Playing", color=disnake.Color.green())
    embed.add_field(name="Title", value=next_song['title'], inline=False)
    embed.add_field(name="Duration", value=next_song['duration'], inline=False)
    embed.set_thumbnail(url=next_song.get('thumbnail', 'default_thumbnail_url'))
    embed.set_footer(text=f"Requested by: {next_song['requested_by']}")
    view = ControlsView()
    await inter.followup.send(embed=embed, view=view)

# ...

async def get_youtube_song(inter, search_query, add_to_queue=True):
    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'default_search': 'ytsearch:',
            'extractor_args': {
                'youtube': {'noplaylist': True},
                'soundcloud': {},
            },
        }

        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(search_query, download=False)
            if 'entries' in info:
                info = info['entries'][0]

        if info is None:
            await inter.send("Error: Unable to fetch the song URL.")
            return False, "Error: Unable to fetch the song URL."

        if add_to_queue:
            queues[inter.guild.id].add(info)
            if not inter.guild.voice_client.is_playing() and not inter.guild.voice_client.is_paused():
                await play_song(inter, info)
        else:
            if not inter.guild.voice_client.is_playing() and not inter.guild.voice_client.is_paused():
                await play_song(inter, info)
            else:
                await show_queue(inter.guild.id, inter.channel)  # Show the updated queue

        return True, ""  # No error
    except Exception as e:
        return False, str(e)  # There was an error, return False and the error message


def format_duration(duration):
    minutes = duration // 60
    seconds = duration % 60
    return f"{minutes:02d}:{seconds:02d}"

@bot.slash_command(name="show_queue", description="Show the current song queue")
async def _show_queue(inter, page_number: int = 1):
    guild_id = inter.guild.id
    if guild_id in queues and queues[guild_id].size() > 0:
        queue = queues[guild_id]
        queue_items = [song['title'] for song in queue.queue]

        page_size = 10
        page_count = (len(queue_items) + page_size - 1) // page_size  # Calculate total number of pages
        
        if page_number < 1 or page_number > page_count:
            await inter.response.send_message("Invalid page number.")
            return

        start_index = (page_number - 1) * page_size
        end_index = start_index + page_size
        queue_items_page = queue_items[start_index:end_index]

        queue_text = "\n".join([f"`{start_index + i + 1}.` {song}" for i, song in enumerate(queue_items_page)])

        embed = disnake.Embed(
            title="Music Queue",
            description=queue_text,
            color=disnake.Color.blue()
        )
        embed.set_footer(text=f"Page {page_number}/{page_count} | Songs {start_index + 1}-{end_index}/{len(queue_items)} | Requested by: {inter.user.display_name}")


        await inter.response.send_message(embed=embed)
    else:
        await inter.response.send_message("The music queue is currently empty.")

def get_readable_song_name(song_name):
    # Remove special characters and capitalize the first letter of each word
    cleaned_name = ' '.join(word.capitalize() for word in re.findall(r'\w+', song_name))
    
    # Remove unwanted words
    unwanted_words = ['video', 'full', 'song']
    cleaned_name = ' '.join(word for word in cleaned_name.split() if word.lower() not in unwanted_words)
    
    return cleaned_name


@bot.slash_command(name="clear_queue", description="Clear the current song queue")
async def _clear_queue(inter):
    guild_id = inter.guild.id
    if guild_id in queues and queues[guild_id].size() > 0:
        queue = queues[guild_id]
        queue.queue.clear()  # Assuming you have a `clear` method in your Queue class
        
        # Check if the bot is connected to a voice channel
        voice_client = inter.guild.voice_client
        if voice_client and voice_client.is_connected():
            # Disconnect the bot from the voice channel
            await voice_client.disconnect()

        await inter.response.send_message("The song queue has been cleared.")
    else:
        await inter.response.send_message("The song queue is already empty.")



@bot.slash_command(name="play_pause", description="Pause or resume the currently playing song")
async def _play_pause(inter):
    guild_id = inter.guild.id
    if guild_id in currently_playing:
        voice_client = inter.guild.voice_client
        if voice_client.is_playing():
            voice_client.pause()
            await inter.response.send_message("Paused the song.")
        else:
            voice_client.resume()
            await inter.response.send_message("Resumed the song.")
    else:
        await inter.response.send_message("No song is currently playing.")
class Song:
    def __init__(self, song_id, title, youtube_url, thumbnail, duration, requested_by):
        self.song_id = song_id
        self.title = title
        self.youtube_url = youtube_url
        self.thumbnail = thumbnail
        self.duration = duration
        self.requested_by = requested_by

# Function to add a song to the queue
async def add_to_queue(inter, song_info):
    song = Song(song_info['id'], song_info['title'])

    guild_id = inter.guild.id
    if guild_id not in queues:
        queues[guild_id] = Queue()

    queues[guild_id].enqueue(song)

@bot.slash_command(name="skip", description="Skip the currently playing song")
async def _skip(inter):
    guild_id = inter.guild.id
    if guild_id in queues:
        queue = queues[guild_id]
        if not queue.is_empty():
            # Set the skip request flag
            skip_request[guild_id] = True
            
            # Stop the current song
            voice_client = inter.guild.voice_client
            voice_client.stop()
            
            print(f'Skipping song. Queue: {list(queue._queue)}')  # Debug print statement

            await inter.send("Skipping to the next song.")
        else:
            await inter.send("The song queue is empty.")
    else:
        await inter.send("The song queue is empty.")




@bot.slash_command(name="player", description="Manage the music player")
async def _player(ctx):
    guild_id = ctx.guild.id

    if guild_id in currently_playing:
        song = currently_playing[guild_id]
        embed = disnake.Embed(title="Now Playing", color=disnake.Color.green())
        embed.add_field(name="Title", value=f"[{song.title}]({song.youtube_url})", inline=False)
        embed.add_field(name="Duration", value=song.duration, inline=False)
        embed.set_thumbnail(url=song.thumbnail)
        embed.set_footer(text=f"Requested by: {song.requested_by}")
    else:
        embed = disnake.Embed(title="Music Player", description="No song is currently playing.", color=disnake.Color.blue())

    view = PlayerControls()
    view= ControlsView ()

    if ctx.data.name == "clear":
        # Clear chat and disconnect functionality
        channel = ctx.channel

        # Delete all messages in the channel
        await channel.purge()

        # Disconnect the bot from the voice channel (if connected)
        voice_client = get(bot.voice_clients, guild=ctx.guild)
        if voice_client and voice_client.is_connected():
            await voice_client.disconnect()

        # Send a response message indicating the chat has been cleared
        embed = disnake.Embed(title="Music Player", description="Chat cleared and bot disconnected.", color=disnake.Color.blue())
        await ctx.send(embed=embed, view=view)
    else:
        await ctx.send(embed=embed, view=view)
@bot.event
async def on_button_click(inter):
    custom_id = inter.data.custom_id

    if custom_id == "skip" or custom_id == "skip_command":
        guild_id = inter.guild.id
        if guild_id in queues:
            queue = queues[guild_id]
            if not queue.is_empty():
                # Set the skip request flag
                skip_request[guild_id] = True

                # Stop the current song
                voice_client = inter.guild.voice_client
                voice_client.stop()

                print(f'Skipping song. Queue: {list(queue._queue)}')  # Debug print statement

                await inter.send("Skipping to the next song.")
            else:
                await inter.send("The song queue is empty.")
        else:
            await inter.send("The song queue is empty.")

    elif custom_id == "play_pause":
        voice_client = inter.guild.voice_client
        if voice_client.is_playing():
            voice_client.pause()
            await inter.message.edit(content="Paused the song.")
        else:
            voice_client.resume()
            await inter.message.edit(content="Resumed the song.")

    elif custom_id == "stop":
        inter.guild.voice_client.stop()
        await inter.message.edit(content="Stopped the song.")

    elif custom_id == "send_dm":
        if inter.guild.id in currently_playing:
            song = currently_playing[inter.guild.id]
            message = f"Here is the song you liked:\nView on YouTube: {song.youtube_url}"
            await inter.user.send(message)
        else:
            await inter.message.edit(content="No song has been played yet.")
    elif custom_id == "clear_chat":
        channel = inter.channel

        # Delete all messages in the channel
        await channel.purge()

        # Check if the bot is connected to a voice channel
        voice_client = get(bot.voice_clients, guild=inter.guild)
        if voice_client and voice_client.is_connected():
            # Disconnect the bot
            await voice_client.disconnect()

        # Send a response message indicating the chat has been cleared
        await inter.send("Chat cleared and bot disconnected.")
    elif custom_id == "show_queue":
        guild_id = inter.guild.id
        if guild_id in queues:
            queue = queues[guild_id]
            if not queue.is_empty():
                page_number = 1
                page_size = 10
                page_count = (queue.size() + page_size - 1) // page_size

                if page_number < 1 or page_number > page_count:
                    await inter.send("Invalid page number.")
                    return

                start_index = (page_number - 1) * page_size
                end_index = start_index + page_size
                queue_items_page = list(queue._queue)[start_index:end_index]

                queue_text = "\n".join([f"{start_index + i + 1}. {song.title}" if not isinstance(song, dict) else f"{start_index + i + 1}. {song['title']}" for i, song in enumerate(queue_items_page)])

                embed = disnake.Embed(
                    title="Music Queue",
                    description=queue_text,
                    color=disnake.Color.blue()
                )
                embed.set_footer(text=f"Page {page_number}/{page_count} | Songs {start_index + 1}-{end_index}/{queue.size()} | Requested by: {inter.user.display_name}")

                await inter.send(embed=embed)
            else:
                await inter.send("The song queue is empty.")
        else:
            await inter.send("The song queue is empty.")
    elif custom_id == "clear_queue":
        await _clear_queue(inter)  # Invoke the clear queue slash command
# |----------------------------------------------------------------------------------------------|
#other shit

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
    music_commands = [
        ("/play", "Play a song from YouTube or Spotify"),
        ("/stop", "Stop the currently playing song"),
        ("/next", "Skip to the next song in the queue"),
        ("/queue", "Show the current song queue"),
        ("/show_queue", "Show the current song queue"),
        ("/player", "Show information about the currently playing song"),
    ]
   


    embed = disnake.Embed(title="Help", description="List of available commands", color=disnake.Color.blue())

    embed.add_field(name="Music Commands:", value="\u200b", inline=False)
    for name, value in music_commands:
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


@bot.slash_command()
async def kill(ctx):
    # Check if the user has admin permissions
    if ctx.author.guild_permissions.administrator:
        await ctx.response.send_message("Killing bot and resetting all data...")
        data.clear()
        save_data()
        await bot.close()
    else:
        await ctx.response.send_message("You do not have permission to use this command.")

@bot.event
async def on_error(event, *args, **kwargs):
    import traceback
    error_message = traceback.format_exc()
    print(f"An error occurred: {error_message}")

    save_data()
    await bot.close()

def save_data():
    try:
        with open('data.json', 'w') as f:
            json.dump(data, f)
        print("Data saved successfully.")
    except Exception as e:
        print(f"Failed to save data: {e}")

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
