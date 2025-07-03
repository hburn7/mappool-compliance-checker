from pathlib import Path
from dataclasses import dataclass
import re

import json

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
sources_path = Path('./banned_sources.json')

flagged_artists = {} # dict -> artist: FlaggedArtistData
overrides = []
banned_sources = []

# We only want to parse this once to save resources
if len(flagged_artists) == 0:
    with open(flag_path, 'r') as file:
        flagged_artists = dict(json.load(file))

        for k in flagged_artists:
            flagged_artists[k] = FlaggedArtistData(**flagged_artists[k])

    with open(overrides_path, 'r') as file:
        overrides = list(json.load(file))

    with open(sources_path, 'r') as file:
        banned_sources = list(json.load(file))

def is_banned_source(beatmapset: Beatmapset) -> bool:
    if beatmapset.source is None:
        return False

    for source in banned_sources:
        if source.lower() in beatmapset.source.lower():
            return True

    return False

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

def artist_in_title_flagged(title: str) -> bool:
    """
    Checks if any flagged artists appear in the beatmap title.
    This catches cases like "Song Name (Artist Remix)" or "Track (feat. Artist)"
    """
    if not title:
        return False
    
    lower_title = title.lower()
    
    for artist in flagged_artists.keys():
        lower_artist = artist.lower()
        
        # For artists with spaces in their name, do a simple substring match
        if ' ' in artist:
            if lower_artist in lower_title:
                return True
        else:
            # For single-word artists, ensure word boundaries to avoid false positives
            # Check for common patterns like "remix", "feat.", "vs.", etc.
            # Word boundary pattern - artist must be a complete word
            pattern = r'\b' + re.escape(lower_artist) + r'\b'
            if re.search(pattern, lower_title):
                return True
    
    return False

def get_flagged_artist_in_title(title: str) -> tuple[str | None, str | None]:
    """
    Returns the flagged artist found in the title and their status.
    Returns (artist_name, status) or (None, None) if no flagged artist found.
    """
    if not title:
        return (None, None)
    
    lower_title = title.lower()
    
    for artist in flagged_artists.keys():
        lower_artist = artist.lower()
        found = False
        
        # For artists with spaces in their name, do a simple substring match
        if ' ' in artist:
            if lower_artist in lower_title:
                found = True
        else:
            # For single-word artists, ensure word boundaries to avoid false positives
            pattern = r'\b' + re.escape(lower_artist) + r'\b'
            if re.search(pattern, lower_title):
                found = True
        
        if found:
            return (artist, flagged_artists[artist].status)
    
    return (None, None)

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

def description_contains_banned_source(beatmapset: Beatmapset) -> bool:
    desc = beatmapset.description["description"] if beatmapset.description else None
    l_desc = desc.lower() if desc else None
    if not l_desc:
        return False

    for source in banned_sources:
        if source.lower() in l_desc:
            return True

    return False


def is_partial(beatmapset: Beatmapset) -> bool:
    if is_override(beatmapset, "partial"):
        return True

    if description_contains_banned_source(beatmapset):
        return True

    if is_allowed(beatmapset):
        return False

    # Check if artist is flagged in the artist field
    artist = beatmapset.artist
    artist_field_partial = False
    
    if artist_flagged(artist):
        key = flag_key_match(artist)
        if key is not None:
            artist_field_partial = flagged_artists[key].status == PARTIAL_STATUS

    # Check if artist is flagged in the title field
    title_artist, title_status = get_flagged_artist_in_title(beatmapset.title)
    title_field_partial = title_artist is not None and title_status == PARTIAL_STATUS

    return artist_field_partial or title_field_partial

def is_allowed(beatmapset: Beatmapset):
    """
    Determines whether a beatmapset is allowed according to the current
    content usage permissions rules.

    Rules:
    0. The beatmap cannot have any DMCA notices at all.
    1. If the beatmap is ranked, approved, or loved, it is allowed.
    2. If the track is licensed, it is allowed.
    3. The beatmapset description does not contain a banned source (safety check).
    4. If the beatmap is neither of those and the artist is not in our
    disallowed / partial list, it is allowed. To be on the safe side,
    i.e. in the case of gray-area collabs,
    """
    if is_dmca(beatmapset):
        return False

    if is_licensed(beatmapset.track_id) or is_status_approved(beatmapset.status):
        return True

    if is_override(beatmapset, "allowed"):
        return True

    if is_banned_source(beatmapset):
        return False

    if description_contains_banned_source(beatmapset):
        return False

    # Check both artist field and title field for flagged artists
    if artist_flagged(beatmapset.artist):
        return False
    
    if artist_in_title_flagged(beatmapset.title):
        return False
    
    return True

def is_disallowed(beatmapset: Beatmapset) -> bool:
    if is_override(beatmapset, "disallowed"):
        return True

    if is_banned_source(beatmapset):
        return True

    if is_allowed(beatmapset):
        return False

    # Check if artist is flagged in the artist field
    artist_field_disallowed = False
    if artist_flagged(beatmapset.artist):
        key = flag_key_match(beatmapset.artist)
        if key is not None:
            artist_field_disallowed = flagged_artists[key].status == DISALLOWED_STATUS

    # Check if artist is flagged in the title field
    title_artist, title_status = get_flagged_artist_in_title(beatmapset.title)
    title_field_disallowed = title_artist is not None and title_status == DISALLOWED_STATUS

    return artist_field_disallowed or title_field_disallowed