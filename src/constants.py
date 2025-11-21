from enum import IntEnum

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

PAGE_SIZE = 25
COOLDOWN_RATE = 10
COOLDOWN_PER = 45

SUCCESS_TEXT = "🥳 No disallowed beatmapsets found!"
FAILURE_TEXT = "⛔ Disallowed beatmapsets found!"
WARN_TEXT = "⚠️Ensure all flagged beatmapsets are compliant!"

ICON_DMCA = "⛔"
ICON_DISALLOWED = "❌"
ICON_WARNING = ":warning:"
ICON_RANKED = "✅"
ICON_LOVED = "💞"
ICON_OK = ":ballot_box_with_check:"

OSU_BEATMAPSET_URL = "https://osu.ppy.sh/beatmapsets/{}"

LOG_DIR = 'logs'
LOG_FILE = 'logs/discord.log'
LOG_MAX_BYTES = 32 * 1024 * 1024  # 32 MiB
LOG_BACKUP_COUNT = 5
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
LOG_FORMAT = '[{asctime}] [{levelname:<8}] {name}: {message}'