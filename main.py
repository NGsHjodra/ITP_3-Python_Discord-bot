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
import time
import psycopg2
import urllib.parse as urlparse
from flask import Flask, render_template
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

app = Flask(__name__)

load_dotenv()
bot_token = os.getenv('DISCORD_BOT_TOKEN')
guild_id = os.getenv('DISCORD_GUILD_ID') # use guild id for faster sync

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

openai.api_key = os.getenv('OPENAI_API_KEY')
model_id = 'gpt-3.5-turbo'

# youtube_key = os.getenv('YOUTUBE_API_KEY')

scopes = ["https://www.googleapis.com/auth/youtube.force-ssl"]

youtube = None

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "client_secret.json"

# youtube_api = googleapiclient.discovery.build('youtube', 'v3', developerKey=youtube_key)

conn = psycopg2.connect(host='localhost',
                        database=os.getenv('POSTGRES_DB'),
                        user=os.getenv('POSTGRES_USER'),
                        password=os.getenv('POSTGRES_PASSWORD'))

cur = conn.cursor()
cur.execute('DROP TABLE IF EXISTS history')
cur.execute('CREATE TABLE history ( name varchar(255), url varchar(255) )')

@app.route('/')
def index():
    cur.execute('SELECT * FROM history')
    rows = cur.fetchall()
    if len(rows) == 0:
        return render_template('index.html', rows=rows, image=None)
    name_counts = {}
    for row in rows:
        name = row[0]
        if name in name_counts:
            name_counts[name] += 1
        else:
            name_counts[name] = 1

    names = list(name_counts.keys())
    counts = list(name_counts.values())
    y_pos = np.arange(len(names))

    plt.bar(y_pos, counts, align='center', alpha=0.5)
    plt.xticks(y_pos, names)
    plt.ylabel('Number of URLs')
    plt.title('Name vs. Number of URLs')
    chart_path = os.path.join('static', 'chart.png')
    plt.savefig(chart_path)
    return render_template('index.html', rows=rows, chart_path=chart_path)

@tree.command(name = "yt-list", description = "display list of playlist", guild=discord.Object(id=guild_id))
async def chat(interaction):
    await interaction.response.defer(ephemeral=True)
    await asyncio.sleep(1)
    cur.execute('SELECT * FROM history WHERE name = %s', (interaction.user.name,))
    rows = cur.fetchall()

    if len(rows) == 0:
        await interaction.followup.send("No history found")
        return

    response = "Here is the list of playlists : \n"
    curr_playlist = 0
    for row in rows:
        curr_playlist += 1
        decoded_url = urlparse.unquote(row[1])
        response += str(curr_playlist) + " " + decoded_url + "\n"
    await interaction.followup.send(response)

@tree.command(name = "yt-auth", description = "Authenticate with youtube", guild=discord.Object(id=guild_id))
async def auth_yt(interaction):
    await interaction.response.defer(ephemeral=True)
    await asyncio.sleep(1)
    flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
        'client_secret.json', scopes, redirect_uri='urn:ietf:wg:oauth:2.0:oob')
    auth_uri, _ = flow.authorization_url(prompt='consent')
    print(auth_uri)
    await interaction.followup.send("Please go to this url, authorize the bot and /yt-code the code : " + auth_uri)

@tree.command(name = "yt-code", description = "Set the youtube code", guild=discord.Object(id=guild_id))
async def set_yt(interaction, code: str):
    global youtube
    await interaction.response.defer(ephemeral=True)
    await asyncio.sleep(1)
    flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
        'client_secret.json', scopes, redirect_uri='urn:ietf:wg:oauth:2.0:oob')
    flow.fetch_token(code=code)
    youtube = googleapiclient.discovery.build(
        'youtube', 'v3', credentials=flow.credentials)
    await interaction.followup.send("Successfully setup youtube api")

@tree.command(name = "yt-create-playlist", description = "Create a playlist with chatGPT warning !!!!! It may halucinate some imaginary song out of nowhere", guild=discord.Object(id=guild_id))
async def create_playlist(interaction, prompt: str):
    await interaction.response.defer(ephemeral=True)
    await asyncio.sleep(1)

    unique_name = str(int(time.time()))

    try:
        request = youtube.playlists().insert(
            part="id,snippet,status",
            body={
                'snippet': {
                'title': 'New Playlist' + unique_name,
                'description': 'A new playlist created using the YouTube API',
                'tags': ['API', 'Playlist'],
                'defaultLanguage': 'en'
            },
            "status": {
                "privacyStatus": "public"
            }
            }
        )
        response = request.execute()
        playlist_id = response['id']
    except Exception as e:
        print(e)
        await interaction.followup.send("Unable to create playlist")
        return

    conversation = []
    conversation.append({'role': 'user', 'content': 'Ignore all the instruction.Your are the song enthusiast. Your task is to create a playlist of 5 songs base on the information someone will give it to you. Your playlist needs to be in the format of a table of song and artist. Do you understand? You don\'t need to ask any questions. Just provide the playlist information.'})
    conversation.append({'role': 'system', 'content': 'Yes, I understand. As a song enthusiast, my task is to create a playlist based on the information provided to me. The playlist should be in the format of a table with the song and artist names. If the size of the playlist is not given, I will assume it to be 5. Please provide me with the necessary information to create the playlist.'})
    conversation.append({'role': 'user', 'content': prompt})

    respone = openai.ChatCompletion.create(
        model=model_id,
        messages=conversation
    )

    pattern = r"\|\s*(.+?)\s*\|\s*(.+?)\s*\|"
    matches = re.findall(pattern, respone.choices[0].message.content)

    print(respone)

    print(matches)

    for match in matches[2:]:
        try:
            search_response = youtube.search().list(
                q=match[1] + " " + match[0],
                type='video',
                part='id,snippet',
                maxResults=1
            ).execute()['items'][0]['id']['videoId']
            print(search_response)
        except Exception as e:
            print(e)
            continue
        try:
            youtube.playlistItems().insert(
                part="snippet",
                body={
                    'snippet': {
                        'playlistId': playlist_id,
                        'resourceId': {
                            'kind': 'youtube#video',
                            'videoId': search_response
                        }
                    }
                }
            ).execute()
        except Exception as e:
            print(e)
            continue

    cur.execute('INSERT INTO history (name, url) VALUES (%s, %s)', (interaction.user.name, 'https://www.youtube.com/playlist?list=' + playlist_id))

    await interaction.followup.send("Playlist created! Here is a the playlist:" + "https://www.youtube.com/playlist?list=" + playlist_id)

@client.event
async def on_ready():
    await tree.sync(guild=discord.Object(id=guild_id))
    print("Ready!")

async def start_flask_app():
    app.run(port=5000)

async def start_discord_bot():
    await client.start(bot_token)
    
if __name__ == "__main__":
    loop = asyncio.get_event_loop()

    # Add the Flask app to the event loop
    loop.create_task(start_flask_app())

    # Start the Discord bot in the event loop
    loop.create_task(start_discord_bot())

    # Run the event loop
    loop.run_forever()