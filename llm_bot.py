"""Discord bot for robotics integration and command handling."""
import os
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables from .env file
load_dotenv()
TOKEN = os.getenv('DISCORD_BOT_TOKEN') # This should match what you put in .env

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables.")

genai.configure(api_key=GEMINI_API_KEY)

# Define intents (important!)
# Define specific intents
# Set all intents to False by default, then enable the ones you need
intents = discord.Intents.default() # Start with no intents enabled

# Guilds intent is necessary for most bots to even function on servers
# (e.g., to know which server the message came from)
# Message content intent is crucial if your bot reads message content
# (e.g., for prefix commands, or reacting to keywords)
intents.message_content = True
intents.guilds = True

# Initialize the bot client
# For prefix commands (e.g., !hello), use commands.Bot
bot = commands.Bot(command_prefix='!', intents=intents) # Your bot's prefix

model = genai.GenerativeModel('gemini-pro')

# --- NEW: Function to list available Gemini models ---
async def list_gemini_models():
    """Lists available Gemini models that support generateContent."""
    print("\n--- Available Gemini Models supporting 'generateContent' ---")
    found_models = False
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"- {m.name}")
            found_models = True
    if not found_models:
        print("No models found that support 'generateContent'.")
    print("---------------------------------------------------------")

@bot.event
async def on_ready():
    """Event: Bot is ready"""
    print(f'{bot.user} has connected to Discord!')
    print(f'Logged in as {bot.user.name} ({bot.user.id})')
    # You can set the bot's activity here, e.g.,
    await bot.change_presence(activity=discord.Game(name="with robots!"))
 # --- Call the model listing function here ---
    await list_gemini_models()

    # --- IMPORTANT: Update your model name here based on the output of list_gemini_models() ---
    # For example, if list_gemini_models() prints "models/gemini-1.5-flash", use that.
    # A common and stable model that supports generateContent is often 'gemini-1.5-pro'
    # or 'gemini-1.5-flash'
    global model
    try:
        # Prioritize 'gemini-1.5-pro' if available, otherwise try 'gemini-1.5-flash'
        # You'll need to check the exact names printed by list_gemini_models()
        model_name_to_use = None
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                if m.name == 'models/gemini-1.5-pro':
                    model_name_to_use = 'gemini-1.5-pro'
                    break
                elif m.name == 'models/gemini-1.5-flash':
                    model_name_to_use = 'gemini-1.5-flash'
                    # Don't break yet, still prefer pro if it appears later
        if model_name_to_use:
            model = genai.GenerativeModel(model_name_to_use)
            print(f"Using Gemini model: {model_name_to_use}")
        else:
            #print("No suitable Gemini model found that supports 'generateContent'.
            # Please check your API key and region.")
            # Optionally, you can raise an error or disable the !ask command here
            raise ValueError("No suitable Gemini model found.")

    except Exception as e:
        print(f"Failed to initialize Gemini model: {e}")
        # Optionally, you can raise an error or disable the !ask command here

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
    """print error messages"""
    print(f'Error: {error}')

@bot.event
async def on_message(message):
    """print useful information about received messages"""
        # Ignore messages from the bot itself to prevent infinite loops
    if message.author == bot.user:
        return
    print(f"Received message: {message.content}")
    print(f"From user: {message.author} in channel: {message.channel} (Guild: {message.guild})")
    # Critical: allows command decorators like @bot.command to still work
    await bot.process_commands(message)

# Helper function to split long messages
async def send_long_message(channel, text):
    """Sends a long message by splitting it into chunks if it exceeds Discord's limit."""
    if len(text) <= 2000:
        await channel.send(text)
        return

    chunks = []
    current_chunk = ""
    for line in text.splitlines(True): # splitlines(True) keeps newlines
        if len(current_chunk) + len(line) <= 2000:
            current_chunk += line
        else:
            chunks.append(current_chunk)
            current_chunk = line
    if current_chunk: # Add the last chunk
        chunks.append(current_chunk)

    for chunk in chunks:
        if chunk.strip(): # Avoid sending empty chunks
            await channel.send(chunk)
            await asyncio.sleep(0.5) # Add a small delay to avoid hitting Discord rate limits

@bot.command(name='ask')
async def ask_gemini(ctx, *, question: str):
    """
    Asks the Gemini API a question and responds with the generated answer.
    Usage: !ask What is the capital of France?
    """
    try:
        await ctx.send("Thinking...") # Let the user know the bot is working

        # Generate content using Gemini
        response = model.generate_content(question)

        # Check if response.text exists and handle potential safety blocks
        if hasattr(response, 'text') and response.text:
            await send_long_message(ctx.channel, response.text)
        elif response.prompt_feedback and response.prompt_feedback.safety_ratings:
            # If the response was blocked due to safety settings
            safety_issues = []
            for rating in response.prompt_feedback.safety_ratings:
                if rating.blocked:
                    safety_issues.append(f"{rating.category.name}: BLOCKED (Threshold: {rating.threshold.name})")
                elif rating.probability > rating.threshold: # If it's over threshold but not blocked (unlikely for blocked responses but good check)
                    safety_issues.append(f"{rating.category.name}: {rating.probability.name} (Threshold: {rating.threshold.name})")
            if safety_issues:
                await ctx.send(
                    f"My response was blocked due to safety concerns. "
                    f"Details: {', '.join(safety_issues)}\n"
                    f"Please try rephrasing your question."
                )
            else:
                await ctx.send("I couldn't generate a response for that, possibly due to an internal issue or content that couldn't be processed.")
        else:
            await ctx.send("I couldn't generate a response for that question.")

    except Exception as e:
        # More specific error handling for Gemini API
        if "BlockedReason" in str(e): # A common indicator for safety blocks if prompt_feedback isn't enough
            await ctx.send(
                "I couldn't process that request due to potential safety concerns with the prompt itself. "
                "Please try rephrasing your question."
            )
        else:
            await ctx.send(f"An error occurred while communicating with Gemini: {e}")
            print(f"Gemini API Error: {e}") # Log the full error for debugging
# Run the bot
if TOKEN is None:
    raise ValueError("DISCORD_BOT_TOKEN not found in environment variables.")
bot.run(TOKEN)
