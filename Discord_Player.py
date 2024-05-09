from discord.ext import commands
from discord import voice_client
from dotenv import load_dotenv
import os
import typing
import discord 
import yt_dlp
import nacl
import asyncio
import json
from collections import defaultdict
from discord import ui
from youtube_search import YoutubeSearch
#from discord_ui import Components

 
def run_bot():
   
    TOKEN = "" 
    #load_dotenv()
    #TOKEN = os.getenv('discord_token')
    intents = discord.Intents.default()
    intents.message_content = True
    client = commands.Bot(command_prefix="!", intents=intents)
    voice_clients = {}
    queues = defaultdict(list)
    yt_dl_options = {"format": "bestaudio/best", 'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'm4a'}]}
    ytdl = yt_dlp.YoutubeDL(yt_dl_options)
    ffmpeg_options = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5','options': '-vn -filter:a "volume=0.25"'}

    #check that bot is running
    @client.event
    async def on_ready():
        print(f'{client.user} is now jamming')
    
    #play next song
    async def play_next(ctx):
       try:
            if queues[ctx.guild.id]!= []:
                link = queues[ctx.guild.id][0].pop(0)
                global repeat_songs
                if repeat_songs == 1:await queue(ctx,link) 
                await play(ctx, link)
       except Exception as e:
            print(e)
            
    #main command:play
    @client.command(name="play")
    async def play(ctx, link):
        try:
            if ctx.author.voice is None: return await ctx.send("Get in a voice channel first...")
            voice_client = await ctx.author.voice.channel.connect()
            voice_clients[ctx.guild.id] = voice_client
        except Exception as e:
            print(e)
        
        try:
            if link.find("http") == -1:
                result = YoutubeSearch(ctx.message.content,max_results = 20).to_dict()
                link = "https://www.youtube.com" + result[0]['url_suffix']
            
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None,lambda: ytdl.extract_info(link, download=False))
            song = data['url']
       
            player = discord.FFmpegOpusAudio(song, **ffmpeg_options)

            if voice_clients[ctx.guild.id].is_playing(): 
               await queue(ctx,song)
            else:
               global current_song
               current_song = link
               voice_clients[ctx.guild.id].play(player, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), client.loop))
        except Exception as e:
            print(e)
    
    #clear queue
    @client.command(name="clear_queue")
    async def clear_queue(ctx):
        if ctx.guild.id in queues:
            queues[ctx.guild.id][0].clear()
            await ctx.send("Queue cleared!")
        else:
            await ctx.send("There is no queue to clear!")
    
    #repeat queue
    @client.command(name = "repeat")
    async def repeat(ctx):
        global repeat_songs
        global current_song
        repeat_songs = abs(repeat_songs-1)
        if repeat_songs == 1:
            await queue(ctx,current_song)
            await ctx.send("repeated now")
        else: 
            await ctx.send("don't repeated now")
    
    #pause bot
    @client.command(name="pause")
    async def pause(ctx):
        try:
            voice_clients[ctx.guild.id].pause()
        except Exception as e:
            print(e)
   
    #resume
    @client.command(name="resume")
    async def resume(ctx):
        try:
            voice_clients[ctx.guild.id].resume()
        except Exception as e:
            print(e)
    
    #skip
    @client.command(name="skip")
    async def skip(ctx):
        try:
            if voice_clients[ctx.guild.id].is_playing():
               voice_clients[ctx.guild.id].stop()
               await play_next(ctx)
        except Exception as e:
            print(e)
    
    #stops bot
    @client.command(name="stop")
    async def stop(ctx):
        try:
            global repeat_songs
            repeat_songs = 0
            await clear_queue(ctx)
            voice_clients[ctx.guild.id].stop()
            client.loop.close()
            
            #await voice_clients[ctx.guild.id].disconnect()
            #del voice_clients[ctx.guild.id]
        except Exception as e:
            print(e)

    #add to queue
    async def queue(ctx, url):
        #if key does not exists
        if ctx.guild.id not in queues:
            queues[ctx.guild.id].append([])
        queues[ctx.guild.id][0].append(url)
    
    #getting queue list 
    @client.command(name="get")
    async def get(ctx):
        if ctx.guild.id in queues:
          for u in queues[ctx.guild.id][0]:
             await ctx.send(u)

    client.run(TOKEN)

#global vars
current_song = None
repeat_songs = 0
from_queue = 0
run_bot()


