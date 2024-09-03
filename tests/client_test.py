from src import client

def test_sanitize_full_beatmapset():
    url = "https://osu.ppy.sh/beatmapsets/90784#osu/246099"
    ids = client.sanitize(url)

    assert ids == {90784}

def test_sanitize_partial_beatmapset():
    url = "https://osu.ppy.sh/beatmapsets/90784#osu"
    ids = client.sanitize(url)

    assert ids == {90784}

def test_sanitize_partial_beatmapset_taiko():
    url = "https://osu.ppy.sh/beatmapsets/90784#taiko"
    ids = client.sanitize(url)

    assert ids == {90784}

def test_sanitize_partial_beatmapset_fruits():
    url = "https://osu.ppy.sh/beatmapsets/90784#fruits"
    ids = client.sanitize(url)

    assert ids == {90784}

def test_sanitize_partial_beatmapset_mania():
    url = "https://osu.ppy.sh/beatmapsets/90784#taiko"
    ids = client.sanitize(url)

    assert ids == {90784}

def test_sanitize_partial_beatmapset_no_hash():
    url = "https://osu.ppy.sh/beatmapsets/90784"
    ids = client.sanitize(url)

    assert ids == {90784}

def test_sanitize_b():
    url = "https://osu.ppy.sh/b/90784"
    ids = client.sanitize(url)

    assert ids == {90784}

def test_sanitize_solo_id():
    url = "90784"
    ids = client.sanitize(url)

    assert ids == {90784}