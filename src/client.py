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


def format_line_item(response: api.ValidationResponse) -> str:
    base_url = f"https://osu.ppy.sh/beatmapsets/{response.beatmapsetId}"
    
    if response.complianceStatus == ComplianceStatus.DISALLOWED:
        if response.complianceFailureReason == ComplianceFailureReason.DMCA:
            icon = "⛔"
        else:
            icon = "❌"
    elif response.complianceStatus == ComplianceStatus.POTENTIALLY_DISALLOWED:
        icon = ":warning:"
    else:  # OK status
        if response.status in ["ranked", "approved"]:
            icon = "✅"
        elif response.status == "loved":
            icon = "💞"
        else:
            icon = ":ballot_box_with_check:"
    
    s = f"{icon} [{response.artist} - {response.title}]({base_url})"
    
    # Add failure reason for disallowed items
    if response.complianceStatus == ComplianceStatus.DISALLOWED:
        if response.complianceFailureReasonString and response.complianceFailureReason == ComplianceFailureReason.DISALLOWED_ARTIST:
            s += f" - {response.complianceFailureReasonString}"
    
    if response.notes:
        s += f" - {response.notes}"
    
    return s

def create_embeds(responses: list[api.ValidationResponse], title: str, color: discord.Color) -> list[Embed]:
    embeds = []
    line_items = [format_line_item(r) for r in responses]
    
    for i in range(0, len(line_items), PAGE_SIZE):
        embed = discord.Embed(title=title, color=color)
        embed.description = '\n'.join(line_items[i:i + PAGE_SIZE])
        embeds.append(embed)
    
    return embeds if embeds else [discord.Embed(title=title, description="No beatmaps found", color=color)]

def categorize_responses(responses: list[api.ValidationResponse]) -> tuple[list, list, list]:
    ok = []
    potential = []
    disallowed = []
    
    for r in responses:
        if r.complianceStatus == ComplianceStatus.OK:
            ok.append(r)
        elif r.complianceStatus == ComplianceStatus.POTENTIALLY_DISALLOWED:
            potential.append(r)
        elif r.complianceStatus == ComplianceStatus.DISALLOWED:
            disallowed.append(r)
    
    # Sort disallowed by severity (DMCA first, then by reason)
    disallowed.sort(key=lambda x: (x.complianceFailureReason if x.complianceFailureReason is not None else 999))
    
    # Sort OK by status (ranked/approved first, then loved, then graveyard)
    def status_priority(r):
        if r.status in ["ranked", "approved"]:
            return 0
        elif r.status == "loved":
            return 1
        else:
            return 2
    
    ok.sort(key=lambda x: (status_priority(x), x.artist.lower() if x.artist else ''))
    potential.sort(key=lambda x: x.artist.lower() if x.artist else '')
    
    return ok, potential, disallowed

def success_error_text(error: bool, potential: bool):
    if error:
        return FAILURE_TEXT

    if potential:
        return WARN_TEXT

    return SUCCESS_TEXT

def menu(interaction: discord.Interaction, responses: list[api.ValidationResponse]) -> ViewMenu:
    logger.info(f"Creating menu for {len(responses)} responses")
    ok, potential, disallowed = categorize_responses(responses)
    
    # Build combined list in specified order
    combined = []
    
    # 1. DMCA first
    dmca = [r for r in disallowed if r.complianceFailureReason == ComplianceFailureReason.DMCA]
    combined.extend(dmca)
    
    # 2. Other disallowed (already sorted by severity)
    other_disallowed = [r for r in disallowed if r.complianceFailureReason != ComplianceFailureReason.DMCA]
    combined.extend(other_disallowed)
    
    # 3. Potential
    combined.extend(potential)
    
    # 4. OK beatmaps (already sorted by status priority)
    combined.extend(ok)
    
    logger.info(f"Combined list has {len(combined)} items")
    
    # Count statistics for footer
    dmca_count = len(dmca)
    disallowed_count = len(other_disallowed)
    partial_count = len(potential)
    
    # Count OK subcategories
    graveyard_count = len([r for r in ok if r.status not in ["ranked", "loved", "approved"]])
    ranked_count = len([r for r in ok if r.status in ["ranked", "loved", "approved"]])
    
    # Determine overall status and color
    if dmca_count > 0 or disallowed_count > 0:
        status_text = FAILURE_TEXT
        color = discord.Color.red()
    elif partial_count > 0:
        status_text = WARN_TEXT
        color = discord.Color.yellow()
    else:
        status_text = SUCCESS_TEXT
        color = discord.Color.green()
    
    # Create embeds with all beatmaps together
    title = "Mappool Compliance Check Results"
    embeds = create_embeds(combined, title, color)
    
    logger.info(f"Created {len(embeds)} embed(s)")
    
    # Add footer with statistics to all pages
    for embed in embeds:
        embed.set_footer(text=f'\n{status_text}\n️⛔: {dmca_count} | ❌: {disallowed_count} | ⚠️: {partial_count} | ☑️: {graveyard_count} | ✅ / 💞: {ranked_count}')
    
    # Create menu
    view_menu = ViewMenu(interaction, menu_type=ViewMenu.TypeEmbed)
    view_menu.add_pages(embeds)
    
    logger.info(f"ViewMenu created with {len(embeds)} pages")
    
    # Always add navigation buttons, but disable them if only one page
    back_button = ViewButton.back()
    next_button = ViewButton.next()
    
    if len(embeds) <= 1:
        back_button.disabled = True
        next_button.disabled = True
    
    view_menu.add_button(back_button)
    view_menu.add_button(next_button)
    
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
    if not token:
        logger.error('TOKEN environment variable not set')
        return
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

        # Use results directly - sorting will be done in menu()
        responses = api_response.results

        # Handle any failures
        if api_response.failures:
            logger.warning(f'Failed to validate beatmap IDs: {api_response.failures}')
        
        # Check if we have any responses
        if not responses:
            await ctx.followup.send('No beatmap data received from the API.')
            return

        logger.info(f"Processing {len(responses)} beatmap responses")
        view_menu = menu(ctx, responses)
        logger.info("Starting ViewMenu")
        await view_menu.start()
        logger.info("ViewMenu started successfully")
    except ValueError as e:
        logger.warning(f'Invalid input [{e}].')
        await ctx.followup.send(f'Invalid input [{e}].')
        return
    except Exception as e:
        logger.error(f'Error creating menu: {e}', exc_info=True)
        await ctx.followup.send('An error occurred while creating the response menu.')
        return


@tree.error
async def on_app_command_error(interaction, error):
    if isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(f"Command is on cooldown. Try again in {error.retry_after:.2f} seconds.", ephemeral=True)
