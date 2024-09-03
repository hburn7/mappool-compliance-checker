import logging
import logging.handlers
import os

import discord
import ossapi
from ossapi.enums import RankStatus
from discord import app_commands
from dotenv import load_dotenv
from ossapi import OssapiAsync, Beatmapset

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
@app_commands.checks.cooldown(10, 45)
async def validate(ctx, u_input: str):
    """Validates a mappool. Input should be a list of map IDs separated by commas, spaces, tabs, or new lines."""
    map_ids = sanitize(u_input)

    if len(map_ids) > 100:
        await ctx.response.send_message('Too many map IDs provided.')
        return

    if not map_ids:
        await ctx.response.send_message('Invalid input (map id collection empty).')
        return

    embed = discord.Embed()
    embed.colour = discord.Colour.blurple()
    embed.title = "Mappool verification result"

    try:
        beatmapsets, error_ids = await fetch_beatmapsets(map_ids)
        artists = set([b.artist for b in beatmapsets])
        dmca_sets = [b for b in beatmapsets if b.availability.download_disabled]
        artist_info = []

        for a in artists:
            if a in artist_data:
                artist_info.append(artist_data[a])
            else:
                artist_info.append(ArtistData(False, "", a, "unspecified", ""))

        embed.description = description(artist_info, beatmapsets, dmca_sets)

        await ctx.response.send_message(embed=embed)
    except ValueError as e:
        logger.warning(f'Invalid input [{e}].')
        await ctx.response.send_message(f'Invalid input [{e}].')
        return


@tree.error
async def on_app_command_error(interaction, error):
    if isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(f"Command is on cooldown. Try again in {error.retry_after:.2f} seconds.", ephemeral=True)


def description(artist_info: list[ArtistData], beatmapsets: list[Beatmapset], dmca_sets: list[Beatmapset] | None) -> str:
    s = ""

    if dmca_sets:
        s += "__**DMCA'd beatmapsets found:**__\n"
        for dmca_set in dmca_sets:
            s += f":warning: :bangbang: [{dmca_set.artist} - {dmca_set.title}](https://osu.ppy.sh/beatmapsets/{dmca_set.id})\n"

        s += "\n"

    ranked = [b for b in beatmapsets if (b.ranked == RankStatus.RANKED or b.ranked == RankStatus.APPROVED) and b not in dmca_sets]
    qualified = [b for b in beatmapsets if b.ranked == RankStatus.QUALIFIED and b not in dmca_sets]
    loved = [b for b in beatmapsets if b.ranked == RankStatus.LOVED and b not in dmca_sets]
    pending = [b for b in beatmapsets if (b.ranked == RankStatus.PENDING or b.ranked == RankStatus.WIP) and b not in dmca_sets]
    graveyard = [b for b in beatmapsets if b.ranked == RankStatus.GRAVEYARD and b not in dmca_sets]

    bypass = ranked + loved
    scrutinize = qualified + pending + graveyard

    disallowed = [x for x in artist_info if x.status == "false"]
    partial = [x for x in artist_info if x.status == "partial"]

    if bypass:
        s += "__**Ranked/Loved beatmapsets:**__\n"
        for b in bypass:
            if b in dmca_sets:
                continue

            icon = "💞" if b in loved else "✅"
            s += f"{icon} [{b.artist} - {b.title}](https://osu.ppy.sh/beatmapsets/{b.id})\n"

        s += "\n"

    if scrutinize:
        found_disallowed = []
        found_partial = []

        for b in scrutinize:
            if b in dmca_sets:
                continue

            if b.artist in disallowed:
                found_disallowed.append(b)
            elif b.artist in partial:
                found_partial.append(b)

        if found_disallowed:
            s += "__**Disallowed beatmapsets:**__\n"
            for b in found_disallowed:
                s += f"❌ [{b.artist} - {b.title}](https://osu.ppy.sh/beatmapsets/{b.id})\n"

            s += "\n"

        elif found_partial:
            s += "__**Partially disallowed beatmapsets:**__\n"
            for b in found_partial:
                partial = [x for x in artist_info if x.artist == b.artist][0]
                s += f":warning: [{b.artist} - {b.title}](https://osu.ppy.sh/beatmapsets/{b.id}) ({partial.notes})\n"

            s += "\n"

        remaining = [b for b in scrutinize if b not in found_disallowed and b not in found_partial]
        if remaining:
            s += "__**Pending/Graveyard beatmapsets:**__\n"
            for b in remaining:
                s += f":ballot_box_with_check: [{b.artist} - {b.title}](https://osu.ppy.sh/beatmapsets/{b.id})\n"

            s += "\n"

        if not found_disallowed and not found_partial and not dmca_sets:
            s += "__**No disallowed beatmapsets found! :partying_face:**__"

    return s


def sanitize(u_input: str) -> set[int]:
    ids = []

    # Split the input by commas, spaces, tabs, or new lines
    parts = (u_input
             .replace(',', ' ')
             .replace('\t', ' ')
             .replace('\n', ' ')
             .replace('#osu', '')
             .replace('#taiko', '')
             .replace('#fruits', '')
             .replace('#mania', '')
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


async def fetch_beatmapsets(ids: set[int]) -> (list[ossapi.Beatmapset], list[int]):
    """Fetches the beatmaps for the provided ids

    :param ids: A set of beatmap ids

    :return: A tuple containing a list of beatmapsets and a list of ids which were not found"""
    beatmaps = await oss_client.beatmaps(list(ids))
    returned_beatmapset_ids = set([b.beatmapset_id for b in beatmaps])

    all_ids = returned_beatmapset_ids | set([b.id for b in beatmaps])

    # Find beatmapsets of any ids which were not found here
    error_ids = ids - all_ids

    return [b.beatmapset() for b in beatmaps], error_ids


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
