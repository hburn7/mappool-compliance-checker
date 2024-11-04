from ossapi import Beatmapset, Availability
from ossapi.enums import RankStatus

from src import validator

def __no_dmca_ranked_beatmap():
    beatmapset = Beatmapset()
    beatmapset.artist = 'Some cool allowed artist'
    beatmapset.availability = Availability()
    beatmapset.availability.download_disabled = False
    beatmapset.availability.more_information = None
    beatmapset.track_id = None
    beatmapset.status = RankStatus.RANKED

    return beatmapset

def __no_dmca_graveyard_beatmap():
    beatmapset = __no_dmca_ranked_beatmap()
    beatmapset.status = RankStatus.GRAVEYARD

    return beatmapset

def test_artist_flagged():
    artist = 'Igorrr'
    assert(validator.artist_flagged(artist))

def test_artist_flagged_case_insensitive():
    artist = 'IgOrRr'
    assert(validator.artist_flagged(artist))

def test_artist_flagged_collab():
    artist = 'igorrr vs. Camellia'
    assert(validator.artist_flagged(artist))

def test_is_licensed():
    track_id = 1234
    assert(validator.is_licensed(track_id))

def test_is_not_licensed():
    track_id = None
    assert(validator.is_licensed(track_id) == False)

def test_is_status_approved():
    statuses = [validator.RankStatus.RANKED, validator.RankStatus.APPROVED, validator.RankStatus.LOVED]
    for status in statuses:
        assert(validator.is_status_approved(status))

def test_is_dmca_download_disabled():
    beatmapset = Beatmapset()
    beatmapset.availability = Availability()
    beatmapset.availability.download_disabled = True
    assert(validator.is_dmca(beatmapset))

def test_is_dmca_more_info():
    beatmapset = Beatmapset()
    beatmapset.availability = Availability()
    beatmapset.availability.more_information = 'blah'
    assert(validator.is_dmca(beatmapset))

def test_beatmapset_is_allowed_standard():
    beatmapset = __no_dmca_ranked_beatmap()
    assert(validator.is_allowed(beatmapset))

def test_beatmapset_is_allowed_ranked_with_prohibited_artist():
    beatmapset = __no_dmca_ranked_beatmap()
    beatmapset.artist = 'Igorrr'
    assert(validator.is_allowed(beatmapset))

def test_beatmapset_is_allowed_ranked_with_prohibited_artist_collab():
    beatmapset = __no_dmca_ranked_beatmap()
    beatmapset.artist = 'Igorrr vs. Camellia'
    assert(validator.is_allowed(beatmapset))

def test_beatmapset_is_not_allowed_dmca():
    beatmapset = __no_dmca_ranked_beatmap()
    beatmapset.availability.download_disabled = True
    assert(validator.is_allowed(beatmapset) == False)

def test_beatmapset_is_partial_artist():
    beatmapset = __no_dmca_graveyard_beatmap()
    beatmapset.artist = 'Akira Complex'
    assert(validator.is_partial(beatmapset))

def test_beatmapset_is_partial_artist_collab():
    beatmapset = __no_dmca_graveyard_beatmap()
    beatmapset.artist = 'Akira Complex & Hommarju'
    assert(validator.is_partial(beatmapset))

def test_beatmapset_artist_partial_track_licensed():
    beatmapset = __no_dmca_graveyard_beatmap()
    beatmapset.artist = 'Akira Complex'
    beatmapset.track_id = 1234
    assert(validator.is_partial(beatmapset) == False)
    assert(validator.is_allowed(beatmapset))

def test_disallowed_artist():
    beatmapset = __no_dmca_graveyard_beatmap()
    beatmapset.artist = 'Igorrr'
    assert(validator.is_disallowed(beatmapset))

def test_disallowed_artist_collab():
    beatmapset = __no_dmca_graveyard_beatmap()
    beatmapset.artist = 'Igorrr vs. Camellia'
    assert(validator.is_disallowed(beatmapset))

# Edge case: https://osu.ppy.sh/beatmapsets/2148404#mania/4525647
def test_edge_uma_vs_morimori_partial():
    beatmapset = __no_dmca_graveyard_beatmap()
    beatmapset.artist = 'uma vs. Morimori Atsushi'

    # Needs to be disallowed because Morimori Atsushi is a prohibited artist
    assert(validator.is_partial(beatmapset))

def test_edge_artist_one_word_flase_flag():
    """If a disallowed artist appears in the same word as another legitimate artist,
    it should not be flagged. i.e. NOMA inside of NOMANOA should not be flagged.
    NOMA vs. NOMANOA should be flagged."""
    beatmapset = __no_dmca_graveyard_beatmap()
    beatmapset.artist = 'nomanoa'

    # Needs to be disallowed because Morimori Atsushi is a prohibited artist
    assert(validator.is_allowed(beatmapset))

def test_disallowed_space_in_name():
    beatmapset = __no_dmca_graveyard_beatmap()
    beatmapset.artist = 'Hatsuki Yura'

    assert(validator.is_disallowed(beatmapset))

def test_override_allowed():
    """Designed to catch some edge cases with wrong
    metadata for tracks which may have been renamed or something.
    This is a good example: https://osu.ppy.sh/beatmapsets/352169#osu/776107
    The officially licensed track name is 'Txxs or get the fxxk out!!' whereas
    this beatmap uses 'Tits or get the fuck out!!'"""
    beatmapset = __no_dmca_graveyard_beatmap()
    beatmapset.artist = "Morimori Atsushi"
    beatmapset.title = "Tits or get the fuck out!!"

    assert(validator.is_allowed(beatmapset))

def test_overrides():
    beatmapset = __no_dmca_graveyard_beatmap()
    beatmapset.artist = "Morimori Atsushi"
    beatmapset.title = "Tits or get the fuck out!!"

    assert(validator.is_override(beatmapset, "allowed"))

def test_overrides_negative_artist():
    beatmapset = __no_dmca_graveyard_beatmap()
    beatmapset.artist = "Morimori Sushi"
    beatmapset.title = "Tits or get the fuck out!!"

    assert(not validator.is_override(beatmapset, "allowed"))

def test_overrides_negative_title():
    beatmapset = __no_dmca_graveyard_beatmap()
    beatmapset.artist = "Morimori Atsushi"
    beatmapset.title = "Tits or get the fuck outt!!"

    assert(not validator.is_override(beatmapset, "allowed"))
