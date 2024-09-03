from src import validator

def test_fa_recognition():
    s = "| [![][FA]](https://osu.ppy.sh/beatmaps/artists/180) | [Fred V & Grafix](https://osu.ppy.sh/beatmaps/artists/180) | ![][true] |"
    res = validator.identify_artists(s)[0]

    assert res.fa == True
    assert res.fa_url == "https://osu.ppy.sh/beatmaps/artists/180"
    assert res.artist == "Fred V & Grafix"
    assert res.status == "true"
    assert res.notes == ""

def test_no_fa_artist_recognition():
    s = "| ak+q | ![][false] |"
    res = validator.identify_artists(s)[0]

    assert res.fa == False
    assert res.fa_url == ""
    assert res.artist == "ak+q"
    assert res.status == "false"
    assert res.notes == ""