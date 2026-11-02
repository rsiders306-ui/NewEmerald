#!/usr/bin/env bash

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    echo "source this file from a shell or from another script" >&2
    exit 2
fi

BEACONDEX_REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
export BEACONDEX_REPO_ROOT
export BEACONDEX_TOOLCHAIN_ROOT="$BEACONDEX_REPO_ROOT/.cache/beacondex/toolchain"

if [[ ! -x "$BEACONDEX_TOOLCHAIN_ROOT/usr/bin/qemu-i386" ]]; then
    echo "BeaconDex cloud toolchain is missing; run tools/beacondex/cloud/bootstrap.sh" >&2
    return 1
fi

export PATH="$BEACONDEX_TOOLCHAIN_ROOT/usr/bin:$PATH"
export M4="$BEACONDEX_TOOLCHAIN_ROOT/usr/bin/m4"
export BISON_PKGDATADIR="$BEACONDEX_TOOLCHAIN_ROOT/usr/share/bison"
export PKG_CONFIG="$(command -v pkg-config)"
export PKG_CONFIG_FOR_BUILD="$PKG_CONFIG"
export PKG_CONFIG_SYSROOT_DIR="$BEACONDEX_TOOLCHAIN_ROOT"
export PKG_CONFIG_SYSROOT_DIR_FOR_BUILD="$BEACONDEX_TOOLCHAIN_ROOT"
export PKG_CONFIG_PATH="$BEACONDEX_TOOLCHAIN_ROOT/usr/lib/x86_64-linux-gnu/pkgconfig"
export PKG_CONFIG_PATH_FOR_BUILD="$PKG_CONFIG_PATH"
export LD_LIBRARY_PATH="$BEACONDEX_TOOLCHAIN_ROOT/usr/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export SKREW_QEMU="$BEACONDEX_TOOLCHAIN_ROOT/usr/bin/qemu-i386"
export SKREW_QEMU_LD_PREFIX="$BEACONDEX_TOOLCHAIN_ROOT"
