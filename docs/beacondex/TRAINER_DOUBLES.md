# Trainer Double Battle integration

## Engine policy

`FieldBattleDTO_New` adds `BATTLE_TYPE_DOUBLES` to offline trainer battles.
Wild battles and link battles retain their original formats. Battle Frontier
battles remain temporarily excluded until the Battle Hall's one-Pokémon party
selection and record flow can be expanded safely.

The original trainer JSON `double_battle` field still identifies paired
overworld NPCs. It was not set globally because the field also controls partner
object lookup, approach movement, and paired dialogue.

## Trainer parties

Every non-sentinel trainer record now has at least two explicit party members,
and `trainerproc` rejects future records below that minimum. The 928 records are
distributed as follows:

| Party size | Records |
| --- | ---: |
| 0 (`TRAINER_NONE`) | 1 |
| 2 | 657 |
| 3 | 189 |
| 4 | 31 |
| 5 | 27 |
| 6 | 23 |

The first Barry teams use deliberate two-starter pairs. The remaining 397
one-member records received deterministic same-class, same-level partners as a
safe structural pass. Their moves, items, and species remain balance candidates
for the later regional-distribution milestone.

## Battle-flow coverage

The field-script inventory contains 104 trainer battle starts:

- 97 direct trainer starts
- 3 Route 201 first-battle variants
- 4 tag battles with an AI partner

All 97 direct starts have a reviewed two-battler path. Talk, rematch, Gym,
Galactic, Barry, Elite Four, Cynthia, daily, Restaurant, Mansion, and optional
challenge scripts refuse cleanly when the player lacks two usable battlers. An
active AI partner satisfies the check. Automatic sight trainers wait until the
party is eligible so their approach script cannot repeatedly retrigger and trap
the player.

Route 201's three first-battle commands are safe: the selection event grants
both distinct level-five starters while the event is locked and before any
Barry battle branch can run.

## Dialogue and sequential battles

Forced single-trainer doubles use the normal defeat message. The 28 existing
composite Double Battle records also define a combined normal defeat entry so
both original lines remain available. Existing Frontier doubles retain their
Frontier defeat-message path.

Floaroma Meadow heals the party between its two forced consecutive Grunt
battles, and Stark Mountain does the same between Mars and Jupiter. Cynthia's
automatic room event returns an ineligible player to the preceding elevator.

## Verification

The following checks passed on 2026-11-02:

- `trainer_party_audit.py`: 928 records, zero minimum-party violations
- `trainer_battle_flow_audit.py`: 104 calls, 104 safe, zero deferred, zero
  violations
- all trainer JSON parsed with unique message types
- all changed C, battle scripts, field scripts, text banks, and trainer archives
  compiled
- the complete modified US Rev 1 ROM linked successfully

The original doubles-only checkpoint ROM was 134,217,728 bytes with SHA-1
`0e725d96dd0fd56ebd43042b79bcae99a20267f7`. The later integrated starter,
Fairy, and 63-species checkpoint also links successfully; Route 201 is no longer
deferred.
