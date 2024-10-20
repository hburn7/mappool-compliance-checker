from pathlib import Path
from dataclasses import dataclass

import json

from ossapi import Beatmapset
from ossapi.enums import RankStatus


@dataclass
class FlaggedArtistData:
    artist: str
    status: str # Either 'partial' or 'disallowed'
    notes: str | None

path = Path('./flagged.json')

flagged_artists = {} # dict -> artist: FlaggedArtistData

# We only want to parse this once to save resources
if len(flagged_artists) == 0:
    with open(path, 'r') as file:
        flagged_artists = dict(json.load(file))


def is_dmca(beatmapset: Beatmapset) -> bool:
    return beatmapset.availability.download_disabled or \
        beatmapset.availability.more_information is not None

def is_licensed(track_id: int | None) -> bool:
    return track_id is not None

def is_status_approved(status: RankStatus) -> bool:
    return status == RankStatus.RANKED or \
        status == RankStatus.APPROVED or \
        status == RankStatus.LOVED

def artist_flagged(artist: str) -> bool:
    if artist in flagged_artists:
        return True

    lower = artist.lower()
    keys = [f.lower() for f in flagged_artists.keys()]
    for k in keys:
        if k in lower:
            return True

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

