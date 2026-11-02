# BeaconDex wild distribution

Every BeaconDex species has one permanent encounter slot. The placement pass uses
48 maps across the main story and postgame, keeps all original Pokémon available
somewhere in Sinnoh, and leaves encounter levels unchanged so the regional level
curve remains intact.

The first forms appear on early or biome-appropriate routes. Middle forms appear
in midgame habitats, and most final forms are rare encounters in late-game or
postgame areas. Land slots use the vanilla `20/20/10/10/10/10/5/5/4/4/1/1`
weights. Almost all additions occupy the 5%, 4%, or 1% slots. Tidelion uses the
1% Super Rod slot on Route 230.

| Family | First form | Middle form | Final form |
| --- | --- | --- | --- |
| Glimbark | Route 203 | Route 210 South | Victory Road 2F |
| Calflank | Oreburgh Mine | Iron Island | Stark Mountain |
| Zephylet | Route 202 | Route 210 North | Route 228 |
| Trillkit | Eterna Forest | Trophy Garden | Route 222 |
| Medijest | Route 209 | Solaceon Ruins | Route 224 |
| Rookit | Route 206 | Iron Island | Mt. Coronet 6F |
| Groovette | Route 205 North | Fuego Ironworks | Stark Mountain |
| Emberrest | Route 207 | Wayward Cave | Victory Road 1F |
| Timblet | Valley Windworks | Route 212 North | Route 224 |
| Nilecub | Route 205 South | Great Marsh | Route 230 (Super Rod) |
| Snugrime | Eterna Forest | Route 216 | Snowpoint Temple 1F |
| Fleurrit | Eterna Forest | Lost Tower | Turnback Cave |
| Emberimp | Route 207 | Fuego Ironworks | Stark Mountain |
| Sluship | Route 211 West | Route 216 | Snowpoint Temple |
| Driblit | Great Marsh | Mt. Coronet 2F | Route 226 |
| Shardshade | Oreburgh Gate | Lost Tower | Turnback Cave |
| Spriglet | Route 204 South | Route 212 South | Route 224 |
| Tinham | Valley Windworks | Iron Island | Route 228 |
| Pufflurry | Route 205 North | Route 216 | Snowpoint Temple |
| Niblit | Route 202 | Route 214 | Route 229 |
| Pebpup | Route 207 | Mt. Coronet 3F | Stark Mountain |

The exact map, table, slot, level, replaced original species, and habitat note are
recorded in `data/beacondex/wild_distribution.json`. Run
`python3 tools/beacondex/wild_distribution_audit.py` after encounter changes.
