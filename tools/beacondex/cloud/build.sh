#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$script_dir/env.sh"
cd "$BEACONDEX_REPO_ROOT"

build_dir="${BUILD:-build-cloud-r1}"
revision="${ROM_REVISION:-1}"
mode="${1:-rom}"

case "$mode" in
baseline)
    BUILD="$build_dir" ROM_REVISION="$revision" make check
    ;;
rom)
    BUILD="$build_dir" ROM_REVISION="$revision" make rom
    ;;
debug)
    BUILD="$build_dir" ROM_REVISION="$revision" make debug
    ;;
*)
    echo "usage: $0 [baseline|rom|debug]" >&2
    exit 2
    ;;
esac
