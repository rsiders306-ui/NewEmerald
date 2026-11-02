# BeaconDex integration-pack audit

The supplied integration pack contains 424 files. Its manifest SHA-256 is:

```text
0dd9aa6a846129d78714ae3cfb11c1de4474d5458fae8de4d156d59ab761f1f3
```

The pack contains all 63 intended species in 21 three-stage families and 252
64-by-64 RGBA draft battle images: normal and shiny front and back images for
every species.

## Source precedence

Mechanical data is resolved in this order:

1. explicit user decisions in the project specification;
2. `user_override_27_source.json`;
3. provisional legacy entries.

The historical 27-species replacement map is Emerald-specific and is not used.
BeaconDex Platinum assigns additive IDs after Arceus and preserves every
original species.

## Data requiring documented defaults

- The pack omits height, weight, catch rate, growth group, egg groups, base
  friendship, habitat, and cries.
- All 36 newer species lack TM/HM compatibility. The older 27 contain
  Emerald-era machine lists that require a Platinum audit.
- Twelve non-final species do not have structured evolution methods despite
  clear family ordering: Trillkit, Cantacat, Medijest, Chartickle, Rookit,
  Vroombrel, Groovette, Sautène, Emberrest, Forguard, Timblet, and Nestelle.
- Pokédex prose is draft or unapproved.
- Six proposed custom hidden abilities are prohibited by the specification and
  require existing-ability substitutions: Discipler, Dad Strength, Mama
  Instinct, Sermon Notes, Deadpan Drive, and Family First.
- Later-generation moves and abilities require engine work or documented Gen IV
  substitutions. The known set includes Pixilate, Friend Guard, Ice Scales,
  Fairy Wind, Dazzling Gleam, Moonblast, Play Rough, Aurora Veil, Pollen Puff,
  Quiver Dance, Struggle Bug, and Heal Pulse.

## Recorded design conflicts

- Terraptor is 545 BST in the override and master manifest but 550 elsewhere.
  The override's 545 value is used until the user changes it.
- `Heartistle` is the selected ten-character name. Older paths may still use
  `Hearthistle`.
- The Nilecub family remains provisional as Water, Water, Water/Fairy.
- Older summaries disagree with the current manifest for parts of the Ariapurr,
  Sermedic, Talladevil, Veloura, and Heartistle families. The override/manifest
  wins while each conflict remains listed for review.

## Graphics status

All 252 battle drafts have valid dimensions and alpha, and no normal/shiny pair
is pixel-identical. They are not ready-made Platinum sprites. Platinum expects
indexed, 16-color, two-frame 160-by-80 images plus separate palettes. Fifty-four
drafts across 27 species currently exceed 16 colors.

Only the original 27 species have draft party icons and footprints. The newer
36 need both. Several rear sprites are silhouette-level drafts. Initial engine
integration may use clearly labeled generated placeholders, but final graphics
must be reviewed in an emulator before being called complete.
