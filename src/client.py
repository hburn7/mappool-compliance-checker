import logging
import logging.handlers
import os
from enum import IntEnum

import discord
from discord import app_commands, Embed
from dotenv import load_dotenv
from reactionmenu import ViewMenu, ViewButton

import api

# Enum definitions matching the TypeScript API
class ComplianceStatus(IntEnum):
    OK = 0
    POTENTIALLY_DISALLOWED = 1
    DISALLOWED = 2

class ComplianceFailureReason(IntEnum):
    DMCA = 0
    DISALLOWED_ARTIST = 1
    DISALLOWED_SOURCE = 2
    DISALLOWED_BY_RIGHTSHOLDER = 3
    FA_TRACKS_ONLY = 4

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.reactions = True
intents.members = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

load_dotenv()
bot_token = os.getenv('TOKEN')

logger = logging.getLogger('client')

PAGE_SIZE = 25

SUCCESS_TEXT = "🥳 No disallowed beatmapsets found!"
FAILURE_TEXT = "⛔ Disallowed beatmapsets found!"
WARN_TEXT = "⚠️Ensure all flagged beatmapsets are compliant!"

@client.event
async def on_ready():
    logger.info(f'Logged in as {client.user}')
    await tree.sync()

    logger.info('Commands synced, bot is ready!')


def line_item_dmca(response: api.ValidationResponse) -> str:
    s = f"⛔ [{response.artist} - {response.title}](https://osu.ppy.sh/beatmapsets/{response.beatmapsetId})"

    if response.notes:
        s += f" - {response.notes}"

    return s

def line_item_disallowed(response: api.ValidationResponse) -> str:
    base = f"❌ [{response.artist} - {response.title}](https://osu.ppy.sh/beatmapsets/{response.beatmapsetId})"

    # Add reason if available
    if response.complianceFailureReasonString:
        if response.complianceFailureReason == ComplianceFailureReason.DISALLOWED_ARTIST:
            base += f" - {response.complianceFailureReasonString}"

    if response.notes:
        base += f" - {response.notes}"

    return base

def line_item_partial(response: api.ValidationResponse) -> str:
    s = f":warning: [{response.artist} - {response.title}](https://osu.ppy.sh/beatmapsets/{response.beatmapsetId})"

    if response.notes:
        s += f" - {response.notes}"

    return s

def line_item_allowed_unranked(response: api.ValidationResponse) -> str:
    s = f":ballot_box_with_check: [{response.artist} - {response.title}](https://osu.ppy.sh/beatmapsets/{response.beatmapsetId})"

    if response.notes:
        s += f" - {response.notes}"

    return s

def line_item_allowed_ranked(response: api.ValidationResponse) -> str:
    s = f"✅ [{response.artist} - {response.title}](https://osu.ppy.sh/beatmapsets/{response.beatmapsetId})"

    if response.notes:
        s += f" - {response.notes}"

    return s

def line_item_allowed_loved(response: api.ValidationResponse) -> str:
    s = f"💞 [{response.artist} - {response.title}](https://osu.ppy.sh/beatmapsets/{response.beatmapsetId})"

    if response.notes:
        s += f" - {response.notes}"

    return s

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

def dmca_sets_embeds(dmca: list[api.ValidationResponse]) -> list[Embed]:
    line_items = [line_item_dmca(b) for b in dmca]
    return embeds_from_line_items("DMCA'd beatmapsets found", line_items, discord.Color.red())

def disallowed_sets_embeds(disallowed: list[api.ValidationResponse]) -> list[Embed]:
    line_items = [line_item_disallowed(b) for b in disallowed]
    return embeds_from_line_items("Disallowed beatmapsets found", line_items, discord.Color.red())

def partial_sets_embeds(potential: list[api.ValidationResponse]) -> list[Embed]:
    line_items = [line_item_partial(b) for b in potential]
    return embeds_from_line_items("Partially disallowed beatmapsets found", line_items, discord.Color.yellow())

def allowed_graveyard_sets_embeds(graveyard: list[api.ValidationResponse]) -> list[Embed]:
    line_items = [line_item_allowed_unranked(b) for b in graveyard]
    return embeds_from_line_items("Pending/Graveyard beatmapsets found", line_items, discord.Color.blurple())

