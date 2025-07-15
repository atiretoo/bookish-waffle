"""Discord bot for robotics integration and command handling."""
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
TOKEN = os.getenv('DISCORD_BOT_TOKEN') # This should match what you put in .env

# Define intents (important!)
# Define specific intents
# Set all intents to False by default, then enable the ones you need
intents = discord.Intents.none() # Start with no intents enabled

# Guilds intent is necessary for most bots to even function on servers
# (e.g., to know which server the message came from)
intents.guilds = True

# Message content intent is crucial if your bot reads message content
# (e.g., for prefix commands, or reacting to keywords)
intents.message_content = True
intents.guilds = True
#intents = discord.Intents.default() # Start with default intents

# Initialize the bot client
# For prefix commands (e.g., !hello), use commands.Bot

bot = commands.Bot(command_prefix='!', intents=intents) # Your bot's prefix

# Event: Bot is ready
@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    print(f'Logged in as {bot.user.name} ({bot.user.id})')
    # You can set the bot's activity here, e.g.,
    await bot.change_presence(activity=discord.Game(name="with robots!"))

# Command: A simple 'hello' command
@bot.command(name='hello')
async def hello(ctx):
    """Responds with a friendly greeting."""
    await ctx.send(f'Hello there, {ctx.author.mention}!')

# Command: A simple 'ping' command
@bot.command(name='ping')
async def ping(ctx):
    """Responds with Pong! and latency."""
    await ctx.send(f'Pong! {round(bot.latency * 1000)}ms')

@bot.event
async def on_command_error(ctx, error):# pylint: disable=unused-argument

    print(f'Error: {error}')

@bot.event
async def on_message(message):
    print(f"Received message: {message.content}")
    print(f"From user: {message.author} in channel: {message.channel} (Guild: {message.guild})")
    # Critical: allows command decorators like @bot.command to still work
    await bot.process_commands(message)  

# Run the bot
bot.run(TOKEN)
