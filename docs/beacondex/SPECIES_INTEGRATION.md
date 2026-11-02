# BeaconDex species integration

## Registry and source data

All 63 BeaconDex species are appended as IDs 494 through 556. The original 493
species retain their IDs; Egg and Bad Egg move to 557 and 558. The normalized
manifest at `data/beacondex/species_normalized.json` records source precedence,
post-Gen-IV move and ability substitutions, defaults, and unresolved decisions.

The generator at `tools/beacondex/generate_species_sources.py` creates the full
species source tree deterministically from that manifest and the private
integration pack. It validates 63 species in 21 three-stage families, their
evolution targets, data files, sprite dimensions, palette indices, icons,
footprints, and required asset inventory.

The Regional Pokédex appends the families as entries 211 through 273. The
original 210-entry seen requirement still unlocks the National Pokédex so the
new postgame entries do not block the vanilla story transition.

## Runtime data

Each species has two type slots, base stats, supported ability slots, catch and
experience data, EV yields, gender and breeding data, friendship, learnsets,
TM/HM compatibility, evolution data, Pokédex display metadata, and Pal Park
fallback data. Four official Fairy attacks are implemented with Gen-IV-supported
battle effects: Fairy Wind, Dazzling Gleam, Play Rough, and Moonblast. Other
post-Gen-IV moves and abilities remain mapped to documented substitutes; this
release adds no signature moves, custom abilities, or Mega Evolution mechanics.
All Fairy-typed BeaconDex species receive at least one Fairy attack by level-up.
Early learnsets use Fairy Wind, special attackers progress through Dazzling
Gleam to Moonblast, and physical attackers receive Play Rough later.
Dazzling Gleam is level-up-only because Platinum’s fixed TM01–TM92 item range
has no TM99 slot; adding a new machine item requires a separate bag/save/UI
expansion.

Adding 63 Pokédex bits expands save structures derived from the species count.
Fresh saves are required until a vanilla-save migration has been implemented
and tested.

## Graphics and audio

The integration supplies all 252 battle sprite slots: normal and shiny,
front and back, for every species. They are converted to Platinum's indexed
160-by-80 two-frame sheets and 16-color palettes. The author drafts provide one
pose, so both animation frames currently duplicate that pose.

The 27 supplied party icons are remapped to Platinum's shared icon palettes.
The remaining 36 icons are generated placeholders based on their front sprite.
All footprints use the game's two-tile format: visible art in the left 16-by-16
tile and palette index 12 in the unused right tile. The 36 generated footprints
remain silhouette placeholders.

The supplied shiny drafts for some of the original 27 species do not share the
normal sprite's silhouette. Conversion preserves the normal outline and maps
the shiny colors onto it, which avoids transparent-pixel corruption but needs
an art review. Every species currently reuses a documented vanilla cry template
until authored cries are available.

## Text and open design decisions

English Pokédex text is copied into all six required language banks as a
technical fallback. Category strings are constrained to the stock Pokédex UI
width. The following remain review items rather than silent canon changes:

- legacy typing and learnset candidates for the original 27 species
- Terraptor's conflicting 545/550 BST sources
- Heartistle as Emily's final species name
- the provisional Water, Water, Water/Fairy typing for Moses's family
- generated icons, footprints, repeated sprite frames, temporary cries, and
  untranslated non-English text

## Regeneration

From the repository root, with the extracted private pack at the default path:

```sh
python3 tools/beacondex/generate_species_sources.py --clean
```

The command writes a staged source tree and a machine-readable validation report
under `/tmp/beacondex-species-generator`; it does not overwrite the checkout.
