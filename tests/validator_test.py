from ossapi import Beatmapset, Availability
from ossapi.enums import RankStatus

from src import validator

def __no_dmca_ranked_beatmap():
    beatmapset = Beatmapset()
    beatmapset.artist = 'Some cool allowed artist'
    beatmapset.availability = Availability()
    beatmapset.availability.download_disabled = False
    beatmapset.availability.more_information = None
    beatmapset.status = RankStatus.RANKED

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
    beatmapset = __no_dmca_ranked_beatmap()
    beatmapset.status = RankStatus.GRAVEYARD
    beatmapset.artist = 'Akira Complex'
    assert(validator.is_partial(beatmapset))

def test_beatmapset_is_partial_artist_collab():
    beatmapset = __no_dmca_ranked_beatmap()
    beatmapset.status = RankStatus.GRAVEYARD
    beatmapset.artist = 'Akira Complex & Hommarju'
    assert(validator.is_partial(beatmapset))

def test_beatmapset_artist_partial_track_licensed():
    beatmapset = __no_dmca_ranked_beatmap()
    beatmapset.artist = 'Akira Complex'
    beatmapset.track_id = 1234
    beatmapset.status = RankStatus.GRAVEYARD
    assert(validator.is_partial(beatmapset) == False)
    assert(validator.is_allowed(beatmapset))

def test_disallowed_artist():
    beatmapset = __no_dmca_ranked_beatmap()
    beatmapset.status = RankStatus.GRAVEYARD
    beatmapset.artist = 'Igorrr'
    assert(validator.is_disallowed(beatmapset))

def test_disallowed_artist_collab():
    beatmapset = __no_dmca_ranked_beatmap()
    beatmapset.status = RankStatus.GRAVEYARD
    beatmapset.artist = 'Igorrr vs. Camellia'
    assert(validator.is_disallowed(beatmapset))

# Edge case: https://osu.ppy.sh/beatmapsets/2148404#mania/4525647
def test_edge_uma_vs_morimori_partial():
    beatmapset = Beatmapset()
    beatmapset.availability = Availability()
    beatmapset.availability.download_disabled = False
    beatmapset.availability.more_information = None
    beatmapset.track_id = None

    beatmapset.artist = 'uma vs. Morimori Atsushi'
    beatmapset.status = RankStatus.GRAVEYARD

    # Needs to be disallowed because Morimori Atsushi is a prohibited artist
    assert(validator.is_partial(beatmapset))