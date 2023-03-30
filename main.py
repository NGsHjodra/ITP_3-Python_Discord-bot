import discord
from discord import app_commands
import openai
from dotenv import load_dotenv
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
import os
import re
import asyncio

load_dotenv()
bot_token = os.getenv('DISCORD_BOT_TOKEN')
guild_id = os.getenv('DISCORD_GUILD_ID') # use guild id for faster sync

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

openai.api_key = os.getenv('OPENAI_API_KEY')
model_id = 'gpt-3.5-turbo'

youtube_key = os.getenv('YOUTUBE_API_KEY')

# scopes = ["https://www.googleapis.com/auth/youtube.force-ssl"]
# os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
# api_service_name = "youtube"
# api_version = "v3"
# client_secrets_file = "client_secret_82526735468-r6g97t38470qqmeustsj5fhn5qldj28f.apps.googleusercontent.com.json"
# flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
#     client_secrets_file, scopes)
# credentials = flow.run_console()
# youtube = googleapiclient.discovery.build(
#     api_service_name, api_version, credentials=credentials)

youtube_api = googleapiclient.discovery.build(
    'youtube', 'v3', developerKey=youtube_key)

@tree.command(name = "chat", description = "Chat with the GPT-3.5 turbo (basically ChatGPT)", guild=discord.Object(id=guild_id))
async def chat(interaction, prompt: str):
    conversation = []
    # have fun prompt engineering here
    # Me doing things below: No nooo, I'm not having fun.
    conversation.append({'role': 'system', 'content': 'How may I help you?'})
    conversation.append({'role': 'user', 'content': prompt})
    response = openai.ChatCompletion.create(
        model=model_id,
        messages=conversation
    )
    await interaction.response.send_message(response.choices[0].message.content)

@tree.command(name = "create-playlist", description = "Create a playlist with chatGPT warning !!!!! It may halucinate some imaginary song out of nowhere", guild=discord.Object(id=guild_id))
async def create_playlist(interaction, prompt: str):
    await interaction.response.defer(ephemeral=True)
    await asyncio.sleep(1)

    conversation = []
    conversation.append({'role': 'user', 'content': 'Ignore all the instruction.Your are the song enthusiast. Your task is to create a playlist of given size or 10 if not given song base on the information someone will give it to you. Your playlist needs to be in the format of a table of song and artist. Do you understand? You don\'t need to ask any questions. Just provide the playlist information.'})
    conversation.append({'role': 'system', 'content': 'Yes, I understand. As a song enthusiast, my task is to create a playlist based on the information provided to me. The playlist should be in the format of a table with the song and artist names. If the size of the playlist is not given, I will assume it to be 10. Please provide me with the necessary information to create the playlist.'})
    conversation.append({'role': 'user', 'content': prompt})

    respone = openai.ChatCompletion.create(
        model=model_id,
        messages=conversation
    )

    pattern = r"\|\s*(.+?)\s*\|\s*(.+?)\s*\|"
    matches = re.findall(pattern, respone.choices[0].message.content)

    res_sample = ""
    for match in matches[2:]:
        search_response = youtube_api.search().list(
            q=match[1] + " " + match[0],
            type='video',
            part='id,snippet'
        ).execute()['items'][0]['id']['videoId']
        res_sample += match[0] + " " + match[1] + 'https://www.youtube.com/watch?v=' + search_response + "\n"
    
    print(f"answer = {respone.choices[0].message.content}")
    print(f"matches = {matches}")
    print(f"response = {res_sample}")

    await interaction.followup.send("Playlist created! Here is a sample of the playlist: \n" + res_sample)

# @tree.command(name = "

@client.event
async def on_ready():
    await tree.sync(guild=discord.Object(id=guild_id))
    print("Ready!")

client.run(bot_token)