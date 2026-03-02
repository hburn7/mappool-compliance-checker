import csv
import io
import logging
import logging.handlers
import os
from dataclasses import dataclass
from typing import Optional, Sequence, Union

import discord
from discord import Embed, app_commands
from dotenv import load_dotenv
from reactionmenu import ViewButton, ViewMenu

import api
import constants

AnyValidationResponse = Union[api.ValidationResponse, api.RawValidationResponse]

load_dotenv()

logger = logging.getLogger("client")

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.reactions = True
intents.members = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


@dataclass
class CategorizedResponses:
    ok: list[AnyValidationResponse]
    potential: list[AnyValidationResponse]
    disallowed: list[AnyValidationResponse]
    failed_ids: list[int]
    is_raw: bool = False

    @property
    def dmca_count(self) -> int:
        return sum(
            1
            for r in self.disallowed
            if r.complianceFailureReason == constants.ComplianceFailureReason.DMCA
        )

    @property
    def other_disallowed_count(self) -> int:
        return sum(
            1
            for r in self.disallowed
            if r.complianceFailureReason != constants.ComplianceFailureReason.DMCA
        )

    @property
    def potential_count(self) -> int:
        return len(self.potential)

    @property
    def ok_count(self) -> int:
        return len(self.ok)

    @property
    def graveyard_count(self) -> int:
        if self.is_raw:
            return 0
        return sum(
            1
            for r in self.ok
            if getattr(r, "status", "") not in ["ranked", "loved", "approved"]
        )

    @property
    def ranked_count(self) -> int:
        if self.is_raw:
            return 0
        return sum(
            1
            for r in self.ok
            if getattr(r, "status", "") in ["ranked", "loved", "approved"]
        )

    @property
    def failed_count(self) -> int:
        return len(self.failed_ids)

    def get_combined_list(self) -> list[AnyValidationResponse]:
        combined = []

        dmca = [
            r
            for r in self.disallowed
            if r.complianceFailureReason == constants.ComplianceFailureReason.DMCA
        ]
        combined.extend(dmca)

        other_disallowed = [
            r
            for r in self.disallowed
            if r.complianceFailureReason != constants.ComplianceFailureReason.DMCA
        ]
        combined.extend(other_disallowed)

        combined.extend(self.potential)
        combined.extend(self.ok)

        return combined


class ResponseFormatter:
    @staticmethod
    def format_line_item(response: AnyValidationResponse) -> str:
        icon = ResponseFormatter._get_icon(response)
        beatmapset_id = getattr(response, "beatmapsetId", None)

        if beatmapset_id is not None:
            base_url = constants.OSU_BEATMAPSET_URL.format(beatmapset_id)
            line = f"{icon} [{response.artist} - {response.title}]({base_url})"
        else:
            line = f"{icon} {response.artist} - {response.title}"

        if (
            response.complianceStatus == constants.ComplianceStatus.DISALLOWED
            and response.complianceFailureReasonString
            and response.complianceFailureReason
            == constants.ComplianceFailureReason.DISALLOWED_ARTIST
        ):
            line += f" - {response.complianceFailureReasonString}"

        if response.notes:
            line += f" - {response.notes}"

        return line

    @staticmethod
    def _get_icon(response: AnyValidationResponse) -> str:
        if response.complianceStatus == constants.ComplianceStatus.DISALLOWED:
            if (
                response.complianceFailureReason
                == constants.ComplianceFailureReason.DMCA
            ):
                return constants.ICON_DMCA
            return constants.ICON_DISALLOWED
        elif (
            response.complianceStatus
            == constants.ComplianceStatus.POTENTIALLY_DISALLOWED
        ):
            return constants.ICON_WARNING
        else:
            status = getattr(response, "status", None)
            if status in ["ranked", "approved"]:
                return constants.ICON_RANKED
            elif status == "loved":
                return constants.ICON_LOVED
            return constants.ICON_OK

    @staticmethod
    def categorize_responses(
        responses: Sequence[AnyValidationResponse],
        failed_ids: Optional[list[int]] = None,
        is_raw: bool = False,
    ) -> CategorizedResponses:
        ok = []
        potential = []
        disallowed = []

        for r in responses:
            if r.complianceStatus == constants.ComplianceStatus.OK:
                ok.append(r)
            elif (
                r.complianceStatus == constants.ComplianceStatus.POTENTIALLY_DISALLOWED
            ):
                potential.append(r)
            elif r.complianceStatus == constants.ComplianceStatus.DISALLOWED:
                disallowed.append(r)

        disallowed.sort(
            key=lambda x: (
                x.complianceFailureReason
                if x.complianceFailureReason is not None
                else 999
            )
        )

        if is_raw:
            ok.sort(key=lambda x: x.artist.lower() if x.artist else "")
        else:
            ok.sort(
                key=lambda x: (
                    ResponseFormatter._get_status_priority(x),
                    x.artist.lower() if x.artist else "",
                )
            )
        potential.sort(key=lambda x: x.artist.lower() if x.artist else "")

        return CategorizedResponses(
            ok=ok,
            potential=potential,
            disallowed=disallowed,
            failed_ids=failed_ids or [],
            is_raw=is_raw,
        )

    @staticmethod
    def _get_status_priority(response: api.ValidationResponse) -> int:
        if response.status in ["ranked", "approved"]:
            return 0
        elif response.status == "loved":
            return 1
        return 2


