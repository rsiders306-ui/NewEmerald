# Six-choice starter pair

## Selection flow

Route 201 presents a typed list containing Glimbark, Calflank, Zephylet,
Turtwig, Chimchar, and Piplup. The player selects two entries in sequence,
cannot select the same species twice, sees both names in a confirmation prompt,
and can restart the selection before confirming.

Both choices are granted at level 5 while the field event remains locked. The
two grants happen before the first Barry battle, so its forced Double Battle
always starts with two player battlers. The chosen pair is stored in the
existing `VAR_PLAYER_STARTER` slot and the renamed unused
`VAR_PLAYER_SECOND_STARTER` slot; this does not add a new save field.

## Barry's pair

Barry receives a deterministic pair selected from the four species the player
did not choose. The 15-pair mapping uses the starters' base types to avoid a
matchup where both of Barry's starters can be assigned a super-effective target
in the player's pair. The pair is stored in two formerly unused variables and
is applied to party slots zero and one for all 33 Barry trainer records.

Each dynamic line evolves at its own level thresholds. Dynamic party members
use their species' level-up moves. A later fixed Sinnoh starter in the original
Barry parties is changed to Staravia or Staraptor, preserving his bird line and
preventing him from carrying a third starter family.

The runtime substitution keeps the following roster structure:

| Battle stage | Stored roster shape | Runtime roster shape |
| --- | --- | --- |
| Route 201/203 | two early species | Barry's two starters |
| Route 209 through Canalave | bird, support members, legacy starter | Barry's two starters, retained support members, bird |
| Spear Pillar | support, bird, Munchlax, Heracross, support, legacy starter | Barry's two starters, Munchlax, Heracross, support, Staraptor |
| League and later six-member teams | bird, support, Heracross, support, Snorlax, legacy starter | Barry's two starters, Heracross, support, Snorlax, Staraptor |

The Spear Pillar source records place Munchlax outside the two dynamic slots so
Barry keeps that signature line when he acts as the player's partner.

## Unchosen starter availability

The three BeaconDex starter bases have permanent early encounters. The three
Sinnoh starter bases have rare recovery encounters later in the game: Turtwig
in Great Marsh Area 2, Chimchar outside Fuego Ironworks, and Piplup while
Surfing at Lake Acuity. As a result, all four unchosen species are obtainable
for each of the 15 possible initial pairs.

## First-starter compatibility

Scripts that still branch on the first starter use explicit, deterministic
fallbacks for Glimbark, Calflank, and Zephylet. Rowan treats all three as
unevolved starters. The Jubilife and Veilstone partner battles select the
Turtwig-player trainer record, whose counterpart starter is Piplup, matching
the custom-first fallback returned by `SystemVars_GetPlayerCounterpartStarter`.
The Fight Area and Spear Pillar partner battles select their Piplup-player
support roster before Barry's two dynamic starter substitutions are applied.

The Underground Man awards a Piplup Doll for a custom first starter. The three
starter-themed accessory gifts also initialize a valid mask before their
legacy three-way branches, so none can fall through with item ID zero.

## Verification

- `starter_pair_audit.py` checks both selection orders for all 15 unordered
  player pairs, confirms that Barry receives two distinct unchosen species, and
  rejects two simultaneous base-type hard counters
- all 15 unordered player pairs leave all four unchosen species obtainable
- the same audit simulates all 495 pair/record combinations across all 33 Barry
  records, checks evolved substitutions and level-up attacks, and rejects
  duplicate birds, species, nonzero replacement forms, and lost Munchlax,
  Snorlax, or Heracross identity
- it also checks the Sandgem dialogue, accessory gifts, Underground Man doll,
  counterpart C fallback, and the Jubilife, Veilstone, Fight Area, and Spear
  Pillar partner-team defaults for custom first starters
- Route 201 script and message bank compile
- the save-variable and trainer-substitution C units compile
- the complete integrated ROM links successfully
- `trainer_battle_flow_audit.py` reports all 104 trainer starts safe

Emulator validation is still required for the field-list layout, both party
grants, the first battle, a later Barry battle, and save/reload behavior.
