#!/usr/bin/env python3
"""Generate a staged pokeplatinum source tree for the 63 BeaconDex species.

The generator never changes the input repository.  It writes only the files that
must be copied into the repository after review: species directories, the species
constant registry, and the expanded Sinnoh Pokédex registry.
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import os
import re
import shutil
import sys
import textwrap
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Iterable, Sequence

from PIL import Image


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PACK = Path(
    os.environ.get(
        "BEACONDEX_PACK",
        REPO_ROOT.parent / "beacondex-pack" / "BeaconDex_63_Complete_Integration_Pack",
    )
)
EXPECTED_SPECIES = 63
EXPECTED_FIRST_ID = 494
EXPECTED_LAST_ID = 556
SHEET_SIZE = (160, 80)
ICON_SIZE = (32, 64)
FOOTPRINT_SIZE = (32, 16)
FRAME_ORIGIN = (8, 16)
OPAQUE_ALPHA = 128
LOCALES = ("en", "fr", "de", "it", "es", "jp")
POKEDEX_CATEGORY_OVERRIDES = {
    "SPECIES_WARDMANE": "Mane Guard Pokémon",
    "SPECIES_TERRAPTOR": "Sky Raptor Pokémon",
    "SPECIES_TRILLKIT": "Melody Cat Pokémon",
    "SPECIES_SERMEDIC": "Guide Spirit Pokémon",
    "SPECIES_ROOKIT": "Roving Rook Pokémon",
    "SPECIES_VROOMBREL": "Speed Shadow Pokémon",
    "SPECIES_SAUTENE": "Dance Flame Pokémon",
    "SPECIES_VELOURA": "Light Dancer Pokémon",
    "SPECIES_AEGICARE": "Shield Guard Pokémon",
    "SPECIES_NESTELLE": "Hearth Bloom Pokémon",
    "SPECIES_TIDELION": "River Guard Pokémon",
    "SPECIES_AUROROTH": "Aurora Ward Pokémon",
    "SPECIES_SHIVERSKEW": "Frost Wraith Pokémon",
    "SPECIES_NIVISPECT": "Ice Specter Pokémon",
    "SPECIES_HEARTHALO": "Holy Hearth Pokémon",
    "SPECIES_WYRMOLT": "Molt Wyrm Pokémon",
    "SPECIES_DRAKOCOON": "Ancient Wing Pokémon",
    "SPECIES_SHARDSHADE": "Whisper Rock Pokémon",
    "SPECIES_CAIRNRAITH": "Cairn Wraith Pokémon",
    "SPECIES_GRAVEMOURN": "Old Sentinel Pokémon",
    "SPECIES_SPRIGLET": "Meadow Den Pokémon",
    "SPECIES_LOAMBELLE": "Garden Ward Pokémon",
    "SPECIES_MEADOWMIRA": "Earth Boon Pokémon",
    "SPECIES_TINHAM": "Clock Pup Pokémon",
    "SPECIES_FERRALUME": "Living Gear Pokémon",
    "SPECIES_CAIRNCROWN": "Summit Ward Pokémon",
}
REQUIRED_FILES = (
    "data.json",
    "sprite_data.json",
    "meson.build",
    "male_front.png",
    "female_front.png",
    "male_back.png",
    "female_back.png",
    "male_front.png.key",
    "female_front.png.key",
    "male_back.png.key",
    "female_back.png.key",
    "normal.pal",
    "shiny.pal",
    "icon.png",
    "footprint.png",
    "cry.txt",
    "cry.wav",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=REPO_ROOT)
    parser.add_argument(
        "--manifest",
        type=Path,
        help="normalized species manifest (defaults inside --repo)",
    )
    parser.add_argument(
        "--pack",
        type=Path,
        default=DEFAULT_PACK,
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("/tmp/beacondex-species-generator/staging"),
    )
    parser.add_argument(
        "--report",
        type=Path,
        help="generation report (defaults next to --output)",
    )
    parser.add_argument("--clean", action="store_true", help="remove output before generation")
    return parser.parse_args()


def normalized_name(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    ascii_value = "".join(c for c in decomposed if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", ascii_value.lower())


def code_stem(row: dict) -> str:
    return row["code_name"].removeprefix("SPECIES_").lower()


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_game_text(text: str) -> str:
    """Replace unsupported ASCII punctuation with Platinum charmap glyphs."""
    return text.replace("'", "’")


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=4, ensure_ascii=False) + "\n", encoding="utf-8")


def parse_jasc_palette(path: Path) -> list[tuple[int, int, int]]:
    lines = path.read_text(encoding="ascii").replace("\r", "").splitlines()
    if len(lines) < 4 or lines[0] != "JASC-PAL" or lines[1] != "0100":
        raise ValueError(f"invalid JASC palette: {path}")
    count = int(lines[2])
    colors = [tuple(map(int, line.split())) for line in lines[3 : 3 + count]]
    if len(colors) != count or any(len(color) != 3 for color in colors):
        raise ValueError(f"truncated JASC palette: {path}")
    return colors


def write_jasc_palette(path: Path, colors: Sequence[tuple[int, int, int]]) -> None:
    if len(colors) != 16:
        raise ValueError(f"battle palette must have 16 colors, got {len(colors)}")
    body = ["JASC-PAL", "0100", "16"]
    body.extend(f"{r} {g} {b}" for r, g, b in colors)
    path.write_bytes(("\r\n".join(body) + "\r\n").encode("ascii"))


def rgb_distance(left: tuple[int, int, int], right: tuple[int, int, int]) -> int:
    # Mildly perceptual integer weighting; exact weights do not affect topology.
    return (
        30 * (left[0] - right[0]) ** 2
        + 59 * (left[1] - right[1]) ** 2
        + 11 * (left[2] - right[2]) ** 2
    )


def nearest_palette_index(
    rgb: tuple[int, int, int], colors: Sequence[tuple[int, int, int]], *, start: int = 1
) -> int:
    if start >= len(colors):
        raise ValueError("palette has no drawable colors")
    return min(range(start, len(colors)), key=lambda i: rgb_distance(rgb, colors[i]))


def load_rgba(path: Path) -> Image.Image:
    image = Image.open(path).convert("RGBA")
    if image.size != (64, 64):
        raise ValueError(f"expected 64x64 source sprite: {path} ({image.size})")
    return image


def color_pair_distance(left: Sequence[int], right: Sequence[int]) -> int:
    return rgb_distance(tuple(left[:3]), tuple(right[:3])) + rgb_distance(
        tuple(left[3:]), tuple(right[3:])
    )


def paired_samples(
    normal_images: Sequence[Image.Image],
    shiny_images: Sequence[Image.Image],
) -> Counter[tuple[int, int, int, int, int, int]]:
    samples: Counter[tuple[int, int, int, int, int, int]] = Counter()
    for normal, shiny in zip(normal_images, shiny_images, strict=True):
        for normal_pixel, shiny_pixel in zip(
            normal.get_flattened_data(), shiny.get_flattened_data(), strict=True
        ):
            nr, ng, nb, na = normal_pixel
            sr, sg, sb, sa = shiny_pixel
            if na < OPAQUE_ALPHA:
                continue
            # Geometry changes cannot be represented by a palette swap.  Keep
            # the normal color as a stable fallback where the shiny draft is
            # transparent at an otherwise-opaque pixel.
            if sa < OPAQUE_ALPHA:
                sr, sg, sb = nr, ng, nb
            samples[(nr, ng, nb, sr, sg, sb)] += 1
    return samples


def derive_paired_palettes(
    normal_images: Sequence[Image.Image],
    shiny_images: Sequence[Image.Image],
    count: int = 15,
) -> tuple[list[tuple[int, int, int]], list[tuple[int, int, int]]]:
    weighted = paired_samples(normal_images, shiny_images)
    points = sorted(weighted)
    if not points:
        raise ValueError("sprite has no opaque pixels")

    # Deterministic weighted farthest-first initialization followed by Lloyd
    # refinement in six-dimensional (normal RGB + shiny RGB) color space.
    centers: list[tuple[int, ...]] = [max(points, key=lambda point: (weighted[point], point))]
    while len(centers) < min(count, len(points)):
        centers.append(
            max(
                (point for point in points if point not in centers),
                key=lambda point: (
                    min(color_pair_distance(point, center) for center in centers)
                    * max(1, weighted[point]),
                    point,
                ),
            )
        )

    for _ in range(30):
        groups: list[list[tuple[tuple[int, ...], int]]] = [[] for _ in centers]
        for point in points:
            index = min(
                range(len(centers)),
                key=lambda i: (color_pair_distance(point, centers[i]), i),
            )
            groups[index].append((point, weighted[point]))
        updated: list[tuple[int, ...]] = []
        for index, group in enumerate(groups):
            if not group:
                updated.append(centers[index])
                continue
            total = sum(weight for _, weight in group)
            updated.append(
                tuple(
                    round(sum(point[channel] * weight for point, weight in group) / total)
                    for channel in range(6)
                )
            )
        if updated == centers:
            break
        centers = updated

    while len(centers) < count:
        centers.append(centers[-1])
    background = (248, 248, 248)
    normal_palette = [background, *(tuple(center[:3]) for center in centers[:count])]
    shiny_palette = [background, *(tuple(center[3:]) for center in centers[:count])]
    return normal_palette, shiny_palette


def nearest_palette_pair_index(
    normal_rgb: tuple[int, int, int],
    shiny_rgb: tuple[int, int, int],
    normal_palette: Sequence[tuple[int, int, int]],
    shiny_palette: Sequence[tuple[int, int, int]],
    *,
    preserve_normal: bool = False,
) -> int:
    if preserve_normal:
        normal_distances = [
            rgb_distance(normal_rgb, normal_palette[i])
            for i in range(1, min(len(normal_palette), len(shiny_palette)))
        ]
        minimum = min(normal_distances)
        candidates = [i + 1 for i, distance in enumerate(normal_distances) if distance == minimum]
        return min(candidates, key=lambda i: (rgb_distance(shiny_rgb, shiny_palette[i]), i))
    pair = (*normal_rgb, *shiny_rgb)
    return min(
        range(1, min(len(normal_palette), len(shiny_palette))),
        key=lambda i: color_pair_distance(pair, (*normal_palette[i], *shiny_palette[i])),
    )


def png_palette(colors: Sequence[tuple[int, int, int]]) -> list[int]:
    values: list[int] = []
    for color in colors[:16]:
        values.extend(color)
    values.extend([0] * (768 - len(values)))
    return values


def indexed_sprite_sheet(
    normal: Image.Image,
    shiny: Image.Image,
    normal_palette: Sequence[tuple[int, int, int]],
    shiny_palette: Sequence[tuple[int, int, int]],
    *,
    preserve_normal: bool = False,
) -> tuple[Image.Image, float, float, int]:
    sheet = Image.new("P", SHEET_SIZE, color=0)
    sheet.putpalette(png_palette(normal_palette))
    indexed = Image.new("P", normal.size, color=0)
    indexed.putpalette(png_palette(normal_palette))
    normal_error = 0
    shiny_error = 0
    normal_count = 0
    shiny_count = 0
    alpha_mismatch = 0
    for y in range(normal.height):
        for x in range(normal.width):
            nr, ng, nb, na = normal.getpixel((x, y))
            sr, sg, sb, sa = shiny.getpixel((x, y))
            if (na >= OPAQUE_ALPHA) != (sa >= OPAQUE_ALPHA):
                alpha_mismatch += 1
            if na < OPAQUE_ALPHA:
                continue
            shiny_rgb = (sr, sg, sb) if sa >= OPAQUE_ALPHA else (nr, ng, nb)
            index = nearest_palette_pair_index(
                (nr, ng, nb),
                shiny_rgb,
                normal_palette,
                shiny_palette,
                preserve_normal=preserve_normal,
            )
            indexed.putpixel((x, y), index)
            normal_error += rgb_distance((nr, ng, nb), normal_palette[index])
            normal_count += 1
            if sa >= OPAQUE_ALPHA:
                shiny_error += rgb_distance((sr, sg, sb), shiny_palette[index])
                shiny_count += 1
    x, y = FRAME_ORIGIN
    sheet.paste(indexed, (x, y))
    sheet.paste(indexed, (x + 80, y))
    return (
        sheet,
        math.sqrt(normal_error / max(1, normal_count) / 100.0),
        math.sqrt(shiny_error / max(1, shiny_count) / 100.0),
        alpha_mismatch,
    )


def save_indexed_png(image: Image.Image, path: Path) -> None:
    if image.mode != "P":
        raise ValueError("indexed PNG writer requires P mode")
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="PNG", bits=4, optimize=False)


def remap_supplied_icon(
    source: Path,
    shared_palette: Sequence[tuple[int, int, int]],
    palette_index: int,
    destination: Path,
) -> None:
    image = Image.open(source)
    if image.mode != "P" or image.size != ICON_SIZE:
        raise ValueError(f"unexpected supplied icon format: {source} ({image.mode}, {image.size})")
    if max(int(pixel) for pixel in image.get_flattened_data()) > 15:
        raise ValueError(f"supplied icon uses more than 4 bits: {source}")

    begin = palette_index * 16
    colors = list(shared_palette[begin : begin + 16])
    if len(colors) != 16:
        raise ValueError(f"invalid icon palette index {palette_index}")
    source_palette = image.getpalette() or []
    if len(source_palette) < 48:
        raise ValueError(f"supplied icon has an incomplete palette: {source}")

    remapped = Image.new("P", ICON_SIZE, color=0)
    remapped.putpalette(png_palette(colors))
    for y in range(image.height):
        for x in range(image.width):
            source_index = int(image.getpixel((x, y)))
            if source_index == 0:
                continue
            offset = source_index * 3
            source_rgb = tuple(source_palette[offset : offset + 3])
            remapped.putpixel((x, y), nearest_palette_index(source_rgb, colors))
    save_indexed_png(remapped, destination)


def generate_icon(
    source: Image.Image,
    shared_palette: Sequence[tuple[int, int, int]],
    palette_index: int,
    destination: Path,
) -> None:
    begin = palette_index * 16
    colors = list(shared_palette[begin : begin + 16])
    if len(colors) != 16:
        raise ValueError(f"invalid icon palette index {palette_index}")

    alpha = source.getchannel("A").resize((28, 28), Image.Resampling.NEAREST)
    rgb = source.convert("RGB").resize((28, 28), Image.Resampling.NEAREST)
    frame = Image.new("P", (32, 32), color=0)
    frame.putpalette(png_palette(colors))
    for y in range(28):
        for x in range(28):
            if alpha.getpixel((x, y)) < OPAQUE_ALPHA:
                continue
            frame.putpixel((x + 2, y + 2), nearest_palette_index(rgb.getpixel((x, y)), colors))

    icon = Image.new("P", ICON_SIZE, color=0)
    icon.putpalette(png_palette(colors))
    icon.paste(frame, (0, 0))
    icon.paste(frame, (0, 32))
    save_indexed_png(icon, destination)


def preserve_supplied_footprint(source: Path, destination: Path) -> None:
    footprint = Image.open(source)
    if footprint.mode != "P" or footprint.size != (16, 16):
        raise ValueError(
            f"unexpected supplied footprint format: {source} ({footprint.mode}, {footprint.size})"
        )
    if max(int(pixel) for pixel in footprint.get_flattened_data()) > 15:
        raise ValueError(f"supplied footprint uses more than 4 bits: {source}")
    # pokefoot stores the visible 16x16 mark in the left tile. Stock assets use
    # index 4 for the mark and fill the unused right tile with index 12.
    out = Image.new("P", FOOTPRINT_SIZE, color=12)
    out.putpalette(png_palette([(0, 0, 0)] * 16))
    for y in range(16):
        for x in range(16):
            source_index = int(footprint.getpixel((x, y)))
            out.putpixel((x, y), 0 if source_index == 0 else 4)
    save_indexed_png(out, destination)


def generate_footprint(source: Image.Image, destination: Path) -> None:
    alpha = source.getchannel("A")
    bbox = alpha.point(lambda value: 255 if value >= OPAQUE_ALPHA else 0).getbbox()
    if bbox is None:
        raise ValueError("cannot derive footprint from transparent sprite")
    silhouette = alpha.crop(bbox)
    silhouette.thumbnail((14, 14), Image.Resampling.NEAREST)
    out = Image.new("P", FOOTPRINT_SIZE, color=12)
    out.putpalette(png_palette([(0, 0, 0)] * 16))
    for y in range(16):
        for x in range(16):
            out.putpixel((x, y), 0)
    x_offset = (16 - silhouette.width) // 2
    y_offset = (16 - silhouette.height) // 2
    for y in range(silhouette.height):
        for x in range(silhouette.width):
            if silhouette.getpixel((x, y)) >= OPAQUE_ALPHA:
                out.putpixel((x + x_offset, y + y_offset), 4)
    save_indexed_png(out, destination)


def wrap_entry(text: str) -> tuple[list[str], str]:
    # The stock UI uses three lines and vanilla source never exceeds 38 chars.
    # The handoff prose often has two long sentences; retain its first complete
    # sentence rather than silently overflowing the fixed Pokédex entry window.
    text = normalize_game_text(text)
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    chosen = sentences[0]
    lines = textwrap.wrap(chosen, width=38, break_long_words=False, break_on_hyphens=False)
    if len(lines) > 3:
        raise ValueError(f"entry's first sentence still exceeds three lines: {text}")
    lines.extend([""] * (3 - len(lines)))
    encoded = [line + ("\n" if i < 2 else "") for i, line in enumerate(lines)]
    return encoded, chosen


def build_data_json(row: dict, template: dict) -> tuple[dict, str]:
    defaults = row["documented_defaults"]
    data = copy.deepcopy(template)
    data["base_stats"] = copy.deepcopy(row["base_stats"])
    types = list(row["types"])
    if len(types) == 1:
        types.append(types[0])
    data["types"] = types
    data["catch_rate"] = defaults["catch_rate"]
    data["base_exp_reward"] = defaults["base_exp_reward"]
    data["ev_yields"] = copy.deepcopy(defaults["ev_yields"])
    data["held_items"] = copy.deepcopy(defaults["held_items"])
    data["gender_ratio"] = defaults["gender_ratio"]
    data["hatch_cycles"] = defaults["hatch_cycles"]
    data["base_friendship"] = defaults["base_friendship"]
    data["exp_rate"] = defaults["exp_rate"]
    data["egg_groups"] = list(defaults["egg_groups"])
    data["abilities"] = list(row["abilities"]["runtime_slots"])
    data["safari_flee_rate"] = defaults["safari_flee_rate"]
    data["body_color"] = defaults["body_color"]
    data["flip_sprite"] = defaults["flip_sprite"]
    data["icon_palette"] = defaults["temporary_icon_palette"]
    data["learnset"] = {
        "by_level": copy.deepcopy(row["learnset"]["by_level"]),
        "by_tm": list(row["machines"]["by_tm_hm"]),
        "by_tutor": [],
        "egg_moves": [],
    }
    data["evolutions"] = [list(row["evolution"])] if row["evolution"] else []
    data["offspring"] = defaults["offspring"]
    data["footprint"] = copy.deepcopy(defaults["footprint_classification"])

    entry_lines, retained_entry = wrap_entry(row["pokedex"]["entry_en"])
    locale = {
        "name": row["display_name"].upper(),
        "category": POKEDEX_CATEGORY_OVERRIDES.get(
            row["code_name"], normalize_game_text(row["pokedex"]["category_en"])
        ),
        "entry_text": entry_lines,
    }
    scaling = copy.deepcopy(defaults["pokedex_display_scaling"])
    data["pokedex_data"] = {
        "height_inches": defaults["height_inches"],
        "weight_pounds": defaults["weight_pounds"],
        "body_shape": defaults["body_shape"],
        **scaling,
        **{language: copy.deepcopy(locale) for language in LOCALES},
    }
    data["catching_show"] = copy.deepcopy(defaults["catching_show"])
    return data, retained_entry


def species_meson() -> str:
    return """species_data_files += files('data.json', 'sprite_data.json')

