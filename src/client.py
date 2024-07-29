import logging

import discord
import os
from dotenv import load_dotenv

import ossapi
from ossapi import OssapiAsync
from discord import app_commands

from validator import artist_data, ArtistData

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

load_dotenv()
client_id = int(os.getenv('CLIENT_ID'))
client_secret = os.getenv('CLIENT_SECRET')
bot_token = os.getenv('TOKEN')

oss_client = OssapiAsync(client_id, client_secret)


@client.event
async def on_ready():
    logging.info(f'Logged in as {client.user}')
    await tree.sync()

    logging.info('Commands synced, bot is ready!')


@tree.command(description="Validates a list of maps against osu!'s content-usage listing.")
async def validate(ctx, u_input: str):
    """Validates a mappool. Input should be a list of map IDs separated by commas, spaces, or tabs."""
    map_ids = sanitize(u_input)

    if not map_ids:
        await ctx.response.send_message('Invalid input (map id collection empty).')
        return

    embed = discord.Embed()
    embed.color = discord.Color.blurple()
    embed.title = "Mappool verification result"

    try:
        beatmapsets = await fetch_beatmapsets(map_ids)
        artists = set([b.artist for b in beatmapsets])
        relevant_data = []

        for a in artists:
            if a in artist_data:
                relevant_data.append(artist_data[a])
            else:
                relevant_data.append(ArtistData(False, "", a, "unspecified", ""))

        embed.description = description(relevant_data)

        await ctx.response.send_message(embed=embed)
    except ValueError as e:
        await ctx.response.send_message(f'Invalid input [{e}].')
        return


def description(artist_info: list[ArtistData]) -> str:
    s = ""

    disallowed = [x for x in artist_info if x.status == "false"]
    allowed = [x for x in artist_info if x.status == "true"]
    unspecified = [x for x in artist_info if x.status == "unspecified"]
    partial = [x for x in artist_info if x.status == "partial"]

    if disallowed:
        s += "__**Disallowed artists found:**__\n"
        for d in disallowed:
            s += f"❌ {d.markdown()}\n"

        s += "\n"

    if partial:
        s += "__**Partially allowed artists found:**__\n"
        for p in partial:
            s += f"⚠️{p.markdown()}\n"

        s += "\n"

    if unspecified:
        s += "__**Unspecified artists found:**__\n"
        for u in unspecified:
            s += f"❔ {u.markdown()}\n"

        s += "\n"

    if allowed:
        s += "__**Allowed artists found:**__\n"
        for a in allowed:
            s += f"✅ {a.markdown()}\n"

        s += "\n"

    return s


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
            if '/' in part:
                part = part.split('/')[-1]

            ids.append(int(part))
        except ValueError:
            # If any part is not an integer, return an empty list
            return set([])

    return set(ids)


async def fetch_beatmapsets(ids: set[int]) -> list[ossapi.Beatmapset]:
    """Fetches the beatmaps for the provided ids"""
    beatmaps = await oss_client.beatmaps(list(ids))
    return [b.beatmapset() for b in beatmaps]


def run():
    token = os.getenv('TOKEN')
    client.run(token)