class InputSanitizer:
    @staticmethod
    def sanitize_map_ids(user_input: str) -> set[int]:
        if not user_input:
            return set()

        cleaned = (
            user_input.replace(",", " ")
            .replace("\t", " ")
            .replace("\n", " ")
            .replace("#osu", "")
            .replace("#taiko", "")
            .replace("#fruits", "")
            .replace("#mania", "")
        )

        ids = set()
        for part in cleaned.split():
            try:
                if "/" in part:
                    part = part.split("/")[-1]
                map_id = int(part)
                if map_id > 0:
                    ids.add(map_id)
            except (ValueError, TypeError):
                continue

        return ids


class MenuBuilder:
    @staticmethod
    def create_embeds(
        responses: Sequence[AnyValidationResponse],
        failed_ids: list[int],
        title: str,
        color: discord.Color,
    ) -> list[Embed]:
        if not responses and not failed_ids:
            embed = discord.Embed(
                title=title, description="No beatmaps found", color=color
            )
            return [embed]

        embeds = []
        line_items = [ResponseFormatter.format_line_item(r) for r in responses]

        # Add failed beatmap IDs with error emoji and note
        for beatmap_id in failed_ids:
            line_items.append(f"⁉️ Beatmap ID {beatmap_id} - Processing failed")

        for i in range(0, len(line_items), constants.PAGE_SIZE):
            embed = discord.Embed(title=title, color=color)
            embed.description = "\n".join(line_items[i : i + constants.PAGE_SIZE])
            embeds.append(embed)

        return embeds

    @staticmethod
    def get_status_color(
        categorized: CategorizedResponses,
    ) -> tuple[str, discord.Color]:
        if categorized.dmca_count > 0 or categorized.other_disallowed_count > 0:
            return constants.FAILURE_TEXT, discord.Color.red()
        elif categorized.potential_count > 0 or categorized.failed_count > 0:
            return constants.WARN_TEXT, discord.Color.yellow()
        else:
            return constants.SUCCESS_TEXT, discord.Color.green()

    @staticmethod
    def build_footer_text(categorized: CategorizedResponses, status_text: str) -> str:
        if categorized.is_raw:
            footer = (
                f"\n{status_text}\n️"
                f"⛔: {categorized.dmca_count} | "
                f"❌: {categorized.other_disallowed_count} | "
                f"⚠️: {categorized.potential_count} | "
                f"☑️: {categorized.ok_count}"
            )
        else:
            footer = (
                f"\n{status_text}\n️"
                f"⛔: {categorized.dmca_count} | "
                f"❌: {categorized.other_disallowed_count} | "
                f"⚠️: {categorized.potential_count} | "
                f"☑️: {categorized.graveyard_count} | "
                f"✅ / 💞: {categorized.ranked_count}"
            )

        if categorized.failed_count > 0:
            footer += f" | ⁉️: {categorized.failed_count}"

        return footer

    @staticmethod
    def create_menu(
        interaction: discord.Interaction,
        responses: Sequence[AnyValidationResponse],
        failed_ids: Optional[list[int]] = None,
        is_raw: bool = False,
    ) -> Optional[ViewMenu]:
        try:
            logger.debug(
                f"Creating menu for {len(responses)} responses and {len(failed_ids or [])} failures"
            )

            categorized = ResponseFormatter.categorize_responses(
                responses, failed_ids, is_raw=is_raw
            )
            combined = categorized.get_combined_list()

            logger.debug(f"Combined list has {len(combined)} items")

            status_text, color = MenuBuilder.get_status_color(categorized)

            embeds = MenuBuilder.create_embeds(
                combined, categorized.failed_ids, "Validation Result", color
            )

            logger.debug(f"Created {len(embeds)} embed(s)")

            footer_text = MenuBuilder.build_footer_text(categorized, status_text)
            for embed in embeds:
                embed.set_footer(text=footer_text)

            view_menu = ViewMenu(interaction, menu_type=ViewMenu.TypeEmbed)
            view_menu.add_pages(embeds)

            logger.debug(f"ViewMenu created with {len(embeds)} pages")

            back_button = ViewButton.back()
            next_button = ViewButton.next()

            if len(embeds) <= 1:
                back_button.disabled = True
                next_button.disabled = True

            view_menu.add_button(back_button)
            view_menu.add_button(next_button)

            return view_menu

        except Exception as e:
            logger.error(f"Error creating menu: {e}", exc_info=True)
            return None


