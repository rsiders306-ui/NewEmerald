# BeaconDex wild distribution

Every BeaconDex species has one permanent encounter slot. The placement pass uses
50 maps across the main story and postgame, preserves all 147 species present in
the pre-BeaconDex wild baseline, and leaves encounter levels unchanged so the
regional level curve remains intact. The protected inventory is recorded in
`data/beacondex/original_wild_species.json`. Turtwig, Chimchar, and Piplup have rare recovery
encounters so every species omitted from the player's initial pair remains
obtainable in the same save.

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

## Unchosen Sinnoh starters

| Species | Location | Encounter |
| --- | --- | --- |
| Turtwig | Great Marsh Area 2 | 1% land slot, level 31 |
| Chimchar | Fuego Ironworks exterior | 1% land slot, level 31 |
| Piplup | Lake Acuity | 1% Surf slot, levels 20–40 |

Driblit uses Great Marsh Area 1 land slot 10. Great Marsh Safari encounters
always replace land slots 6 and 7 with the daily species, so those slots cannot
host a permanent placement. The audit models that runtime replacement and checks
all 15 possible initial starter pairs.

The exact map, table, slot, level, replaced original species, and habitat note are
recorded in `data/beacondex/wild_distribution.json`. Run
`python3 tools/beacondex/wild_distribution_audit.py` after encounter changes.
