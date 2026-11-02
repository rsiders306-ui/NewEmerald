# CODEX MASTER TASK: BEACONDEX PLATINUM

I want you to BUILD a playable Pokémon Platinum (Nintendo DS) ROM hack using my legally obtained Platinum `.nds` ROM and the attached `BeaconDex_63_Complete_Integration_Pack.zip`. Do the implementation work yourself. Do not stop at giving advice, a plan, placeholder files, or instructions for me to edit things manually. Work in testable milestones, commit each working milestone, and continue as far as the environment supports. Report only verified results.

## 1. Inspect and establish a working codebase FIRST

- Inspect the actual input ROM header, region, revision, hashes, and whether it is vanilla Platinum or already a patched hack. Back up the ROM unchanged.
- Inspect the integration ZIP and read `README_START_HERE.md`, `docs/CODEX_IMPORT_INSTRUCTIONS.md`, `metadata/species_master_63.json`, `metadata/unresolved_design_issues.csv`, and the user overrides. Source precedence: approved user decisions > user override manifest > provisional legacy entries. Record all conflicts rather than quietly replacing canon.
- Evaluate `https://github.com/pret/pokeplatinum` and its `INSTALL.md` as a source-based approach. If the ROM is already VGC Platinum, investigate compatibility separately; do NOT assume that an existing modified `.nds` can simply be compiled with vanilla source or merged into another mod.
- Establish and demonstrate a reproducible UNMODIFIED Platinum build first. If necessary, set up available toolchains and scripts. If the exact ROM revision is unsupported, find a supported and legal path without silently converting it. No downloaded commercial ROMs.
- All changes belong in a dedicated project branch/workspace. Preserve game saves where possible. If source-based additional species proves impossible, report concrete technical evidence and continue with the independently feasible features; do not silently replace base-game Pokémon.

## 2. Core game identity: SINNOH, ALL TRAINER BATTLES ARE DOUBLES

- Keep Pokémon Platinum's world map, towns, routes, gyms, Team Galactic plot, rival Barry, Elite Four, Champion Cynthia, exploration, and progression intact as much as possible.
- Convert EVERY NPC TRAINER BATTLE to the Double Battle format: ordinary route trainers, Youngsters, grunts, admins, Gym Leaders, Barry, Gym rematches, Elite Four, Cynthia, optional trainer battles, and story battles. Give every trainer at least TWO Pokémon, usually more as the story progresses. Rebuild trainer parties, moves, held items, AI, EXP, and pacing for balanced two-on-two combat; don't merely flip a flag if battles crash or trainer parties are inadequate.
- Make scripted first battles and partner battles function as doubles. Resolve conflicts with existing tag-battle scripts and battle tutorials. Preserve cutscenes, progression flags, victory conditions, and story triggers. The player must have two starters BEFORE the first required Trainer Battle. Test edge cases when the player's party has fewer than two usable Pokémon, with no softlocks.
- Normal wild encounters can remain SINGLE battles; scripted legendary/wild battles can remain single as needed. I want all **trainer** battles doubled, not necessarily every wild encounter.
- Balance toward fun and strategic doubles, not competitive tournament restriction rules. Keep all six party slots, switch-ins, and ordinary Platinum play.

## 3. Six starter choices; I choose TWO

- Replace the normal initial starter-selection event with an understandable SIX-CHOICE menu presenting: GLIMBARK, CALFLANK, ZEPHYLET, TURTWIG, CHIMCHAR, PIPLUP.
- Player chooses ANY TWO DISTINCT species in succession, receives both at the beginning at the same level, and both are fully functional starters. No forced type pairing, no duplicates. Show names/types or a preview so choices are clear. Let me choose even two custom starters or two Sinnoh starters.
- Custom starter evolution lines: Glimbark -> Wardmane -> Siderion (Fighting -> Fighting/Fairy, Lv16 and Lv36); Calflank -> Gridiruff -> Oxguard (Rock -> Rock -> Rock/Steel, Lv16/Lv36); Zephylet -> Galecrest -> Terraptor (Flying -> Flying -> Flying/Ground, Lv16/Lv36). Respect the integration manifest/user override where more specific.
- Barry should also have TWO starter Pokémon, chosen from different species than the player's pair if practical; preserve a consistent rival team across all battles and make his choice competitive without two hard counters. Adjust story dialogue referring to a single starter.
- The four unchosen starting species should remain obtainable later in the playthrough via sensible rare gifts/encounters, without overwriting the original starters.

## 4. Integrate ALL 63 BeaconDex species as ADDITIONAL Pokémon

