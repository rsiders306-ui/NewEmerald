# BeaconDex trainer distribution

All 63 BeaconDex species appear once across 63 unique regular trainer records.
Every edited team retains its original members, remains between two and six
Pokémon, and receives a custom species appropriate to its level band and, where
possible, its trainer class or existing type theme.

The pass adds custom members to all eight first Gym Leader battles, all four
first-run Elite Four battles, three Galactic commander battles, two Cyrus
battles, and selected route trainers. Cynthia's teams already use all six slots,
so they retain their complete original rosters. Barry is handled by the dynamic
two-starter system instead of a static JSON assignment.

`data/beacondex/trainer_distribution.json` records the exact assignment,
original and resulting party sizes, level, family, stage, and story-boss flag.
`tools/beacondex/trainer_distribution_audit.py` verifies that the 63 species and
63 trainers still match this manifest. The broader party audit continues to
enforce the two-Pokémon minimum required by global Double Battles.

The structural pass compiles and is fully covered by automated checks. Runtime
difficulty, moveset synergy, held items, and pacing still need emulator
playtesting and a full-game balance pass.
