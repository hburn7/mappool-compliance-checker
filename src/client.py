import logging
import logging.handlers
import os

import discord
import ossapi
from discord import app_commands, Embed
from dotenv import load_dotenv
from ossapi import OssapiAsync, Beatmapset
from ossapi.enums import RankStatus
from reactionmenu import ViewMenu, ViewButton

import validator

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.reactions = True
intents.members = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

load_dotenv()
client_id = int(os.getenv('CLIENT_ID'))
client_secret = os.getenv('CLIENT_SECRET')
bot_token = os.getenv('TOKEN')

oss_client = OssapiAsync(client_id, client_secret)

logger = logging.getLogger('client')

PAGE_SIZE = 25


@client.event
async def on_ready():
    logger.info(f'Logged in as {client.user}')
    await tree.sync()

    logger.info('Commands synced, bot is ready!')


def line_item_dmca(beatmapset: Beatmapset) -> str:
    return f"⛔ [{beatmapset.artist} - {beatmapset.title}](https://osu.ppy.sh/beatmapsets/{beatmapset.id})"

def line_item_disallowed(beatmapset: Beatmapset) -> str:
    return f"❌ [{beatmapset.artist} - {beatmapset.title}](https://osu.ppy.sh/beatmapsets/{beatmapset.id})"

def line_item_partial(beatmapset: Beatmapset) -> str:
    key = validator.flag_key_match(beatmapset.artist)
    notes = validator.flagged_artists[key].notes if key is not None else None
    s = f":warning: [{beatmapset.artist} - {beatmapset.title}](https://osu.ppy.sh/beatmapsets/{beatmapset.id})"

    if notes is not None:
        s += f" - {notes}"

    return s

def line_item_allowed_unranked(beatmapset: Beatmapset) -> str:
    return f":ballot_box_with_check: [{beatmapset.artist} - {beatmapset.title}](https://osu.ppy.sh/beatmapsets/{beatmapset.id})"

def line_item_allowed_ranked(beatmapset: Beatmapset) -> str:
    return f"✅ [{beatmapset.artist} - {beatmapset.title}](https://osu.ppy.sh/beatmapsets/{beatmapset.id})"

def line_item_allowed_loved(beatmapset: Beatmapset) -> str:
    return f"💞 [{beatmapset.artist} - {beatmapset.title}](https://osu.ppy.sh/beatmapsets/{beatmapset.id})"

def embeds_from_line_items(title, line_items: list[str], color: discord.Color) -> list[Embed]:
    embeds = []
    for i in range(0, len(line_items), PAGE_SIZE):
        embed = discord.Embed(title=title, color=color)
        embed.description = '\n'.join(line_items[i:i + PAGE_SIZE])
        embeds.append(embed)

    return embeds

def page_count(n: int) -> int:
    # 1 page per PAGE_SIZE items
    return n // PAGE_SIZE + 1

def dmca_sets_embeds(dmca: list[Beatmapset]) -> list[Embed]:
    line_items = [line_item_dmca(b) for b in dmca]
    return embeds_from_line_items("DMCA'd beatmapsets found", line_items, discord.Color.red())

def disallowed_sets_embeds(disallowed: list[Beatmapset]) -> list[Embed]:
    line_items = [line_item_disallowed(b) for b in disallowed]
    return embeds_from_line_items("Disallowed beatmapsets found", line_items, discord.Color.red())

def partial_sets_embeds(partial: list[Beatmapset]) -> list[Embed]:
    line_items = [line_item_partial(b) for b in partial]
    return embeds_from_line_items("Partially disallowed beatmapsets found", line_items, discord.Color.yellow())

def allowed_graveyard_sets_embeds(graveyard: list[Beatmapset]) -> list[Embed]:
    line_items = [line_item_allowed_unranked(b) for b in graveyard]
    return embeds_from_line_items("Pending/Graveyard beatmapsets found", line_items, discord.Color.blurple())

def ranked_sets_embeds(ranked: list[Beatmapset]) -> list[Embed]:
    line_items = [line_item_allowed_loved(b) if b.status == RankStatus.LOVED else line_item_allowed_ranked(b) for b in ranked]
    return embeds_from_line_items("Ranked/Loved beatmapsets found", line_items, discord.Color.green())

def dmca_sets(beatmapsets: list[Beatmapset]) -> list[Beatmapset]:
    return [b for b in beatmapsets if b.availability.more_information is not None or b.availability.download_disabled]