def ranked_sets_embeds(ranked: list[api.ValidationResponse]) -> list[Embed]:
    line_items = [line_item_allowed_loved(b) if b.status == "loved" else line_item_allowed_ranked(b) for b in ranked]
    return embeds_from_line_items("Ranked/Loved beatmapsets found", line_items, discord.Color.green())

def count_graveyard(responses: list[api.ValidationResponse]) -> int:
    return len([r for r in responses if r.status not in ["ranked", "loved", "approved"]])

def count_ranked(responses: list[api.ValidationResponse]) -> int:
    return len([r for r in responses if r.status in ["ranked", "loved", "approved"]])

def count_allowed(responses: list[api.ValidationResponse]) -> int:
    return len([r for r in responses if r.complianceStatus == ComplianceStatus.OK])

def count_disallowed(responses: list[api.ValidationResponse]) -> int:
    return len([r for r in responses if r.complianceStatus == ComplianceStatus.DISALLOWED])

def count_partial(responses: list[api.ValidationResponse]) -> int:
    return len([r for r in responses if r.complianceStatus == ComplianceStatus.POTENTIALLY_DISALLOWED])

def count_dmca(responses: list[api.ValidationResponse]) -> int:
    return len(dmca_responses(responses))

def success_error_text(error: bool, potential: bool):
    if error:
        return FAILURE_TEXT

    if potential:
        return WARN_TEXT

    return SUCCESS_TEXT

def menu(interaction: discord.Interaction, responses: list[api.ValidationResponse]) -> ViewMenu:
    allowed = sorted([r for r in responses if r.complianceStatus == ComplianceStatus.OK], key=lambda r: r.artist)
    potential = [r for r in responses if r.complianceStatus == ComplianceStatus.POTENTIALLY_DISALLOWED]
    disallowed = [r for r in responses if r.complianceStatus == ComplianceStatus.DISALLOWED and 
                  r.complianceFailureReason != ComplianceFailureReason.DMCA]
    dmca = [r for r in responses if r.complianceStatus == ComplianceStatus.DISALLOWED and 
            r.complianceFailureReason == ComplianceFailureReason.DMCA]

    ranked = [r for r in allowed if r.status in ["ranked", "loved", "approved"]]
    graveyard = [r for r in allowed if r not in ranked]

    dmca_count = len(dmca)
    disallowed_count = len(disallowed)
    partial_count = len(potential)
    graveyard_count = len(graveyard)
    ranked_count = len(ranked)

    view_menu = ViewMenu(interaction, menu_type=ViewMenu.TypeEmbed)
    pages = []

    if dmca_count > 0:
        pages += dmca_sets_embeds(dmca)

    if disallowed_count > 0:
        pages += disallowed_sets_embeds(disallowed)

    if partial_count > 0:
        pages += partial_sets_embeds(potential)

    if graveyard_count > 0:
        pages += allowed_graveyard_sets_embeds(graveyard)

    if ranked_count > 0:
        pages += ranked_sets_embeds(ranked)

    status_text = success_error_text(dmca_count > 0 or disallowed_count > 0, partial_count > 0)

    for page in pages:
        page.set_footer(text=f'\n{status_text}\n️⛔: %d | ❌: %d | ⚠️%d | ☑️: %d | ✅ / 💞: %d' %
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
        # Call the API to validate beatmaps
        api_response = await api.validate(list(map_ids))

        if api_response is None:
            await ctx.followup.send('Failed to validate beatmaps. Please try again later.')
            return

        # Sort responses by artist
        responses = sorted(api_response.results, key=lambda r: r.artist if r.artist else '')

        # Handle any failures
        if api_response.failures:
            logger.warning(f'Failed to validate beatmap IDs: {api_response.failures}')

        view_menu = menu(ctx, responses)
        await view_menu.start()
    except ValueError as e:
        logger.warning(f'Invalid input [{e}].')
        await ctx.followup.send(f'Invalid input [{e}].')
        return


@tree.error
async def on_app_command_error(interaction, error):
    if isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(f"Command is on cooldown. Try again in {error.retry_after:.2f} seconds.", ephemeral=True)
