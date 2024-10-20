from pathlib import Path
from dataclasses import dataclass

import json

from ossapi import Beatmapset
from ossapi.enums import RankStatus

PARTIAL_STATUS = 'partial'
DISALLOWED_STATUS = 'disallowed'

@dataclass
class FlaggedArtistData:
    status: str # Either 'partial' or 'disallowed'
    notes: str | None

path = Path('./flagged.json')

flagged_artists = {} # dict -> artist: FlaggedArtistData

# We only want to parse this once to save resources
if len(flagged_artists) == 0:
    with open(path, 'r') as file:
        flagged_artists = dict(json.load(file))

        for k in flagged_artists:
            flagged_artists[k] = FlaggedArtistData(**flagged_artists[k])

def is_dmca(beatmapset: Beatmapset) -> bool:
    return beatmapset.availability.download_disabled or \
        beatmapset.availability.more_information is not None

def is_licensed(track_id: int | None) -> bool:
    return track_id is not None

def is_status_approved(status: RankStatus) -> bool:
    return status == RankStatus.RANKED or \
        status == RankStatus.APPROVED or \
        status == RankStatus.LOVED

def flag_key_match(artist: str) -> str | None:
    """
    If a partial key matches (e.g. the beatmapset artist is
    'Igorrr vs. Camellia' and the flagged artist is 'Igorrr'),
    return the flagged artist. Otherwise, return None.
    """
    keys = flagged_artists.keys()
    for key in keys:
        if key.lower() in artist.lower():
            return key

    return None

def artist_flagged(artist: str) -> bool:
    if artist in flagged_artists:
        return True

    return flag_key_match(artist) is not None

def is_partial(beatmapset: Beatmapset) -> bool:
    if is_allowed(beatmapset):
        return False

    artist = beatmapset.artist

    if not artist_flagged(artist):
        return False

    key = flag_key_match(artist)
    if key is not None:
        return flagged_artists[key].status == PARTIAL_STATUS

    return False

def is_allowed(beatmapset: Beatmapset):
    """
    Determines whether a beatmapset is allowed according to the current
    content usage permissions rules.

    Rules:
    0. The beatmap cannot have any DMCA notices at all.
    1. If the beatmap is ranked, approved, or loved, it is allowed.
    2. If the track is licensed, it is allowed.
    3. If the beatmap is neither of those and the artist is not in our
    disallowed / partial list, it is allowed. To be on the safe side,
    i.e. in the case of gray-area collabs,
    """
    if is_dmca(beatmapset):
        return False

    if is_licensed(beatmapset.track_id) or is_status_approved(beatmapset.status):
        return True

    return not artist_flagged(beatmapset.artist)

def is_disallowed(beatmapset: Beatmapset) -> bool:
    if is_allowed(beatmapset):
        return False

    if not artist_flagged(beatmapset.artist):
        return False

    key = flag_key_match(beatmapset.artist)
    if key is not None:
        return flagged_artists[key].status == DISALLOWED_STATUS

    return False