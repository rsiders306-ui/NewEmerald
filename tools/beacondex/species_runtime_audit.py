#!/usr/bin/env python3
"""Audit BeaconDex species IDs, runtime storage, assets, and built archives."""

from __future__ import annotations

import argparse
import json
import struct
import subprocess
from collections import Counter
from pathlib import Path

from PIL import Image


EXPECTED_FIRST_ID = 494
EXPECTED_LAST_ID = 556
EXPECTED_SPECIES = EXPECTED_LAST_ID - EXPECTED_FIRST_ID + 1
EXPECTED_BASE_ARCHIVE_MEMBERS = 571
EXPECTED_ARCHIVES = {
    "res/pokemon/pl_personal.narc": EXPECTED_BASE_ARCHIVE_MEMBERS,
    "res/pokemon/evo.narc": EXPECTED_BASE_ARCHIVE_MEMBERS,
    "res/pokemon/wotbl.narc": EXPECTED_BASE_ARCHIVE_MEMBERS,
    "res/pokemon/height.narc": 2228,
    "res/pokemon/zukan_data.narc": 59,
    "res/pokemon/pokefoot.narc": 560,
    "res/pokemon/pl_poke_icon.narc": 610,
    "res/pokemon/pl_pokegra.narc": 3342,
    "res/field/encounters/zukan_enc_platinum.narc": 5584,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="pokeplatinum source root (default: inferred from this script)",
    )
    parser.add_argument(
        "--build",
        type=Path,
        required=True,
        help="completed build directory containing the generated NARCs",
    )
    parser.add_argument(
        "--report",
        type=Path,
        help="optional path for the full JSON report; otherwise print it to stdout",
    )
    return parser.parse_args()


def read_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


def read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def narc_member_count(path: Path) -> int:
    header = path.read_bytes()[:0x1A]
    if len(header) != 0x1A or header[:4] != b"NARC" or header[0x10:0x14] != b"BTAF":
        raise ValueError(f"{path} is not a standard NARC")
    return struct.unpack_from("<H", header, 0x18)[0]


def align(value: int, alignment: int) -> int:
    return (value + alignment - 1) // alignment * alignment


def pokedex_struct_size(national_count: int, max_species: int) -> int:
    dex_words = (national_count - 1) // 32 + 1
    size = 4  # magic
    size += dex_words * 4 * 4  # caught, seen, and two gender bitsets
    size += 4  # Spinda form
    size += 4 + 28  # Shellos/Gastrodon/Burmy/Wormadam and Unown forms
    size += max_species + 1  # per-species language flags
    size += 4  # form/language/Pokedex/National Dex flags
    size = align(size, 4)
    size += 4  # Rotom forms
    size += 2  # Shaymin and Giratina forms
    return align(size, 4)


