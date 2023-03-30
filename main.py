import discord
from discord import app_commands
import openai
from dotenv import load_dotenv
import os

load_dotenv()
bot_token = os.getenv('DISCORD_BOT_TOKEN')
guild_id = os.getenv('DISCORD_GUILD_ID') # use guild id for faster sync

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

openai.api_key = os.getenv('OPENAI_API_KEY')
model_id = 'gpt-3.5-turbo'

@tree.command(name = "chat", description = "Chat with the GPT-3.5 turbo (basically ChatGPT)", guild=discord.Object(id=guild_id))
async def chat(interaction, prompt: str):
    conversation = []
    # have fun prompt engineering here
    conversation.append({'role': 'system', 'content': 'How may I help you?'})
    conversation.append({'role': 'user', 'content': prompt})
    response = openai.ChatCompletion.create(
        model=model_id,
        messages=conversation
    )
    await interaction.response.send_message(response.choices[0].message.content)

@client.event
async def on_ready():
    await tree.sync(guild=discord.Object(id=guild_id))
    print("Ready!")

client.run(bot_token)