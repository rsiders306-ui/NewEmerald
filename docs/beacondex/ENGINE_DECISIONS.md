# Engine decisions and compatibility notes

## Species registry

The 63 BeaconDex species use contiguous IDs 494 through 556. Egg and Bad Egg
move to 557 and 558. Species IDs are stored in 16-bit Pokémon data and in the
10-bit trainer-party field, so this range is representable.

Save blocks that size arrays from `NATIONAL_DEX_COUNT` or `MAX_SPECIES` grow.
Fresh BeaconDex saves are the initial compatibility target. Vanilla-save
migration must be tested before existing saves are claimed to work.

## Fairy

Fairy is appended after Dark so all vanilla type IDs remain stable. Battles use
the standard Fairy offense and defense relationships. Steel retains its Gen IV
Ghost and Dark resistances so unrelated vanilla matchups stay unchanged.

Battle Hall retains its original selectable type categories. Its UI and packed
rank data have a fixed 17-type design; Fairy Pokémon can battle there, but a
Fairy rank category needs a separate save/UI expansion. The main Hall ladder
now selects two same-species Pokémon and runs physical Double Battles while
retaining its logical Single record bucket and Matron progression.

## Trainer doubles

Trainer JSON `double_battle` flags retain their vanilla meaning for paired
overworld NPCs, dialogue, and approach animation. The global trainer format is
forced at battle-DTO construction for offline trainer battles. Wild, catching
tutorial, link, and temporarily Battle Hall battles are unaffected.

Every regular trainer record is required to contain at least two Pokémon. Party
data is expanded separately from the battle-format hook so story scripts do not
depend on paired-trainer messages that do not exist.

Talking to a trainer or requesting a rematch requires two usable party members
and shows one shared explanation when that requirement is not met. An active AI
partner supplies the second battler and satisfies this check. Sight trainers,
including the Hearthome Gym's custom sight system, temporarily do not engage
while the player has fewer than two usable party members. Triggering their
refusal script automatically would repeat before the player could move away and
could prevent the player from returning to heal.

## Starter order

Custom starter species must exist before the selection scene can refer to them.
Implementation therefore introduces the Fairy/species registry and three custom
base starters before replacing Route 201's three-choice flow. The player then
receives two distinct level-five choices before the first required trainer
battle.
