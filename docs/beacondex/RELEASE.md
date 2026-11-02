# BeaconDex Platinum v0.1.0 build

## Exact patch base

The BPS patch applies only to the clean US Pokémon Platinum revision 1 ROM:

- title: `POKEMON PL`
- game code: `CPUE`
- revision byte: `1`
- size: 134,217,728 bytes
- SHA-1: `0862ec35b24de5c7e2dcb88c9eea0873110d755c`
- SHA-256: `fbce4c4def0c7797f8dd238a3d7a5e48b4a7e3abd86890ac65f6321cef781bdb`

## Build and patch artifacts

The source build produced `build-cloud-r1/pokeplatinum.us.nds`:

- size: 134,217,728 bytes
- SHA-1: `81236488ad84dcd71b3e7047406875837b95721f`
- SHA-256: `32d3d08790573e90a8a7b2fc463af330bcafae1ff97ab3ada0894ebf25fd63b6`

The private redistributable patch is
`dist/BeaconDex-Platinum-v0.1.0-US-Rev1.bps`:

- size: 23,818,629 bytes
- SHA-256: `aa730a182619332588a37ebac7c847301abbb64fbcd432248d87b4d7970361bd`

Apply the BPS with a standard patcher such as Floating IPS, or with the bundled
tool:

```sh
python3 tools/beacondex/bps_patch.py apply \
  /path/to/clean-platinum-us-rev1.nds \
  dist/BeaconDex-Platinum-v0.1.0-US-Rev1.bps \
  /path/to/BeaconDex-Platinum.nds
```

The bundled tool applied the release patch to the exact clean baseline and
reconstructed the target byte-for-byte. Its result matched both target hashes
above.

## Validation status

The complete ROM and every edited data archive compile. The trainer-party,
trainer-flow, wild-distribution, trainer-distribution, and Frontier audits pass.
No DS emulator is installed in the current environment, so this is a compiled
test build rather than an emulator-certified release. Fresh saves are required;
vanilla-save migration and in-emulator progression remain validation work.
