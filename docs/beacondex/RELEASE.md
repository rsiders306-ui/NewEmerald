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
- SHA-1: `97799e74e448431f3359cf7be879882826a26dec`
- SHA-256: `9c54fe91735278fcc0efee2b26804bcc64d1060367ff310279494bae13b55f96`

The redistributable patch is
`dist/BeaconDex-Platinum-v0.1.0-US-Rev1.bps`:

- size: 28,090,228 bytes
- SHA-1: `57cf2ad156b089417daebabf717ec9f4d55468cb`
- SHA-256: `9d6ce0c99ad5b59989c4d0349b848174869ba7f2eba538ce860286e65665724f`

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

The complete ROM and every edited data archive compile. All 12 consolidated
audits pass, covering trainer parties and battle flow, trainer balance and AI,
starter pairs, wild and trainer distribution, all five Frontier facilities,
compiled cries, compiled Fairy assets, species runtime archives, and save
layout. The BPS round trip reconstructs the target byte-for-byte.

No DS emulator is installed in the current environment, so this is a compiled
test build rather than an emulator-certified release. Fresh saves are required;
vanilla-save migration and in-emulator progression remain validation work.
