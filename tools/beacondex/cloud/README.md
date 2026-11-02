# Cloud build setup

Run from the repository root:

```sh
tools/beacondex/cloud/bootstrap.sh
tools/beacondex/cloud/build.sh baseline
```

`bootstrap.sh` installs the pinned ARM, QEMU, graphics, parser, and build tools
under `.cache/beacondex` without root access. Every downloaded binary package or
archive is SHA-256 checked. Meson and Metroskrew source checkouts are pinned to
exact commits.

The managed cloud kernel does not execute i386 programs directly. The setup
builds native wrappers that launch the original Metrowerks compiler executables
through QEMU. This preserves the exact compiler output needed to reconstruct
Platinum.

Build modes:

```sh
# Exact clean US Rev 1 reconstruction and all five checksum tests
tools/beacondex/cloud/build.sh baseline

# Modified BeaconDex ROM; the clean-ROM checksum is expected to differ
tools/beacondex/cloud/build.sh rom

# Logging/GDB-enabled modified build
tools/beacondex/cloud/build.sh debug
```

Set `BUILD` to select another build directory and `ROM_REVISION=0` to target the
supported US Rev 0 release. The project defaults to Rev 1.