def count_graveyard(beatmapsets: list[Beatmapset]) -> int:
    return len([b for b in beatmapsets if b.status not in [RankStatus.RANKED, RankStatus.LOVED, RankStatus.APPROVED]])

def count_ranked(beatmapsets: list[Beatmapset]) -> int:
    return len([b for b in beatmapsets if b.status == RankStatus.RANKED or b.status == RankStatus.LOVED or b.status == RankStatus.APPROVED])

def count_allowed(beatmapsets: list[Beatmapset]) -> int:
    return len([b for b in beatmapsets if validator.is_allowed(b)])

def count_disallowed(beatmapsets: list[Beatmapset]) -> int:
    return len([b for b in beatmapsets if not validator.is_allowed(b)])

def count_partial(beatmapsets: list[Beatmapset]) -> int:
    return len([b for b in beatmapsets if validator.is_partial(b)])

def count_dmca(beatmapsets: list[Beatmapset]) -> int:
    return len(dmca_sets(beatmapsets))

def menu(interaction: discord.Interaction, beatmapsets: list[Beatmapset], dmca: list[Beatmapset]) -> ViewMenu:
    allowed = sorted([b for b in beatmapsets if validator.is_allowed(b)], key=lambda b: b.artist)
    partial = [b for b in beatmapsets if validator.is_partial(b)]
    disallowed = [b for b in beatmapsets if validator.is_disallowed(b)]

    ranked = [b for b in allowed if b.status == RankStatus.RANKED or b.status == RankStatus.LOVED or b.status == RankStatus.APPROVED]
    graveyard = [b for b in allowed if b not in ranked]

    dmca_count = count_dmca(beatmapsets)
    disallowed_count = count_disallowed(disallowed)
    partial_count = count_partial(partial)
    graveyard_count = count_graveyard(allowed)
    ranked_count = count_ranked(allowed)

    view_menu = ViewMenu(interaction, menu_type=ViewMenu.TypeEmbed)
    pages = []

    if dmca_count > 0:
        pages += dmca_sets_embeds(dmca)

    if disallowed_count > 0:
        pages += disallowed_sets_embeds(disallowed)

    if partial_count > 0:
        pages += partial_sets_embeds(partial)

    if graveyard_count > 0:
        pages += allowed_graveyard_sets_embeds(graveyard)

    if ranked_count > 0:
        pages += ranked_sets_embeds(ranked)

    for page in pages:
        page.set_footer(text='️⛔: %d | ❌: %d | ⚠️%d | ☑️: %d | ✅ / 💞: %d' %
                             (dmca_count, disallowed_count, partial_count, graveyard_count, ranked_count))

    view_menu.add_pages(pages)
    view_menu.add_button(ViewButton.back())
    view_menu.add_button(ViewButton.next())

    return view_menu


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
    # Split ids into batches of 30 maps
    id_sets = [list(ids)[i:i + 30] for i in range(0, len(ids), 30)]
    beatmaps = []

    for set_ in id_sets:
        beatmaps += await oss_client.beatmaps(list(set(set_)))

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


@tree.command(description="Validates a list of maps against osu!'s content-usage listing.")
@app_commands.checks.cooldown(10, 45)
async def validate(ctx: discord.Interaction, u_input: str):
    """Validates a mappool. Input should be a list of map IDs separated by commas, spaces, tabs, or new lines."""
    await ctx.response.defer()  # For interactions, use ctx.response.defer()
    map_ids = sanitize(u_input)

    if len(map_ids) > 200:
        await ctx.followup.send('Too many map IDs provided.')  # Use followup after deferring
        return

    if not map_ids:
        await ctx.followup.send('Invalid input (map id collection empty).')
        return

    try:
        beatmapsets, error_ids = await fetch_beatmapsets(map_ids)
        beatmapsets = list(sorted(beatmapsets, key=lambda b: b.artist))
        dmca = dmca_sets(beatmapsets)

        view_menu = menu(ctx, beatmapsets, dmca)
        await view_menu.start()
    except ValueError as e:
        logger.warning(f'Invalid input [{e}].')
        await ctx.followup.send(f'Invalid input [{e}].')
        return


@tree.error
async def on_app_command_error(interaction, error):
    if isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(f"Command is on cooldown. Try again in {error.retry_after:.2f} seconds.", ephemeral=True)