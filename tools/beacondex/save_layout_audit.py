#!/usr/bin/env python3
"""Audit the species-dependent save layout against Platinum's 32-page limit."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SECTOR_SIZE = 0x1000
SAVE_PAGE_MAX = 32
SAVE_BLOCK_FOOTER_SIZE = 20
SAVE_CHECK_FOOTER_SIZE = 16

# Audited sum of SaveTableEntry_BodySize() for every normal-block entry other
# than the Pokedex. Those entries are species-independent in this project.
NORMAL_NON_POKEDEX_PAGE_BYTES = 52_204

EXPECTED = {
    "pokedex_size": 900,
    "normal_size": 53_132,
    "normal_sectors": 13,
    "normal_spare": 116,
    "pc_size": 74_212,
    "pc_sectors": 19,
    "pc_spare": 3_612,
    "total_sectors": 32,
    "hall_record_size": 3_356,
    "hall_stored_size": 3_372,
    "hall_spare": 724,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, help="write the JSON audit here")
    return parser.parse_args()


def align4(value: int) -> int:
    return (value + 3) & ~3


def save_page_body_size(value: int) -> int:
    # Mirrors SaveTableEntry_BodySize(), including its extra four bytes when
    # the raw size is already aligned.
    return value + (4 - value % 4) + 4


def require_markers(path: str, markers: tuple[str, ...], failures: list[str]) -> None:
    source = (REPO_ROOT / path).read_text()
    for marker in markers:
        if marker not in source:
            failures.append(f"{path}: missing layout marker {marker!r}")


def main() -> int:
    args = parse_args()
    failures: list[str] = []

    species = (REPO_ROOT / "generated" / "species.txt").read_text().splitlines()
    max_species = species.index("SPECIES_BAD_EGG")
    national_dex_count = species.index("SPECIES_CAIRNCROWN")
    if max_species != national_dex_count + 2:
        failures.append("MAX_SPECIES is no longer National Dex count plus Egg and Bad Egg")

    dex_words = (national_dex_count - 1) // 32 + 1
    unown_form_count = 28
    pokedex_size = align4(
        4  # magic
        + 4 * dex_words * 4  # caught, seen, and two recorded-gender bitsets
        + 4  # Spinda personality
        + 4  # Shellos, Gastrodon, Burmy, and Wormadam form bytes
        + unown_form_count
        + max_species + 1  # recordedLanguages
        + 4  # feature flags
    )
    pokedex_size = align4(pokedex_size + 4 + 2)  # Rotom, Shaymin, Giratina

    box_pokemon_size = 136
    pc_boxes_raw_size = align4(
        4 + 18 * 30 * box_pokemon_size + 18 * 20 * 2 + 18 + 1
    )
    pc_size = save_page_body_size(pc_boxes_raw_size) + SAVE_BLOCK_FOOTER_SIZE

    normal_size = (
        NORMAL_NON_POKEDEX_PAGE_BYTES
        + save_page_body_size(pokedex_size)
        + SAVE_BLOCK_FOOTER_SIZE
    )
    normal_sectors = (normal_size + SECTOR_SIZE - 1) // SECTOR_SIZE
    pc_sectors = (pc_size + SECTOR_SIZE - 1) // SECTOR_SIZE
    normal_spare = normal_sectors * SECTOR_SIZE - normal_size
    pc_spare = pc_sectors * SECTOR_SIZE - pc_size
    total_sectors = normal_sectors + pc_sectors

    hall_record_size = align4(4 + 3 * max_species * 2 + 2)
    hall_stored_size = hall_record_size + SAVE_CHECK_FOOTER_SIZE
    hall_spare = SECTOR_SIZE - hall_stored_size

    actual = {
        "pokedex_size": pokedex_size,
        "normal_size": normal_size,
        "normal_sectors": normal_sectors,
        "normal_spare": normal_spare,
        "pc_size": pc_size,
        "pc_sectors": pc_sectors,
        "pc_spare": pc_spare,
        "total_sectors": total_sectors,
        "hall_record_size": hall_record_size,
        "hall_stored_size": hall_stored_size,
        "hall_spare": hall_spare,
    }
    for name, expected in EXPECTED.items():
        if actual[name] != expected:
            failures.append(f"{name}: expected {expected}, found {actual[name]}")

    if total_sectors > SAVE_PAGE_MAX:
        failures.append(
            f"normal and PC blocks need {total_sectors} sectors; limit is {SAVE_PAGE_MAX}"
        )
    if hall_stored_size > SECTOR_SIZE:
        failures.append(
            f"Battle Hall record needs {hall_stored_size} bytes; page is {SECTOR_SIZE}"
        )

    require_markers(
        "include/pokedex.h",
        (
            "u32 caughtPokemon[DEX_SIZE_U32];",
            "u32 seenPokemon[DEX_SIZE_U32];",
            "u32 recordedGenders[2][DEX_SIZE_U32];",
            "u8 recordedLanguages[MAX_SPECIES + 1];",
        ),
        failures,
    )
    require_markers(
        "include/pc_boxes.h",
        (
            "#define MAX_PC_BOXES              18",
            "#define MAX_MONS_PER_BOX          (MAX_PC_ROWS * MAX_PC_COLS)",
            "BoxPokemon boxMons[MAX_PC_BOXES][MAX_MONS_PER_BOX];",
        ),
        failures,
    )
    require_markers(
        "include/battle_hall_win_records.h",
        (
            "u16 singleStreaks[MAX_SPECIES];",
            "u16 doubleStreaks[MAX_SPECIES];",
            "u16 multiStreaks[MAX_SPECIES];",
        ),
        failures,
    )
    require_markers(
        "src/savedata.c",
        (
            "pageInfo[i].size = SaveTableEntry_BodySize(i);",
            "blockInfo[i].sectorsInUse = (blockInfo[i].size + SAVE_SECTOR_SIZE - 1) / SAVE_SECTOR_SIZE;",
            "GF_ASSERT(totalSectors <= SAVE_PAGE_MAX);",
            "saveTable[i].initFunc(page);",
        ),
        failures,
    )

    report = {
        "schema": "beacondex-save-layout-audit-v1",
        "passed": not failures,
        "species": {
            "national_dex_count": national_dex_count,
            "max_species": max_species,
        },
        "layout": actual,
        "limits": {
            "sector_size": SECTOR_SIZE,
            "save_page_max": SAVE_PAGE_MAX,
        },
        "fresh_save": "supported; every page is sized and initialized from the current table",
        "existing_save": "incompatible with the expanded species-dependent layout",
        "failures": failures,
    }
    output = json.dumps(report, indent=2) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(output)
    print(output, end="")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
