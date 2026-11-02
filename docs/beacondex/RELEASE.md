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
- SHA-1: `cf5cf6a2e6fee980659cf41ad38a020e6c37670b`
- SHA-256: `e589b251e95b7558ab1b8c27e3ae1ccacfbf98d26518ed06a528936b77369234`

The redistributable patch is
`dist/BeaconDex-Platinum-v0.1.0-US-Rev1.bps`:

- size: 28,090,228 bytes
- SHA-1: `a18f392e472708ab1b55d630905271a7faf8f60a`
- SHA-256: `299eb1d3f9e3351d7612e7c87c720235bbf242c775f03aec53165cc54cb1b15b`

The complete patch package is
`dist/BeaconDex-Platinum-v0.1.0-Patch-Package.zip`:

- size: 18,962,355 bytes
- SHA-1: `bf14b71cd21910eb7a6c72c2e12526fc1a553567`
- SHA-256: `c5178421cd873c7040ae2f8d2327ee43848fe2c91f63c2fb4b71a4e578e0de5a`

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

The complete ROM and every edited data archive compile. Consolidated release
validation now includes a boot-integrity audit of the NDS header and all 2,135
SDAT payload records, in addition to the trainer, starter, distribution,
Frontier, Fairy, species-runtime, audio, and save-layout audits. The BPS round
trip reconstructs the target byte-for-byte.

The exact target above reaches the Pokémon Platinum title animation in a fresh
melonDS 1.1 configuration and in DeSmuME 0.9.13. melonDS reports successful
secure-area decryption and no ARM9 data abort. Runtime evidence and the startup
failure analysis are stored under `docs/beacondex/evidence` and
`BOOT_FAILURE_ANALYSIS.md`.

The previous target SHA-256
`9c54fe91735278fcc0efee2b26804bcc64d1060367ff310279494bae13b55f96`
is revoked because its SDAT FAT offsets are malformed. Fresh saves are required;
vanilla-save migration and a complete story playthrough remain validation work.
