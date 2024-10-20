from src import validator

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

