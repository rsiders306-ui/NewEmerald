# Milestone A: verified Platinum baseline

The BeaconDex Platinum source baseline is `pret/pokeplatinum` commit
`c6689696d5fb51a644239702cb556eb52012a46a`, merged into the project on the
`beacondex-platinum` branch.

## Reconstructed ROM

The clean source tree was built on 2026-11-02 and passed every upstream
checksum test.

| Property | Verified value |
| --- | --- |
| Title | `POKEMON PL` |
| Game code | `CPUE` |
| Maker code | `01` |
| ROM revision | `1` |
| Size | `134217728` bytes |
| SHA-1 | `0862ec35b24de5c7e2dcb88c9eea0873110d755c` |

The upstream Meson suite reported:

```text
1/5 SBIN Checksums - Shared       OK
2/5 SBIN Checksums - For Revision OK
3/5 SBIN Checksums - ARM7         OK
4/5 Filesystem Checksums          OK
5/5 ROM Checksum                  OK
```

This proves that the source and toolchain reconstruct the supported US Rev 1
release exactly before hack changes are applied. Modified builds use `make rom`;
the clean-ROM checksum test is then expected to differ.

## Cloud toolchain

This kernel cannot directly execute the 32-bit Metroskrew wrappers. The tested
cloud setup uses native x86-64 wrappers and launches the proprietary 32-bit ARM
compiler executables through `qemu-i386`. ARM GNU tools, QEMU, Flex, Bison,
Ninja, NASM, libpng, and zlib are installed in a repository-local cache without
root access. See `tools/beacondex/cloud` for the reproducible setup.

## Supplied ROM inspection status

The uploaded ROM archive is larger than the environment's 32 MiB attachment
download limit and is not mounted as a local file. Its bytes have therefore not
been inspected, altered, or used in this build. Exact identification of that
copy remains pending until the same ZIP is provided in chunks smaller than
32 MiB. The source baseline above identifies the build target, not the user's
unreadable archive.

No commercial ROM is stored in this repository. The clean reconstructed ROM is
a private validation artifact under the ignored build directory.
