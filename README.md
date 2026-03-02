# osu! Mappool Compliance Checker (OMCC)

This app ensures your mappool is in compliance with official [tournament support rules](https://osu.ppy.sh/wiki/en/Tournaments/Official_support) regarding which beatmaps may be used in officially-supported osu! tournaments. It is maintained by [Stage](https://osu.ppy.sh/users/8191845), an active [osu! Tournament Committee](https://osu.ppy.sh/wiki/en/People/Tournament_Committee) member.


## Installation

Add this app to your Discord server with [this link](https://discord.com/oauth2/authorize?client_id=1264419097463226429&integration_type=0&scope=applications.commands).

**Note:** this tool is added as an *integration* ("app") into your server. It will not appear anywhere in the member list, though the functionality is identical to that of a bot. You can manage it by going to `Server Settings > Integrations`.

### Commands

Both commands return compliance results and will inform you if any beatmaps are non-compliant. If you think you have received a false positive (where a beatmap is not marked correctly), please report an issue and [Stage](https://osu.ppy.sh/users/8191845) will review it with input from the Tournament Committee if necessary.

#### `/validate`

Validates a collection of beatmaps against osu!'s [content usage permissions](https://osu.ppy.sh/wiki/en/Rules/Content_usage_permissions) rules. Pass in a list of beatmap links or beatmap IDs, separated by a space.

```
/validate <beatmaps> [strict]
```

#### `/validate-csv`

Validates a CSV file of artist/title metadata against osu!'s content usage permissions.

```
/validate-csv <file> [strict]
```

The CSV must include a header row with `artist` and `title` columns (case-insensitive). Optionally include `artist_unicode` and `title_unicode` columns. Rows missing an artist or title are skipped. Both UTF-8 and UTF-8 with BOM encodings are supported.

Example:

```csv
artist,title,artist_unicode,title_unicode
Camellia,GHOST,かめりあ,GHOST
Frums,memoryfactory.lzh,Frums,memoryfactory.lzh
```

#### Strict mode

Both commands accept an optional `strict` parameter (disabled by default). Strict mode adds additional checks against [game soundtrack databases](https://github.com/hburn7/omc-api/tree/master/data/strict) maintained in [omc-api](https://github.com/hburn7/omc-api). This is useful for world cups or other situations where compliance beyond the standard content usage permissions list is required.

## Bug reports

Please report any bugs as an issue on this repository.