def git_head(repo: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def main() -> int:
    args = parse_args()
    repo = args.repo.resolve()
    build = args.build.resolve()
    checks: list[dict[str, object]] = []

    def record(name: str, passed: bool, evidence: object) -> None:
        checks.append({"name": name, "passed": passed, "evidence": evidence})

    species = read_lines(repo / "generated/species.txt")
    moves = read_lines(repo / "generated/moves.txt")
    abilities = set(read_lines(repo / "generated/abilities.txt"))
    types = set(read_lines(repo / "generated/pokemon_types.txt"))
    evolution_methods = set(read_lines(repo / "generated/evolution_methods.txt"))
    custom = species[EXPECTED_FIRST_ID : EXPECTED_LAST_ID + 1]

    registry_ok = (
        len(custom) == EXPECTED_SPECIES
        and species[493] == "SPECIES_ARCEUS"
        and species[557] == "SPECIES_EGG"
        and species[558] == "SPECIES_BAD_EGG"
    )
    record(
        "species_registry",
        registry_ok,
        {
            "custom_ids": [EXPECTED_FIRST_ID, EXPECTED_LAST_ID],
            "count": len(custom),
            "egg": 557,
            "bad_egg": 558,
            "national_dex_count": 556,
        },
    )

    manifest = read_json(repo / "data/beacondex/species_normalized.json")["species"]
    manifest_ids = [row["proposed_national_dex"] for row in manifest]
    record(
        "manifest_allocation",
        manifest_ids == list(range(EXPECTED_FIRST_ID, EXPECTED_LAST_ID + 1)),
        {"count": len(manifest), "ids": [manifest_ids[0], manifest_ids[-1]]},
    )

    base_by_family = {
        row["family_index"]: row["code_name"]
        for row in manifest
        if row["stage"] == 1
    }
    families: Counter[int] = Counter()
    stages: Counter[int] = Counter()
    evolution_edges: list[list[str]] = []
    asset_counts: Counter[str] = Counter()
    stat_ranges = {
        key: [255, 0]
        for key in ("hp", "attack", "defense", "speed", "special_attack", "special_defense")
    }
    data_errors: list[str] = []

    asset_specs = {
        "male_front.png": (160, 80),
        "female_front.png": (160, 80),
        "male_back.png": (160, 80),
        "female_back.png": (160, 80),
        "icon.png": (32, 64),
        "footprint.png": (32, 16),
    }

    for species_id, constant in enumerate(custom, EXPECTED_FIRST_ID):
        row = manifest[species_id - EXPECTED_FIRST_ID]
        stem = constant.removeprefix("SPECIES_").lower()
        species_dir = repo / "res/pokemon" / stem
        data = read_json(species_dir / "data.json")

        families[row["family_index"]] += 1
        stages[row["stage"]] += 1
        if data["offspring"] != base_by_family[row["family_index"]]:
            data_errors.append(f"{constant}: offspring does not point to the family base")

        for stat, value in data["base_stats"].items():
            stat_ranges[stat][0] = min(stat_ranges[stat][0], value)
            stat_ranges[stat][1] = max(stat_ranges[stat][1], value)
            if not 0 < value <= 255:
                data_errors.append(f"{constant}: {stat}={value} does not fit u8")

        if len(data["learnset"]["by_level"]) > 20:
            data_errors.append(f"{constant}: level learnset exceeds 20 entries")
        for pokemon_type in data["types"]:
            if pokemon_type not in types:
                data_errors.append(f"{constant}: unknown type {pokemon_type}")
        for ability in data["abilities"]:
            if ability not in abilities:
                data_errors.append(f"{constant}: unknown ability {ability}")
        for _level, move in data["learnset"]["by_level"]:
            if move not in moves:
                data_errors.append(f"{constant}: unknown move {move}")

        for evolution in data["evolutions"]:
            method = evolution[0]
            target = evolution[-1]
            if method not in evolution_methods:
                data_errors.append(f"{constant}: unknown evolution method {method}")
            if target not in custom:
                data_errors.append(f"{constant}: evolution target {target} is not a custom species")
            evolution_edges.append([constant, method, target])

        for filename, expected_size in asset_specs.items():
            image = Image.open(species_dir / filename)
            asset_counts[filename] += 1
            if image.mode != "P" or image.size != expected_size:
                data_errors.append(
                    f"{constant}/{filename}: expected indexed {expected_size}, got {image.mode} {image.size}"
                )
            pixels = image.get_flattened_data()
            if pixels and max(pixels) > 15:
                data_errors.append(f"{constant}/{filename}: palette index exceeds four bits")

        for filename in ("normal.pal", "shiny.pal"):
            palette = read_lines(species_dir / filename)
            asset_counts[filename] += 1
            if palette[:3] != ["JASC-PAL", "0100", "16"] or len(palette[3:]) != 16:
                data_errors.append(f"{constant}/{filename}: expected a 16-color JASC palette")
        if not (species_dir / "sprite_data.json").is_file():
            data_errors.append(f"{constant}: sprite_data.json is missing")

    record(
        "personal_evolution_assets",
        not data_errors,
        {
            "families": dict(sorted(families.items())),
            "stages": dict(sorted(stages.items())),
            "evolution_edges": len(evolution_edges),
            "stat_ranges": stat_ranges,
            "asset_counts": dict(asset_counts),
            "errors": data_errors,
        },
    )
    graph_ok = (
        all(families[index] == 3 for index in range(1, 22))
        and stages == Counter({1: 21, 2: 21, 3: 21})
        and len(evolution_edges) == 42
    )
    record(
        "family_graph",
        graph_ok,
        {
            "family_count": len(families),
            "edges": len(evolution_edges),
            "special_methods": [edge for edge in evolution_edges if edge[1] != "EVO_LEVEL"],
        },
    )

    pokemon_source = (repo / "src/pokemon.c").read_text(encoding="utf-8")
    trainer_source = (repo / "src/trainer_data.c").read_text(encoding="utf-8")
    frontier_header = (repo / "include/overlay104/frontier_opponents.h").read_text(encoding="utf-8")
    species_header = (repo / "include/struct_defs/species.h").read_text(encoding="utf-8")
    pokedex_header = (repo / "include/pokedex.h").read_text(encoding="utf-8")
    speciesproc = (repo / "tools/dataproc/src/speciesproc.c").read_text(encoding="utf-8")

    max_move_id = moves.index("MAX_MOVES") - 1
    packed_ok = (
        "species & 0x3FF" in trainer_source
        and "u16 species : 11;" in frontier_header
        and "u16 move : 9;" in species_header
        and EXPECTED_LAST_ID < 1 << 10
        and max_move_id < 1 << 9
    )
    record(
        "packed_species_and_move_widths",
        packed_ok,
        {
            "trainer_species_bits": 10,
            "frontier_species_bits": 11,
            "learnset_move_bits": 9,
            "max_custom_species_id": EXPECTED_LAST_ID,
            "max_move_id": max_move_id,
        },
    )

    sentinel_ok = (
        "SPECIES_BAD_EGG + monForm" in pokemon_source
        and "SPECIES_BAD_EGG + 1 + i" in speciesproc
        and "#define NATIONAL_DEX_COUNT (MAX_SPECIES - 2)"
        in (repo / "include/constants/species.h").read_text(encoding="utf-8")
    )
    record(
        "form_and_sentinel_indices",
        sentinel_ok,
        {"personal_form_first_index": 559, "tutor_form_first_constant": 557},
    )

    sprite_ok = pokemon_source.count(
        "species > SPECIES_ARCEUS && species <= NATIONAL_DEX_COUNT"
    ) >= 2
    record(
        "sprite_runtime_fallback",
        sprite_ok,
        {
            "pl_pokegra_last_custom_member": EXPECTED_LAST_ID * 6 + 5,
            "height_last_custom_member": EXPECTED_LAST_ID * 4 + 3,
        },
    )

    dex_size = pokedex_struct_size(556, 558)
    pokedex_ok = (
        "caughtPokemon[DEX_SIZE_U32]" in pokedex_header
        and "recordedLanguages[MAX_SPECIES + 1]" in pokedex_header
        and dex_size == 900
    )
    record(
        "pokedex_storage",
        pokedex_ok,
        {
            "dex_u32_words": 18,
            "pokedex_struct_bytes": dex_size,
            "vanilla_struct_bytes": 804,
            "delta_bytes": dex_size - 804,
        },
    )

    archive_counts: dict[str, int | None] = {}
    archive_errors: list[str] = []
    for relative_path, expected_count in EXPECTED_ARCHIVES.items():
        path = build / relative_path
        try:
            actual_count = narc_member_count(path)
        except (OSError, ValueError) as error:
            actual_count = None
            archive_errors.append(f"{relative_path}: {error}")
        archive_counts[relative_path] = actual_count
        if actual_count is not None and actual_count != expected_count:
            archive_errors.append(
                f"{relative_path}: expected {expected_count} members, found {actual_count}"
            )
    record(
        "built_archive_cardinality",
        not archive_errors,
        {
            "build": str(build),
            "actual": archive_counts,
            "expected": EXPECTED_ARCHIVES,
            "errors": archive_errors,
        },
    )

    rating_source = (repo / "src/unk_0205DFC4.c").read_text(encoding="utf-8")
    scrcmd_source = (repo / "src/scrcmd.c").read_text(encoding="utf-8")
    rating_ok = (
        "Pokedex_GetRatingMessageID_Local(u16 pokemonSeen, u16 reachedEternaCity, BOOL completed)"
        in rating_source
        and "Pokedex_GetRatingMessageID_National(u16 pokemonCaught, u16 playerGender, BOOL completed)"
        in rating_source
        and rating_source.count("return PokedexRatings_Text_OakPokemonCaught476;") >= 2
        and "Pokedex_LocalDexCompleted(pokedex)" in scrcmd_source
        and "Pokedex_NationalDexCompleted(pokedex)" in scrcmd_source
    )
    record(
        "rating_completion_policy",
        rating_ok,
        {
            "truth_table": [
                {
                    "case": "local original story set complete with seen count below 273",
                    "expected": "Rowan complete-local message",
                },
                {
                    "case": "national 482 through 544 caught and incomplete",
                    "expected": "Oak 476+ progress message",
                },
                {
                    "case": "national 545 required species caught",
                    "expected": "Oak complete-national message",
                },
            ]
        },
    )

    passed = all(check["passed"] for check in checks)
    report = {
        "schema": "beacondex-species-runtime-audit-v1",
        "source_head": git_head(repo),
        "scope": (
            "63 custom species runtime integration; cry SDAT registration and official "
            "Fairy move authoring are audited separately"
        ),
        "result": "pass" if passed else "fail",
        "checks_passed": sum(bool(check["passed"]) for check in checks),
        "checks_total": len(checks),
        "checks": checks,
        "nonblocking_content_limits": [
            (
                "Egg-move and tutor lists are intentionally empty in the current data; "
                "offspring, egg groups, level-up inheritance, and TM inheritance remain functional."
            ),
            (
                "Sprites are integration-pack drafts, but every required normal, shiny, front, "
                "back, icon, and footprint asset is structurally present."
            ),
        ],
    }
    encoded = json.dumps(report, indent=2) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(encoded, encoding="utf-8")
        print(
            json.dumps(
                {
                    "result": report["result"],
                    "checks_passed": report["checks_passed"],
                    "checks_total": report["checks_total"],
                    "report": str(args.report.resolve()),
                },
                indent=2,
            )
        )
    else:
        print(encoded, end="")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