- Import ALL 63 entries / 21 three-stage evolution families from the ZIP. Preserve original existing Platinum species, including all three Sinnoh starter lines. Prefer unique new species IDs, valid National/Regional Dex registration, Pokedex display, menus, PC, evolutions, party use, trainer use, shiny status, breeding, moves, forms, and saving/loading. If expanding the species tables past the original Gen IV limit requires code and data-structure changes, implement and test them carefully.
- Import battle typings, stats, abilities, evolutions, Pokédex entries, learnsets, proposed TM/HM compatibility, sprites, and required metadata. Implement Fairy typing and Fairy-type moves where needed; vanilla Platinum lacks Fairy. For moves/abilities introduced after Gen IV, first inspect engine support; either implement them correctly or document a balanced substitution from working moves/abilities. NO custom signature moves, NO custom abilities, and NO Mega Evolutions for this release.
- Treat the ZIP's 252 normal/shiny front/back transparent PNGs as DRAFT assets, not guaranteed ready-to-use DS battle graphics. Convert to actual Platinum sprite formats/palettes and correct coordinates without ruining character silhouettes. Replace clearly broken mirrored/placeholder backs with proper drawings when possible. Preserve and document what's still a placeholder. Check shiny recolors, interface icons, party status, battle backs, evolution animations, naming limits, Pokedex UI, and any engine-required graphics. Don't claim the sprites are polished unless verified in the game.
- Fill in missing required mechanical metadata using balanced, documented defaults where canon is absent (catch rate, exp growth, gender ratio, friendship, egg groups, size, cries, TM/HM flags). Never quietly overwrite a known design disagreement. Specific known conflicts: some older 27 typings, Terraptor 545 vs 550 BST, Emily's final species name Heartistle, and Moses's line Water -> Water -> Water/Fairy which remains provisional. Record which values need my review. Do not use inaccurate labels from generated posters as data authority.

## 5. Spread our Pokémon throughout SINNOH

- Integrate the 63 Pokémon naturally and progressively across routes, caves, snowfields, marshes, lakes, Mt. Coronet, Great Marsh, underground/other appropriate areas, and postgame where appropriate.
- Theme examples: Snugrime/Cryocoon/Auroroth, Pufflurry/Burrowmuff/Tundrindle, and Fleurrit/Shiverskew/Nivispect in cold northern routes; Venofrost near snowy water; Driblit/Wyrmolt/Drakocoon near wetlands; Shardshade/Cairnraith/Gravemourn in ruins/caves; Emberimp/Gleamber/Hearthalo around hot/fire-related areas; the other families in matching habitats. Treat these as placement guidance, not mandatory map coordinates.
- Keep normal Sinnoh Pokémon available and the world believable. Avoid dumping all 63 on the first routes. Make each of our 63 species obtainable in one save by or during postgame, and implement their evolution requirements. Adjust wild encounter distributions without destroying existing key encounters.
- Incorporate custom Pokémon into selected NPC teams, Gym teams when appropriate, Barry's teams, Galactic teams, and Elite Four/Champion teams if fitting, but preserve their identities. Give trainers synergy appropriate to doubles (Protect, speed control, spread moves, redirection, etc.) and reasonable scaling through the story.

## 6. Do real implementation in independently testable milestones

A. Confirm the ROM and baseline source build. Produce a build log and initial playable build.
B. Implement stable global Trainer Double Battles, starter choice of two, and Barry's two starters; boot and test through at least the first battles.
C. Implement engine changes for Fairy typing and for adding new species without losing original Pokémon; verify a SINGLE representative added BeaconDex species in battle, party, Pokedex and save/load.
D. Import the 63 species, 252 draft sprite files, stats, abilities, level-up moves, evolution and Dex metadata. Build and smoke-test sample species from each family, shinies, back views, evolutions, save/load, moves, and PC boxes.
E. Populate regional wild encounters and trainer parties; verify full-story progression through all gyms and Elite Four including scripted doubles and partner battles.
F. Quality-assurance pass: automated coverage report of all trainer battles and all species, emulator playthrough screenshots/logs where available, graphics and palette validation, compile tests, outstanding issues.

## 7. Deliverables and verification

- A reproducible editable source project with scripts, documented dependencies, saved branch/commits, import manifest and clear README.
- A built and emulator-tested modified `.nds` for PRIVATE local testing if possible; for distribution provide an xdelta/BPS patch against the EXACT stated source ROM, not someone else's copyrighted ROM.
- Machine-readable report listing all 63 species, 252 sprite slots, 6 starter choices, 2-player starter script, trainer doubles conversion counts, encounter locations, known design issues and failures.
- A few actual in-emulator screenshots or logs demonstrating: six-choice starter UI, two starters in party, first rival doubles, a custom Pokémon from the player back, a custom shiny, a new Dex entry, and an evolution.
- Be honest: say what works, what is draft-only, what failed, and the precise next task. If some goals are technically blocked, provide working partial builds and do not label a mockup or asset ZIP a finished game.

Please start NOW by identifying the provided ROM and reading the pack, then set up the real Platinum source workspace and execute milestone A. Continue automatically through later milestones as feasible, without asking me to manually make each edit. Only ask me for missing files, legal source inputs, or major choices that genuinely block progress. My priority order is: playable Platinum base > reliable all-trainer doubles > choose two of six starters > integrate all 63 as new species > route/trainer distribution and full-game balance.
