#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/../../.." && pwd)"
cache_root="$repo_root/.cache/beacondex"
downloads="$cache_root/downloads"
toolchain_root="$cache_root/toolchain"
skrew_source="$cache_root/metroskrew-source"

for command in bash curl git make gcc g++ python3 dpkg-deb pkg-config sha256sum tar xz; do
    if ! command -v "$command" >/dev/null; then
        echo "missing required host command: $command" >&2
        exit 1
    fi
done

mkdir -p "$downloads"

fetch_manifest() {
    local manifest="$1"
    while IFS=$'\t' read -r checksum filename url; do
        [[ -z "$checksum" || "$checksum" == \#* ]] && continue
        destination="$downloads/$filename"
        if [[ -f "$destination" ]] && echo "$checksum  $destination" | sha256sum --check --status; then
            continue
        fi
        temporary="$destination.download"
        curl --fail --location --retry 3 --output "$temporary" "$url"
        echo "$checksum  $temporary" | sha256sum --check --status
        mv "$temporary" "$destination"
    done < "$manifest"
}

fetch_manifest "$script_dir/packages.tsv"
fetch_manifest "$script_dir/assets.tsv"

package_stamp="$(sha256sum "$script_dir/packages.tsv" | awk '{print $1}')"
if [[ ! -f "$toolchain_root/.package-stamp" ]] || [[ "$(<"$toolchain_root/.package-stamp")" != "$package_stamp" ]]; then
    new_root="$cache_root/toolchain.new"
    rm -rf "$new_root"
    mkdir -p "$new_root"
    while IFS=$'\t' read -r checksum filename url; do
        [[ -z "$checksum" || "$checksum" == \#* ]] && continue
        dpkg-deb --extract "$downloads/$filename" "$new_root"
    done < "$script_dir/packages.tsv"
    ln -s usr/lib "$new_root/lib"
    printf '%s\n' "$package_stamp" > "$new_root/.package-stamp"
    rm -rf "$toolchain_root"
    mv "$new_root" "$toolchain_root"
fi

expected_skrew_commit="6693130c796ba2b6056e6d5b8c179ce7e6548171"
if [[ ! -d "$skrew_source/.git" ]] || [[ "$(git -C "$skrew_source" rev-parse HEAD 2>/dev/null || true)" != "$expected_skrew_commit" ]]; then
    rm -rf "$skrew_source"
    git clone --depth=1 --branch 0.1.3 https://github.com/mid-kid/metroskrew.git "$skrew_source"
fi
if [[ "$(git -C "$skrew_source" rev-parse HEAD)" != "$expected_skrew_commit" ]]; then
    echo "unexpected Metroskrew source commit" >&2
    exit 1
fi

git -C "$skrew_source" reset --hard "$expected_skrew_commit" >/dev/null
git -C "$skrew_source" clean -fdx >/dev/null
git -C "$skrew_source" apply "$script_dir/metroskrew-qemu.patch"

mkdir -p "$skrew_source/host-wrap"
printf '%s\n' \
    '#define PROGRAM_NAME "skrewrap"' \
    '#define BIN_TO_LIBDIR "../lib/metroskrew"' \
    '#define BIN_TO_DATADIR "../share/metroskrew"' \
    '#define DEFAULT_MWCCARM "4.0-1051"' \
    '#define DEFAULT_MWLDARM "2.0-99"' \
    '#define DEFAULT_MWASMARM "1.0-27"' \
    > "$skrew_source/wrap/config.h"

gcc -O2 -I"$skrew_source/wrap" -o "$skrew_source/host-wrap/skrewrap" "$skrew_source/wrap/wrap.c"
gcc -O2 -I"$skrew_source/wrap" -DWRAP_PROG='"mwccarm"' -o "$skrew_source/host-wrap/mwccarm" "$skrew_source/wrap/wrap.c"
gcc -O2 -I"$skrew_source/wrap" -DWRAP_PROG='"mwldarm"' -o "$skrew_source/host-wrap/mwldarm" "$skrew_source/wrap/wrap.c"
gcc -O2 -I"$skrew_source/wrap" -DWRAP_PROG='"mwasmarm"' -o "$skrew_source/host-wrap/mwasmarm" "$skrew_source/wrap/wrap.c"

skrew_dir="$repo_root/tools/metroskrew"
skrew_hashes=(
    'f1653bd1328a35904504ca714300d62ce9e9baf8ab6af68dcef898f98c16a764  skrewrap'
    '3980e3e0374874818165e126b402c5e318701b51ee042dff46617f2c54bf40b5  mwccarm'
    'efadd66cb06ddb62c8697e5c54fc13795953840fe11d3ecb379376e52c342bf8  mwldarm'
    '3bc0a5823235f2dbf02dfce699b4a71a86e0f3087c45fa618b9d7e7d1d93df15  mwasmarm'
)
if [[ ! -d "$skrew_dir/lib" ]]; then
    extract_root="$cache_root/metroskrew-release"
    rm -rf "$extract_root"
    mkdir -p "$extract_root"
    tar -xf "$downloads/metroskrew-linux.tar.xz" -C "$extract_root"
    rm -rf "$skrew_dir"
    mv "$extract_root/metroskrew" "$skrew_dir"
fi
for wrapper in skrewrap mwccarm mwldarm mwasmarm; do
    install -m 755 "$skrew_source/host-wrap/$wrapper" "$skrew_dir/bin/$wrapper"
done
for hash_entry in "${skrew_hashes[@]}"; do
    expected="${hash_entry%% *}"
    wrapper="${hash_entry##* }"
    echo "$expected  $skrew_dir/bin/$wrapper" | sha256sum --check --status
done

meson_dir="$repo_root/subprojects/meson-1.12.0"
expected_meson_commit="ab4508e6abe338a3bd2e6eb5da1d18b8cf55dc93"
if [[ ! -d "$meson_dir/.git" ]] || [[ "$(git -C "$meson_dir" rev-parse HEAD 2>/dev/null || true)" != "$expected_meson_commit" ]]; then
    rm -rf "$meson_dir"
    git clone --depth=1 --branch 1.12.0 https://github.com/mesonbuild/meson.git "$meson_dir"
fi
if [[ "$(git -C "$meson_dir" rev-parse HEAD)" != "$expected_meson_commit" ]]; then
    echo "unexpected Meson source commit" >&2
    exit 1
fi

mkdir -p "$repo_root/subprojects/packagecache"
for asset in rapidjson-1.1.0.tar.gz rapidjson_1.1.0-2_patch.zip yyjson-0.12.0.tar.gz yyjson_0.12.0-1_patch.zip; do
    cp "$downloads/$asset" "$repo_root/subprojects/packagecache/$asset"
done

source "$script_dir/env.sh"
arm-none-eabi-gcc --version >/dev/null
ninja --version >/dev/null
qemu-i386 --version >/dev/null
"$skrew_dir/bin/mwccarm" --version >/dev/null
"$skrew_dir/bin/mwldarm" --version >/dev/null
"$skrew_dir/bin/mwasmarm" --version >/dev/null

echo "BeaconDex cloud toolchain is ready"