def setup_logging() -> None:
    if not os.path.exists(constants.LOG_DIR):
        os.mkdir(constants.LOG_DIR)

    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    numeric_level = getattr(logging, log_level, logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    file_handler = logging.handlers.RotatingFileHandler(
        filename=constants.LOG_FILE,
        encoding="utf-8",
        maxBytes=constants.LOG_MAX_BYTES,
        backupCount=constants.LOG_BACKUP_COUNT,
    )

    formatter = logging.Formatter(
        constants.LOG_FORMAT, constants.LOG_DATE_FORMAT, style="{"
    )
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    logger.info(f"Logging configured at {log_level} level")


@client.event
async def on_ready():
    logger.info(f"Logged in as {client.user}")
    await tree.sync()
    logger.info("Commands synced, bot is ready!")


@tree.command(
    description="Validates a list of maps against osu!'s content-usage listing."
)
@app_commands.describe(strict="Enable strict validation mode")
@app_commands.checks.cooldown(constants.COOLDOWN_RATE, constants.COOLDOWN_PER)
async def validate(ctx: discord.Interaction, u_input: str, strict: bool = False):
    """Validates a mappool. Input should be a list of map IDs separated by commas, spaces, tabs, or new lines."""
    await ctx.response.defer()

    map_ids = InputSanitizer.sanitize_map_ids(u_input)

    if not map_ids:
        await ctx.followup.send("Invalid input: No valid map IDs found.")
        return

    try:
        api_response = await api.validate(list(map_ids), strict=strict)

        if api_response is None:
            await ctx.followup.send(
                "Failed to validate beatmaps. Please try again later."
            )
            return

        if not api_response.results and not api_response.failures:
            await ctx.followup.send("No beatmap data received from the API.")
            return

        logger.info(f"Validating {len(map_ids)} beatmaps for {ctx.user}")
        if api_response.failures:
            logger.warning(
                f"Failed to process {len(api_response.failures)} beatmaps: {api_response.failures}"
            )

        view_menu = MenuBuilder.create_menu(
            ctx, api_response.results, api_response.failures
        )
        if view_menu is None:
            await ctx.followup.send(
                "An error occurred while creating the response menu."
            )
            return

        logger.debug("Starting ViewMenu")
        await view_menu.start()
        logger.debug("ViewMenu started successfully")

    except ValueError as e:
        logger.warning(f"Invalid input: {e}")
        await ctx.followup.send(f"Invalid input: {e}")
    except Exception as e:
        logger.error(f"Unexpected error during validation: {e}", exc_info=True)
        await ctx.followup.send("An unexpected error occurred. Please try again later.")


@tree.command(
    description="Validates a CSV of artist/title metadata against osu!'s content-usage listing."
)
@app_commands.describe(
    file="A CSV file with artist and title columns",
    strict="Enable strict validation mode",
)
@app_commands.checks.cooldown(constants.COOLDOWN_RATE, constants.COOLDOWN_PER)
async def validate_csv(
    ctx: discord.Interaction, file: discord.Attachment, strict: bool = False
):
    await ctx.response.defer()

    if not file.filename.lower().endswith(".csv"):
        await ctx.followup.send("Invalid file type. Please upload a `.csv` file.")
        return

    try:
        raw_bytes = await file.read()
        try:
            text = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            text = raw_bytes.decode("utf-8-sig")

        reader = csv.DictReader(io.StringIO(text))
        if reader.fieldnames is None:
            await ctx.followup.send(
                "CSV file appears to be empty or has no header row."
            )
            return

        lower_fields = {f.lower().strip(): f for f in reader.fieldnames}
        if "artist" not in lower_fields or "title" not in lower_fields:
            await ctx.followup.send("CSV must contain `artist` and `title` columns.")
            return

        artist_col = lower_fields["artist"]
        title_col = lower_fields["title"]
        artist_unicode_col = lower_fields.get("artist_unicode")
        title_unicode_col = lower_fields.get("title_unicode")

        inputs = []
        for row in reader:
            artist = (row.get(artist_col) or "").strip()
            title = (row.get(title_col) or "").strip()
            if not artist or not title:
                continue

            artist_unicode = (
                (row.get(artist_unicode_col) or "").strip()
                if artist_unicode_col
                else ""
            )
            title_unicode = (
                (row.get(title_unicode_col) or "").strip() if title_unicode_col else ""
            )

            inputs.append(
                {
                    "artist": artist,
                    "title": title,
                    "artist_unicode": artist_unicode or artist,
                    "title_unicode": title_unicode or title,
                }
            )

        if not inputs:
            await ctx.followup.send("No valid rows found in the CSV file.")
            return

        logger.info(f"Validating {len(inputs)} metadata entries for {ctx.user}")
        results = await api.validate_metadata(inputs, strict=strict)

        if results is None:
            await ctx.followup.send(
                "Failed to validate metadata. Please try again later."
            )
            return

        if not results:
            await ctx.followup.send("No results received from the API.")
            return

        view_menu = MenuBuilder.create_menu(ctx, results, is_raw=True)
        if view_menu is None:
            await ctx.followup.send(
                "An error occurred while creating the response menu."
            )
            return

        await view_menu.start()

    except Exception as e:
        logger.error(f"Unexpected error during CSV validation: {e}", exc_info=True)
        await ctx.followup.send("An unexpected error occurred. Please try again later.")


@tree.error
async def on_app_command_error(
    interaction: discord.Interaction, error: app_commands.AppCommandError
):
    if isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(
            f"Command is on cooldown. Try again in {error.retry_after:.2f} seconds.",
            ephemeral=True,
        )
    else:
        logger.error(f"Unhandled command error: {error}", exc_info=True)
        if not interaction.response.is_done():
            await interaction.response.send_message(
                "An error occurred while processing the command.", ephemeral=True
            )


def run():
    setup_logging()

    token = os.getenv("TOKEN")
    if not token:
        logger.error("TOKEN environment variable not set")
        return

    try:
        client.run(token, log_handler=None)
    except Exception as e:
        logger.error(f"Failed to start bot: {e}", exc_info=True)
        raise
