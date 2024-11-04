from pathlib import Path
from dataclasses import dataclass

import json
from typing import override

from ossapi import Beatmapset
from ossapi.enums import RankStatus

PARTIAL_STATUS = 'partial'
DISALLOWED_STATUS = 'disallowed'

@dataclass
class FlaggedArtistData:
    status: str # Either 'partial' or 'disallowed'
    notes: str | None

flag_path = Path('./flagged.json')
overrides_path = Path('./overrides.json')

flagged_artists = {} # dict -> artist: FlaggedArtistData
overrides = []

# We only want to parse this once to save resources
if len(flagged_artists) == 0:
    with open(flag_path, 'r') as file:
        flagged_artists = dict(json.load(file))

        for k in flagged_artists:
            flagged_artists[k] = FlaggedArtistData(**flagged_artists[k])

    with open(overrides_path, 'r') as file:
        overrides = list(json.load(file))

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

    if ' ' in artist:
        # We have a space in the artist's name, do a partial match
        for key in keys:
            if key.lower() in artist.lower():
                return key
    else:
        # No space in the artist's name, look for an exact match
        # We do this to avoid these kinds of edge cases:
        # (NOMA -> nomanoma) https://osu.ppy.sh/beatmapsets/2062097#osu/4311526
        for key in keys:
            if key.lower() == artist.lower():
                return key

    return None

def artist_flagged(artist: str) -> bool:
    # exact match
    if artist in flagged_artists:
        return True

    # lower case match
    if artist.lower() in [x.lower() for x in flagged_artists.keys()]:
        return True

    return flag_key_match(artist) is not None

def is_override(beatmapset: Beatmapset, target_status: str) -> bool:
    """Returns true if the provided beatmapset is overridden to
    the provided target_status.

    For example, if the overrides list contains 'abcd' by artist 'efgh' as
    an override to 'disallowed', and the beatmapset metadata matches this,
    and the 'target_status' is 'disallowed', this function returns true."""
    for o in overrides:
        if o['artist'] == beatmapset.artist and o['title'] == beatmapset.title and o['status'] == target_status:
            return True

    return False

def is_partial(beatmapset: Beatmapset) -> bool:
    if is_override(beatmapset, "partial"):
        return True

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

    if is_override(beatmapset, "allowed"):
        return True

    return not artist_flagged(beatmapset.artist)

def is_disallowed(beatmapset: Beatmapset) -> bool:
    if is_override(beatmapset, "disallowed"):
        return True

    if is_allowed(beatmapset):
        return False

    if not artist_flagged(beatmapset.artist):
        return False

    key = flag_key_match(beatmapset.artist)
    if key is not None:
        return flagged_artists[key].status == DISALLOWED_STATUS

    return False