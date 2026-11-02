# BeaconDex Platinum development guide

BeaconDex Platinum targets Pokémon Platinum US Rev 1 and keeps the original
Sinnoh story while changing offline NPC Trainer battles to doubles. It adds 63
BeaconDex species after Arceus, implements Fairy, offers six starters with two
distinct selections, and distributes the added roster through Sinnoh.

## Build

The checked-in cloud bootstrap installs the pinned toolchain in the repository
cache. From the repository root:

```sh
tools/beacondex/cloud/bootstrap.sh
BUILD=build-cloud-r1 tools/beacondex/cloud/build.sh rom
```

The modified ROM is written to `build-cloud-r1/pokeplatinum.us.nds`. The clean
baseline can be reconstructed and checked independently:

```sh
tools/beacondex/cloud/build.sh baseline
```

The baseline command must pass all five upstream checksum tests for Pokémon
Platinum US Rev 1 before it is used as a patch base.

## Validation

After building the ROM and release patch, run the consolidated report with:

```sh
python3 tools/beacondex/integration_report.py
```

`data/beacondex/integration_report.json` inventories the 63 species, 252
logical battle-sprite slots, starter combinations, encounter locations,
Trainer assignments, doubles coverage, custom cries, Fairy moves, build hashes,
release-patch round trip, design conflicts, and known validation limits.

## Release patch

The project distributes a BPS patch rather than a commercial ROM. Create and
verify it against the exact clean baseline with:

```sh
python3 tools/beacondex/bps_patch.py create \
  build/pokeplatinum.us.nds \
  build-cloud-r1/pokeplatinum.us.nds \
  dist/BeaconDex-Platinum-v0.1.0-US-Rev1.bps

python3 tools/beacondex/bps_patch.py apply \
  build/pokeplatinum.us.nds \
  dist/BeaconDex-Platinum-v0.1.0-US-Rev1.bps \
  /tmp/BeaconDex-Platinum-reconstructed.nds

cmp build-cloud-r1/pokeplatinum.us.nds \
  /tmp/BeaconDex-Platinum-reconstructed.nds
```

The supported base identity and current artifact hashes are recorded in
`RELEASE.md` and `dist/CHECKSUMS.txt`.

## Source map

- `PROJECT_SPEC.md` preserves the supplied development specification.
- `BASELINE_BUILD.md` records the exact clean reconstruction.
- `ENGINE_DECISIONS.md` describes registry, save, Fairy, and battle-format
  decisions.
- `STARTER_PAIR.md` documents selection, Barry's pair, and recovery encounters.
- `TRAINER_DOUBLES.md` and `FRONTIER_DOUBLES.md` document battle conversion.
- `SPECIES_INTEGRATION.md` documents data, graphics, audio, and open art work.
- `WILD_DISTRIBUTION.md` and `TRAINER_DISTRIBUTION.md` document placement.
- `INTEGRATION_PACK_AUDIT.md` records source precedence and unresolved design
  conflicts from the supplied pack.

The ROM, sprites, icons, footprints, and audio compile from source. Runtime
playthrough evidence still requires a Nintendo DS emulator; the cloud image
used for this build does not include one. Fresh saves are required until a
vanilla-save migration is implemented and tested. Cry audio uses documented
templates, and the new species' egg-move and tutor lists remain empty.
