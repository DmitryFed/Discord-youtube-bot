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
 


class SearchButton(discord.ui.Button):
    def __init__(self, label, style,button_id,rownum):
        super().__init__(label = label, style = style,custom_id = button_id, row = rownum)

    #async def callback(self,interaction,ctx=None):
    #             message = self.custom_id
    #             await interaction.response.send_message(message)

   
class SearchView(discord.ui.View):
    def __init__(self):
        super().__init__()  

    def createButton(self,label,button_id,rownum):
        button = SearchButton(label = label, button_id = button_id, style = discord.ButtonStyle.primary, rownum = rownum)
        self.add_item(button)

class Queue:

    __queue = []

    def enqueue(self,item):
        self.__queue.append(item)

    def dequeue(self):
        return self.__queue.pop(0)
    
    def insertTo(self,index,item):
        self.__queue.insert(index,item)

    def clear(self):
        self.__queue.clear()

    def getQueue(self):
        return self.__queue
    
    def count(self):
        return len(self.__queue)

    def removeFromIndex(self,index):
        self.__queue.pop(index)
   

class YoutubeDownloader(yt_dlp.YoutubeDL):
   
   __ytdl_options = None
   
   def __init__(self,options):
       self.__ytdl_options = options
       super().__init__(options)

   def getOptionValue(self,key):
       return self.__ytdl_options[key]
   
   def setOptionValue(self,key,value):
       self.__ytdl_options[key] = value



class DiscordPlayer(discord.FFmpegOpusAudio):
    
    def __init__(self,audioSource,options):
        super().__init__(source = audioSource, options = options)

   
class VoiceClient(discord.VoiceClient):
    
    #sources for playing
    queue = Queue()
    
    def connect(self,VoiceChannel):
        self = VoiceChannel.connect()
        return self
    
    def addForPlay(self,source):
        self.queue.enqueue(source)

    #def delFromQueue(self,number):
    #    self.queue.

class MusicBot(commands.Bot):
        
    queue = Queue()
    __VoiceClients = {}
   # __srchView = SearchView()

    def __init__(self,options,intents = discord.Intents.default(),commandPrefix ='!'):
        intents.message_content = True
        super().__init__(intents = intents, command_prefix = commandPrefix)
        
   
    def __addVoiceClient(self,guild_id,voice_client):
        if guild_id not in self.__VoiceClients:
            self.__VoiceClients[guild_id] = voice_client
        
    def getVoiceClientByGuildId(self,guild_id):
        return self.__VoiceClients[guild_id]

    def playInChannel(self,player,guild_id):
        self.__VoiceClients[guild_id].play(player, after = lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), self.loop))
    
    def run(self,token):
        self.run(token)
    
    def getSourceByTitle(self,ctx):
        result = YoutubeSearch(ctx.message.content,max_results = 1).to_dict()
        link = "https://www.youtube.com" + result[0]['url_suffix']
        return link
        


def run_bot():

    load_dotenv()
    TOKEN = os.getenv('discord_music_bot_token')
    intents = discord.Intents.default()
    intents.message_content = True
    client = commands.Bot(command_prefix="!", intents=intents)
    voice_clients = {}
    queues = defaultdict(list)
    yt_dl_options = {"format": "bestaudio/best", 'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'm4a'}]}
    ytdl = yt_dlp.YoutubeDL(yt_dl_options)
    ffmpeg_options = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5','options': '-vn -filter:a "volume=0.25"'}


    @client.event
    async def on_interaction(interaction):
        if interaction.type[1] == 3:
            ctx = await client.get_context(interaction.message)
            ctx.author = interaction.user
            await play(ctx,interaction.data['custom_id'])
        
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
            #if ctx.author.voice is None: return await ctx.send("Get in a voice channel first...")
            voice_client = await ctx.author.voice.channel.connect()
            voice_clients[ctx.guild.id] = voice_client
        except Exception as e:
            print(e)
        
        try:
            if link.find("http") == -1:
                result = YoutubeSearch(ctx.message.content,max_results = 1).to_dict()
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
            #await clear_queue(ctx)
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

    @client.command("search")
    async def search(ctx):
        row = 0
        searchview = SearchView()

        lstofbuttons = []
        results = YoutubeSearch(ctx.message.content,max_results = 5).to_dict()

        for result in results:
           label = result['title']
           identifier = "https://www.youtube.com" + result['url_suffix']
           searchview.createButton(label,identifier,row)
           row +=1
        await ctx.reply("Choose the title:",view = searchview)
    
       

    client.run(TOKEN)

global vars
current_song = None
repeat_songs = 0
from_queue = 0
run_bot()
