#!/usr/bin/env python3
"""Verify that every BeaconDex species cry is registered at its species ID."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SPECIES_LIST = REPO_ROOT / "generated" / "species.txt"
SOUND_DATA = REPO_ROOT / "res" / "sound" / "pl_sound_data.json"
FIRST_SPECIES = "glimbark"
LAST_SPECIES = "cairncrown"
SKY_BANK = {
    "name": "BANK_PV516_SKY",
    "fileName": "shaymin/forms/sky/cry.sbnk",
    "waves": ["WAVE_ARC_PV516_SKY", "", "", ""],
}
SKY_WAVARC = {
    "name": "WAVE_ARC_PV516_SKY",
    "fileName": "shaymin/forms/sky/cry.swar",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--naix",
        type=Path,
        help="also verify the generated pl_sound_data.naix constants",
    )
    parser.add_argument("--report", type=Path, help="write the JSON audit here")
    return parser.parse_args()


def expected_species() -> tuple[int, list[str]]:
    species = [
        line.removeprefix("SPECIES_").lower()
        for line in SPECIES_LIST.read_text().splitlines()
    ]
    first_id = species.index(FIRST_SPECIES)
    last_id = species.index(LAST_SPECIES)
    return first_id, species[first_id : last_id + 1]


def check_naix(path: Path, expected: dict[str, int], failures: list[str]) -> None:
    if not path.is_file():
        failures.append(f"generated NAIX does not exist: {path}")
        return

    definitions = {
        name: int(value)
        for name, value in re.findall(
            r"^#define\s+(\w+)\s+(\d+)\s*$", path.read_text(), re.MULTILINE
        )
    }
    for name, expected_id in expected.items():
        actual_id = definitions.get(name)
        if actual_id != expected_id:
            failures.append(
                f"{path}: {name} should be {expected_id}, found {actual_id!r}"
            )


def main() -> int:
    args = parse_args()
    failures: list[str] = []
    first_id, species = expected_species()
    last_id = first_id + len(species) - 1
    sky_slot = last_id + 1

    if (first_id, last_id, len(species)) != (494, 556, 63):
        failures.append(
            "generated/species.txt no longer assigns the 63 BeaconDex species to IDs 494..556"
        )

    sound_data = json.loads(SOUND_DATA.read_text())
    banks = sound_data["bankInfo"]
    wave_archives = sound_data["wavarcInfo"]
    if len(banks) <= sky_slot or len(wave_archives) <= sky_slot:
        failures.append("sound bank or wave-archive table ends before the Sky Form slot")
    else:
        for species_id, stem in enumerate(species, first_id):
            wave_name = f"WAVE_ARC_BDX_{species_id}"
            expected_bank = {
                "name": f"BANK_BDX_{species_id}",
                "fileName": f"{stem}/cry.sbnk",
                "waves": [wave_name, "", "", ""],
            }
            expected_wave = {
                "name": wave_name,
                "fileName": f"{stem}/cry.swar",
            }
            if banks[species_id] != expected_bank:
                failures.append(
                    f"bankInfo[{species_id}] is not the expected {stem} cry bank"
                )
            if wave_archives[species_id] != expected_wave:
                failures.append(
                    f"wavarcInfo[{species_id}] is not the expected {stem} cry wave archive"
                )
            for source_name in ("cry.txt", "cry.wav"):
                source = REPO_ROOT / "res" / "pokemon" / stem / source_name
                if not source.is_file() or source.stat().st_size == 0:
                    failures.append(f"missing or empty cry source: {source.relative_to(REPO_ROOT)}")

        if banks[sky_slot] != SKY_BANK:
            failures.append(f"bankInfo[{sky_slot}] is not the Shaymin Sky Form bank")
        if wave_archives[sky_slot] != SKY_WAVARC:
            failures.append(f"wavarcInfo[{sky_slot}] is not the Shaymin Sky Form wave archive")

        registered_banks = [entry.get("fileName") for entry in banks]
        registered_waves = [entry.get("fileName") for entry in wave_archives]
        for species_id, stem in enumerate(species, first_id):
            for entries, suffix in (
                (registered_banks, "cry.sbnk"),
                (registered_waves, "cry.swar"),
            ):
                file_name = f"{stem}/{suffix}"
                slots = [index for index, value in enumerate(entries) if value == file_name]
                if slots != [species_id]:
                    failures.append(
                        f"{file_name} must be registered only at {species_id}, found {slots}"
                    )

    naix_constants: dict[str, int] = {}
    for species_id, stem in enumerate(species, first_id):
        naix_constants[f"{stem}_cry_sbnk"] = species_id
        naix_constants[f"{stem}_cry_swar"] = species_id
    naix_constants["shaymin_forms_sky_cry_sbnk"] = sky_slot
    naix_constants["shaymin_forms_sky_cry_swar"] = sky_slot
    if args.naix:
        check_naix(args.naix, naix_constants, failures)

    report = {
        "schema": "beacondex-cry-sdat-audit-v1",
        "passed": not failures,
        "species_id_range": [first_id, last_id],
        "registered_species": len(species),
        "shaymin_sky_slot": sky_slot,
        "source_assets": len(species) * 2,
        "naix_checked": bool(args.naix),
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
