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

def test_edge_artist_one_word_false_flag():
    """If a disallowed artist appears in the same word as another legitimate artist,
    it should not be flagged. i.e. NOMA inside of NOMANOA should not be flagged.
    NOMA vs. NOMANOA should be flagged."""
    beatmapset = __no_dmca_graveyard_beatmap()
    beatmapset.artist = 'nomanoa'

    # Should be allowed because NOMA should not match within NOMANOA
    assert(validator.is_allowed(beatmapset))

def test_word_boundary_tsunomaki_watame():
    """Test that 'NOMA' does not flag 'Tsunomaki Watame' (false positive fix)"""
    beatmapset = __no_dmca_graveyard_beatmap()
    beatmapset.artist = 'Tsunomaki Watame'
    
    # Should be allowed - NOMA should not match within Tsunomaki
    assert(validator.is_allowed(beatmapset))

def test_word_boundary_noma_vs_someone():
    """Test that 'NOMA vs. Someone' correctly flags for 'NOMA'"""
    beatmapset = __no_dmca_graveyard_beatmap()
    beatmapset.artist = 'NOMA vs. Good Artist'
    
    # Should be disallowed because NOMA is a word boundary match
    assert(validator.is_disallowed(beatmapset))

def test_word_boundary_edge_cases():
    """Test various word boundary edge cases"""
    # Test 1: Artist name at the beginning
    beatmapset = __no_dmca_graveyard_beatmap()
    beatmapset.artist = 'NOMA feat. Someone'
    assert(validator.is_disallowed(beatmapset))
    
    # Test 2: Artist name at the end
    beatmapset = __no_dmca_graveyard_beatmap()
    beatmapset.artist = 'Someone feat. NOMA'
    assert(validator.is_disallowed(beatmapset))
    
    # Test 3: Artist name in parentheses
    beatmapset = __no_dmca_graveyard_beatmap()
    beatmapset.artist = 'Track (NOMA Remix)'
    assert(validator.is_disallowed(beatmapset))
    
    # Test 4: Artist name with punctuation
    beatmapset = __no_dmca_graveyard_beatmap()
    beatmapset.artist = 'NOMA, Someone Else'
    assert(validator.is_disallowed(beatmapset))
    
    # Test 5: Partial match should not flag when part of another word
    beatmapset = __no_dmca_graveyard_beatmap()
    beatmapset.artist = 'Binomaly'  # Contains "noma" but shouldn't flag
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
    
def test_override_disallowed():
    beatmapset = __no_dmca_graveyard_beatmap()
    beatmapset.artist = "Lusumi"
    beatmapset.title = "/execution_program.wav"
    assert(validator.is_disallowed(beatmapset))

def test_overrides():
    beatmapset = __no_dmca_graveyard_beatmap()
    beatmapset.artist = "Morimori Atsushi"
    beatmapset.title = "Tits or get the fuck out!!"

    assert(validator.is_override(beatmapset, "allowed"))
    
    beatmapset = __no_dmca_graveyard_beatmap()
    beatmapset.artist = "Lusumi"
    beatmapset.title = "/execution_program.wav"
    
    assert(validator.is_override(beatmapset, "disallowed"))
    
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

def test_banned_source():
    beatmapset_1 = __no_dmca_graveyard_beatmap()
    beatmapset_2 = __no_dmca_graveyard_beatmap()
    beatmapset_3 = __no_dmca_graveyard_beatmap()
    beatmapset_4 = __no_dmca_graveyard_beatmap()
    beatmapset_5 = __no_dmca_graveyard_beatmap()
    beatmapset_6 = __no_dmca_graveyard_beatmap()

    beatmapset_1.source = "DJMAX"
    beatmapset_2.source = "DJ MAX"
    beatmapset_3.source = "djmax"
    beatmapset_4.source = "neowiz"
    beatmapset_5.source = "chillierpear"
    beatmapset_6.source = "DJMAX Portable 3"

    assert(validator.is_disallowed(beatmapset_1))
    assert(validator.is_disallowed(beatmapset_2))
    assert(validator.is_disallowed(beatmapset_3))
    assert(validator.is_disallowed(beatmapset_4))
    assert(validator.is_allowed(beatmapset_5))
    assert(validator.is_disallowed(beatmapset_6))

def test_warning_banned_source_description():
    beatmapset = __no_dmca_graveyard_beatmap()

    beatmapset.source = "chillierpear"
    beatmapset.description = create_description("this song is from djmax go support the game !!!")

    assert(validator.is_partial(beatmapset))

def test_beatmapset_allowed_none_desc():
    beatmapset = __no_dmca_graveyard_beatmap()

    beatmapset.source = "chillierpear"
    beatmapset.description = create_description(None)

    assert(validator.is_allowed(beatmapset))

def create_description(description: str | None):
    if description:
        return {
            "description": description
        }

    return None

def test_artist_in_title_flagged_remix():
    title = "Flower Petal (Igorrr Remix)"
    assert(validator.artist_in_title_flagged(title))

def test_artist_in_title_flagged_feat():
    title = "Really Long Name (feat. Igorrr)"
    assert(validator.artist_in_title_flagged(title))

def test_artist_in_title_flagged_vs():
    title = "Song Name (Igorrr vs. Camellia)"
    assert(validator.artist_in_title_flagged(title))

def test_artist_in_title_flagged_case_insensitive():
    title = "Some Song (IgOrRr Remix)"
    assert(validator.artist_in_title_flagged(title))

def test_artist_in_title_not_flagged():
    title = "Normal Song Title"
    assert(validator.artist_in_title_flagged(title) == False)

def test_artist_in_title_partial_word_not_flagged():
    title = "NOMANOA Remix"
    assert(validator.artist_in_title_flagged(title) == False)

def test_artist_in_title_space_in_name():
    title = "Something (Hatsuki Yura Remix)"
    assert(validator.artist_in_title_flagged(title))

def test_disallowed_artist_in_title():
    beatmapset = __no_dmca_graveyard_beatmap()
    beatmapset.title = "Song Name (Igorrr Remix)"
    assert(validator.is_disallowed(beatmapset))

def test_partial_artist_in_title():
    beatmapset = __no_dmca_graveyard_beatmap()
    beatmapset.title = "Song Name (Akira Complex Remix)"
    assert(validator.is_partial(beatmapset))

def test_allowed_artist_in_title_when_licensed():
    beatmapset = __no_dmca_graveyard_beatmap()
    beatmapset.title = "Song Name (Akira Complex Remix)"
    beatmapset.track_id = 1234
    assert(validator.is_allowed(beatmapset))

def test_disallowed_artist_in_title_with_feat():
    beatmapset = __no_dmca_graveyard_beatmap()
    beatmapset.title = "Amazing Track (feat. Igorrr)"
    assert(validator.is_disallowed(beatmapset))