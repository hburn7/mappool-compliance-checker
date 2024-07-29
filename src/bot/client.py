import discord
import os

from ossapi import Ossapi
from discord import app_commands

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

client_id = int(os.getenv('CLIENT_ID'))
client_secret = os.getenv('CLIENT_SECRET')
bot_token = os.getenv('TOKEN')


@client.event
async def on_ready():
    print(f'Logged in as {client.user}')
    await tree.sync()

    print('Commands synced, bot is ready!')


@tree.command(description="Validates a list of maps against osu!'s content-usage listing.")
async def validate(ctx, u_input: str):
    """Validates a mappool. Input should be a list of map IDs separated by commas, spaces, or tabs."""
    map_ids = sanitize(u_input)

    if not map_ids:
        await ctx.response.send_message('Invalid input (map id collection empty).')
        return

    await ctx.response.send_message(f'Validating {len(map_ids)} maps...')


def sanitize(u_input: str) -> set[int]:
    ids = []

    # Split the input by commas, spaces, tabs, or new lines
    parts = (u_input
             .replace(',', ' ')
             .replace('\t', ' ')
             .replace('\n', ' ')
             .split())

    for part in parts:
        try:
            # Try to convert each part to an integer
            ids.append(int(part))
        except ValueError:
            # If any part is not an integer, return an empty list
            return set([])

    return set(ids)


def oss_client() -> Ossapi:
    return Ossapi(client_id, client_secret)


def run():
    token = os.getenv('TOKEN')
    client.run(token)
