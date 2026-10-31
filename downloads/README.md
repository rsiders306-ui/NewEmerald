# BeaconDex: Modern Emerald — playtest patch

[Download the patch ZIP](./BeaconDex-ModernEmerald-playtest.bps.zip?raw=true)

## Apply the patch

1. Download and extract `BeaconDex-ModernEmerald-playtest.bps.zip`.
2. Open [ROM Patcher JS](https://www.marcrobledo.com/RomPatcher.js/) or another BPS-compatible patcher.
3. Select your **Modern Emerald 3.6** `.gba` as the base ROM. Do not select original Emerald.
4. Select `BeaconDex-ModernEmerald-playtest.bps` as the patch, then apply and save the resulting `.gba`.
5. Open the patched game in your GBA emulator and start a new game.

The base must match SHA-256:
`bc7286dca750cf735480fece3ff68c7d86ecbf8391031b5ca2964da78fc945a1`

The patched ROM must match SHA-256:
`222c0ed588905745292a2bc291a3f159d695a749647ae9e01e6055fa84250626`

## Status

All 27 replacements are implemented. The build and emulator smoke tests passed,
including starter/evolution/type checks and actual save/cold reload. Artwork
remains provisional: 18 back sprites are placeholder drafts, shiny palettes and
animations need refinement, some stats retain documented provisional values,
and a full-story playthrough is outstanding. The native-source build is based on
Modern Emerald `Release3.6` (`ec1088c`).

This branch contains the patch ZIP and checksums. No ROM is included.
