# osu! Mappool Compliance Checker (OMCC)

This app ensures your mappool is in compliance with official [tournament support rules](https://osu.ppy.sh/wiki/en/Tournaments/Official_support) regarding which beatmaps may be used in officially-supported osu! tournaments. It is maintained by [Stage](https://osu.ppy.sh/users/8191845), an active [osu! Tournament Committee](https://osu.ppy.sh/wiki/en/People/Tournament_Committee) member.


## Installation

Add this app to your Discord server with [this link](https://discord.com/oauth2/authorize?client_id=1264419097463226429&integration_type=0&scope=applications.commands).

**Note:** this tool is added as an *integration* ("app") into your server. It will not appear anywhere in the member list, though the functionality is identical to that of a bot. You can manage it by going to `Server Settings > Integrations`.

### Commands

The `validate` command is used to validate a collection of beatmaps against osu!'s [content usage permissions](https://osu.ppy.sh/wiki/en/Rules/Content_usage_permissions) rules. You can pass in a list of beatmap links or beatmap IDs, separated by a space.

The command returns the result and will inform you if any beatmaps are non-compliant. If you think you have received a false positive (where a beatmap is not marked correctly), please report an issue and [Stage](https://osu.ppy.sh/users/8191845) will review it with input from the Tournament Committee if necessary.

```
/validate <beatmaps>
```

## Bug reports

Please report any bugs as an issue on this repository.