poke_icon_files += files('icon.png')

pokegra_files += files('female_back.png')
pokegra_files += files('male_back.png')
pokegra_files += files('female_front.png')
pokegra_files += files('male_front.png')

pokefoot_files += files('footprint.png')
"""


def build_asset_lookup(root: Path) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for path in root.iterdir():
        if path.is_dir():
            key = normalized_name(path.name)
            if key in result:
                raise ValueError(f"ambiguous normalized asset directory: {path} and {result[key]}")
            result[key] = path
    return result


def validate_generated_tree(output: Path, rows: Sequence[dict]) -> dict:
    errors: list[str] = []
    species_root = output / "res/pokemon"
    for row in rows:
        stem = code_stem(row)
        directory = species_root / stem
        missing = [name for name in REQUIRED_FILES if not (directory / name).is_file()]
        if missing:
            errors.append(f"{stem}: missing {missing}")
            continue
        data = load_json(directory / "data.json")
        if len(data["types"]) != 2 or len(data["abilities"]) != 2:
            errors.append(f"{stem}: types/abilities must each contain exactly two entries")
        if len(data["learnset"]["by_level"]) > 20:
            errors.append(f"{stem}: level-up learnset exceeds 20 entries")
        for locale in LOCALES:
            locale_data = data["pokedex_data"].get(locale, {})
            if len(locale_data.get("entry_text", [])) != 3:
                errors.append(f"{stem}: locale {locale} does not have three entry lines")
            if any(len(line.removesuffix("\n")) > 38 for line in locale_data.get("entry_text", [])):
                errors.append(f"{stem}: locale {locale} exceeds stock entry width")
        for name, size in (
            ("male_front.png", SHEET_SIZE),
            ("female_front.png", SHEET_SIZE),
            ("male_back.png", SHEET_SIZE),
            ("female_back.png", SHEET_SIZE),
            ("icon.png", ICON_SIZE),
            ("footprint.png", FOOTPRINT_SIZE),
        ):
            image = Image.open(directory / name)
            if image.mode != "P" or image.size != size:
                errors.append(f"{stem}/{name}: expected indexed {size}, got {image.mode} {image.size}")
            elif max(int(pixel) for pixel in image.get_flattened_data()) > 15:
                errors.append(f"{stem}/{name}: pixel index exceeds four bits")
        for palette_name in ("normal.pal", "shiny.pal"):
            if len(parse_jasc_palette(directory / palette_name)) != 16:
                errors.append(f"{stem}/{palette_name}: expected 16 colors")

    species_lines = (output / "generated/species.txt").read_text().splitlines()
    constants = [row["code_name"] for row in rows]
    try:
        start = species_lines.index(constants[0])
        egg = species_lines.index("SPECIES_EGG")
    except ValueError as exc:
        errors.append(f"species registry missing required constant: {exc}")
    else:
        if species_lines[start : start + len(constants)] != constants:
            errors.append("BeaconDex constants are not contiguous/in manifest order")
        if start != EXPECTED_FIRST_ID or start + len(constants) - 1 != EXPECTED_LAST_ID:
            errors.append(f"unexpected species allocation {start}-{start + len(constants) - 1}")
        if egg != EXPECTED_LAST_ID + 1:
            errors.append(f"EGG sentinel expected at {EXPECTED_LAST_ID + 1}, got {egg}")

    sinnoh = load_json(output / "res/pokemon/sinnoh_pokedex.json")
    if len(sinnoh) != 274 or sinnoh[-len(constants) :] != constants:
        errors.append("Sinnoh registry should contain dummy + 273 species in expected order")
    return {"passed": not errors, "errors": errors}


def main() -> None:
    args = parse_args()
    repo = args.repo.resolve()
    manifest_path = (args.manifest or repo / "data/beacondex/species_normalized.json").resolve()
    pack = args.pack.resolve()
    output = args.output.resolve()
    report_path = (args.report or output.parent / "report.json").resolve()

    if args.clean and output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)

    manifest = load_json(manifest_path)
    rows = manifest["species"]
    if len(rows) != EXPECTED_SPECIES:
        raise SystemExit(f"expected {EXPECTED_SPECIES} species, found {len(rows)}")
    if [row["proposed_national_dex"] for row in rows] != list(
        range(EXPECTED_FIRST_ID, EXPECTED_LAST_ID + 1)
    ):
        raise SystemExit("manifest species allocation is not 494-556 in order")

    sprite_dirs = build_asset_lookup(pack / "sprites")
    supplied_dirs = build_asset_lookup(pack / "source_palettes_27")
    shared_icon_palette = parse_jasc_palette(repo / "res/pokemon/.shared/pl_poke_icon.pal")
    if len(shared_icon_palette) < 48:
        raise SystemExit("shared icon palette does not expose three 16-color subpalettes")

    report: dict = {
        "schema": "beacondex-species-source-generation-v1",
        "species": [],
        "policies": {
            "battle_sprites": "two identical 80x80 frames from supplied 64x64 draft; 15 opaque colors plus transparent index 0",
            "shiny": "normal and shiny pixel pairs share one index topology; supplied palettes are preserved for the original 27 and paired six-channel quantization derives the newer 36",
            "new_icons": "28x28 nearest-neighbor preview mapped to the documented template icon subpalette",
            "new_footprints": "binary 16x14 silhouette centered in the left 16x16 tile; unused right tile filled with palette index 12",
            "cries": "documented vanilla template cry copied until authored cries exist",
            "locales": "English technical fallback copied into all six required banks",
            "pokedex_entry": "first complete author-draft sentence retained and wrapped to the stock three-line, 38-character layout",
        },
    }

    species_root = output / "res/pokemon"
    species_root.mkdir(parents=True, exist_ok=True)
    for row in rows:
        stem = code_stem(row)
        key = normalized_name(row["display_name"])
        if key not in sprite_dirs:
            raise SystemExit(f"missing sprite directory for {row['display_name']}")
        sprite_source = sprite_dirs[key]
        supplied_source = supplied_dirs.get(key)
        destination = species_root / stem
        destination.mkdir(parents=True, exist_ok=True)

        template_constant = row["documented_defaults"]["template_species"]
        template_stem = template_constant.removeprefix("SPECIES_").lower()
        template_dir = repo / "res/pokemon" / template_stem
        template_data = load_json(template_dir / "data.json")
        data, retained_entry = build_data_json(row, template_data)
        write_json(destination / "data.json", data)
        sprite_data_text = (template_dir / "sprite_data.json").read_text(encoding="utf-8")
        (destination / "sprite_data.json").write_text(
            sprite_data_text.rstrip("\n") + "\n",
            encoding="utf-8",
        )
        shutil.copy2(template_dir / "cry.txt", destination / "cry.txt")
        shutil.copy2(template_dir / "cry.wav", destination / "cry.wav")
        (destination / "meson.build").write_text(species_meson(), encoding="utf-8")

        normal_front = load_rgba(sprite_source / "normal_front.png")
        normal_back = load_rgba(sprite_source / "normal_back.png")
        shiny_front = load_rgba(sprite_source / "shiny_front.png")
        shiny_back = load_rgba(sprite_source / "shiny_back.png")
        normal_images = (normal_front, normal_back)
        shiny_images = (shiny_front, shiny_back)

        if supplied_source:
            normal_palette = parse_jasc_palette(supplied_source / "normal.pal")
            shiny_palette = parse_jasc_palette(supplied_source / "shiny.pal")
            if len(normal_palette) != 16 or len(shiny_palette) != 16:
                raise SystemExit(f"supplied palette for {stem} is not 16 colors")
            palette_source = "supplied original-27 JASC palettes"
        else:
            normal_palette, shiny_palette = derive_paired_palettes(
                normal_images, shiny_images, count=15
            )
            palette_source = "derived paired normal/shiny palette"

        front_sheet, front_error, shiny_front_error, front_alpha_mismatch = indexed_sprite_sheet(
            normal_front,
            shiny_front,
            normal_palette,
            shiny_palette,
            preserve_normal=supplied_source is not None,
        )
        back_sheet, back_error, shiny_back_error, back_alpha_mismatch = indexed_sprite_sheet(
            normal_back,
            shiny_back,
            normal_palette,
            shiny_palette,
            preserve_normal=supplied_source is not None,
        )
        for gender in ("male", "female"):
            save_indexed_png(front_sheet, destination / f"{gender}_front.png")
            save_indexed_png(back_sheet, destination / f"{gender}_back.png")
            # The four-byte key stores the final state of Platinum's reversible
            # sprite obfuscation LCG.  It depends on the encoded byte length,
            # which is identical for every 160x80 sheet, so a valid template
            # key is safe to reuse and round-trips through nitrogfx.
            for face in ("front", "back"):
                candidates = (
                    template_dir / f"{gender}_{face}.png.key",
                    template_dir / f"male_{face}.png.key",
                    repo / "res/pokemon/riolu" / f"male_{face}.png.key",
                )
                key_source = next((path for path in candidates if path.is_file()), None)
                if key_source is None:
                    raise SystemExit(f"no valid sprite key template for {stem}/{gender}_{face}")
                shutil.copy2(key_source, destination / f"{gender}_{face}.png.key")
        write_jasc_palette(destination / "normal.pal", normal_palette)
        write_jasc_palette(destination / "shiny.pal", shiny_palette)

        if supplied_source:
            remap_supplied_icon(
                supplied_source / "icon.png",
                shared_icon_palette,
                int(row["documented_defaults"]["temporary_icon_palette"]),
                destination / "icon.png",
            )
            preserve_supplied_footprint(
                supplied_source / "footprint.png", destination / "footprint.png"
            )
            icon_policy = "supplied original-27 art remapped to template shared palette"
            footprint_policy = (
                "supplied 16x16 art normalized into the left tile; "
                "unused right tile filled with palette index 12"
            )
        else:
            generate_icon(
                normal_front,
                shared_icon_palette,
                int(row["documented_defaults"]["temporary_icon_palette"]),
                destination / "icon.png",
            )
            generate_footprint(normal_front, destination / "footprint.png")
            icon_policy = "generated preview mapped to template shared palette"
            footprint_policy = "generated silhouette placeholder"

        report["species"].append(
            {
                "id": row["proposed_national_dex"],
                "constant": row["code_name"],
                "directory": stem,
                "template": template_constant,
                "palette_source": palette_source,
                "normal_palette_rms_error": {
                    "front": round(front_error, 3),
                    "back": round(back_error, 3),
                },
                "shiny_palette_rms_error": {
                    "front": round(shiny_front_error, 3),
                    "back": round(shiny_back_error, 3),
                },
                "normal_shiny_alpha_mismatch_pixels": {
                    "front": front_alpha_mismatch,
                    "back": back_alpha_mismatch,
                },
                "icon": icon_policy,
                "footprint": footprint_policy,
                "pokedex_entry_source": row["pokedex"]["entry_en"],
                "pokedex_entry_retained": retained_entry,
            }
        )

    constants = [row["code_name"] for row in rows]
    original_species = [
        species
        for species in (repo / "generated/species.txt").read_text(encoding="utf-8").splitlines()
        if species not in constants
    ]
    insert_at = original_species.index("SPECIES_EGG")
    expanded_species = original_species[:insert_at] + constants + original_species[insert_at:]
    species_output = output / "generated/species.txt"
    species_output.parent.mkdir(parents=True, exist_ok=True)
    species_output.write_text("\n".join(expanded_species) + "\n", encoding="utf-8")

    original_sinnoh = [
        species
        for species in load_json(repo / "res/pokemon/sinnoh_pokedex.json")
        if species not in constants
    ]
    write_json(output / "res/pokemon/sinnoh_pokedex.json", original_sinnoh + constants)

    report["counts"] = {
        "species": len(rows),
        "families": len({row["family_index"] for row in rows}),
        "supplied_icons": sum(1 for row in rows if normalized_name(row["display_name"]) in supplied_dirs),
        "generated_icons": sum(1 for row in rows if normalized_name(row["display_name"]) not in supplied_dirs),
        "supplied_footprints": sum(1 for row in rows if normalized_name(row["display_name"]) in supplied_dirs),
        "generated_footprints": sum(1 for row in rows if normalized_name(row["display_name"]) not in supplied_dirs),
    }
    report["validation"] = validate_generated_tree(output, rows)
    write_json(report_path, report)
    print(report_path)
    print(json.dumps(report["counts"], sort_keys=True))
    print(json.dumps(report["validation"], sort_keys=True))
    if not report["validation"]["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
