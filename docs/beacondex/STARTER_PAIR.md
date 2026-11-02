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

Barry receives the first two species in the ordered six-choice list that the
player did not choose. This produces a distinct unchosen pair for all 15 player
pair combinations. The pair is stored in two formerly unused variables and is
applied to party slots zero and one for all 33 Barry trainer records.

Each dynamic line evolves at its own level thresholds. Dynamic party members
use their species' level-up moves. A later fixed Sinnoh starter in the original
Barry parties is changed to Staravia or Staraptor, preserving his bird line and
preventing him from carrying a third starter family.

## Unchosen starter availability

The three BeaconDex starter bases have permanent early encounters. The three
Sinnoh starter bases have rare recovery encounters later in the game: Turtwig
in Great Marsh Area 2, Chimchar outside Fuego Ironworks, and Piplup while
Surfing at Lake Acuity. As a result, all four unchosen species are obtainable
for each of the 15 possible initial pairs.

## Verification

- all 15 unordered player pairs map to distinct complementary Barry pairs
- all 15 unordered player pairs leave all four unchosen species obtainable
- all 33 Barry records retain at least two party members
- Route 201 script and message bank compile
- the save-variable and trainer-substitution C units compile
- the complete integrated ROM links successfully
- `trainer_battle_flow_audit.py` reports all 104 trainer starts safe

Emulator validation is still required for the field-list layout, both party
grants, the first battle, a later Barry battle, and save/reload behavior.
