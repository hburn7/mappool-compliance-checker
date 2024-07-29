from dataclasses import dataclass

file_path = 'data.txt'


@dataclass
class ArtistData:
    fa: bool
    fa_url: str
    artist: str
    status: str
    notes: str

    def __repr__(self):
        return f"ArtistData(fa={self.fa}, fa_url={self.fa_url}, artist={self.artist}, status={self.status}, notes={self.notes})"


def parse_osu_rules():
    # Read the file content
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
        artists = identify_artists(content)

        for a in artists:
            print(a)

def identify_artists(content: str) -> list[ArtistData]:
    r = []

    for line in content.splitlines():
        data = ArtistData(fa=False, fa_url="", artist="", status="", notes="")

        sections = line.split('|')[1::]

        # If the first section has a url, this is a featured artist.
        if 'https://osu.ppy.sh/beatmaps/artists/' in sections[0]:
            data.fa = True

            # Append the id to the artist url
            data.fa_url = "https://osu.ppy.sh/beatmaps/artists/" + \
                          sections[0].split('https://osu.ppy.sh/beatmaps/artists/')[1]
            data.artist = sections[1].strip().split('[')[1].split(']')[0]
            data.status = "true" if "true" in sections[2] else "partial"

            if data.status == "partial":
                data.notes = sections[3].strip()
        else:
            # Not a featured artist, artist name is in this section
            data.artist = sections[0].strip()
            data.status = "false"

        r.append(data)

    return r
