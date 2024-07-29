import discord
import logging
import logging.handlers
import os
import ossapi

from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
from ossapi import OssapiAsync

from validator import artist_data, ArtistData

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

load_dotenv()
client_id = int(os.getenv('CLIENT_ID'))
client_secret = os.getenv('CLIENT_SECRET')
bot_token = os.getenv('TOKEN')

oss_client = OssapiAsync(client_id, client_secret)

logger = logging.getLogger('client')


@client.event
async def on_ready():
    logger.info(f'Logged in as {client.user}')
    await tree.sync()

    logger.info('Commands synced, bot is ready!')


@tree.command(description="Validates a list of maps against osu!'s content-usage listing.")
@app_commands.checks.cooldown(1, 5, key=lambda x: (x.guild_id, x.user.id))
async def validate(ctx, u_input: str):
    """Validates a mappool. Input should be a list of map IDs separated by commas, spaces, tabs, or new lines."""
    map_ids = sanitize(u_input)

    if len(map_ids) > 50:
        await ctx.response.send_message('Too many map IDs provided.')
        return

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

    disallowed.sort(key=lambda x: x.artist)
    allowed.sort(key=lambda x: x.artist)
    unspecified.sort(key=lambda x: x.artist)
    partial.sort(key=lambda x: x.artist)

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
    if not os.path.exists('logs'):
        os.mkdir('logs')

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    handler = logging.handlers.RotatingFileHandler(
        filename='logs/discord.log',
        encoding='utf-8',
        maxBytes=32 * 1024 * 1024,  # 32 MiB
        backupCount=5  # Rotate through 5 files
    )
    dt_fmt = '%Y-%m-%d %H:%M:%S'
    formatter = logging.Formatter('[{asctime}] [{levelname:<8}] {name}: {message}', dt_fmt, style='{')
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)  # Reuse the same formatter
    root_logger.addHandler(console_handler)

    token = os.getenv('TOKEN')
    client.run(token, log_handler=None)
