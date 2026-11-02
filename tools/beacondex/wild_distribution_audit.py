#!/usr/bin/env python3
"""Validate the permanent BeaconDex wild-encounter distribution."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[2])
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo = args.repo.resolve()
    manifest_path = repo / "data/beacondex/wild_distribution.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    placements = manifest["placements"]
    species_manifest = json.loads(
        (repo / "data/beacondex/species_normalized.json").read_text(encoding="utf-8")
    )["species"]
    species_by_family_stage = {
        (row["family_index"], row["stage"]): row for row in species_manifest
    }
    failures: list[str] = []

    species = [row["species"] for row in placements]
    if len(placements) != 63:
        failures.append(f"expected 63 placements, found {len(placements)}")
    if len(set(species)) != 63:
        failures.append("custom species placements are not unique")

    family_stages: dict[int, set[int]] = defaultdict(set)
    slots = set()
    encounter_counts = Counter()
    for path in (repo / "res/field/encounters").glob("encounters_*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        for table in (
            "land_encounters",
            "surf_encounters",
            "old_rod_encounters",
            "good_rod_encounters",
            "super_rod_encounters",
        ):
            encounter_counts.update(slot["species"] for slot in data.get(table, []))

    for row in placements:
        family_stages[row["family"]].add(row["stage"])
        slot_key = (row["map"], row["table"], row["slot"])
        if slot_key in slots:
            failures.append(f"duplicate placement slot: {slot_key}")
        slots.add(slot_key)

        path = repo / "res/field/encounters" / f"encounters_{row['map']}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        actual = data[row["table"]][row["slot"]]
        if actual["species"] != row["species"]:
            failures.append(
                f"{row['species']} expected in {row['map']} {row['table']} "
                f"slot {row['slot']}, found {actual['species']}"
            )
        for level_key in ("level", "level_min", "level_max"):
            if level_key in row and actual[level_key] != row[level_key]:
                failures.append(f"{row['species']} has mismatched {level_key}")
        if encounter_counts[row["species"]] < 1:
            failures.append(f"{row['species']} is not obtainable from a permanent encounter")
        replaced = row["replaced_species"]
        if replaced != "SPECIES_NONE" and encounter_counts[replaced] < 1:
            failures.append(f"replaced original species is no longer wild: {replaced}")

        if row["stage"] > 1:
            predecessor = species_by_family_stage[(row["family"], row["stage"] - 1)]
            evolution = predecessor["evolution"]
            if evolution and evolution[0] == "EVO_LEVEL":
                minimum_level = row.get("level", row.get("level_min"))
                if minimum_level < evolution[1]:
                    failures.append(
                        f"{row['species']} appears at level {minimum_level} below its "
                        f"level-{evolution[1]} evolution threshold"
                    )

    if sorted(family_stages) != list(range(1, 22)):
        failures.append("expected family IDs 1 through 21")
    for family in range(1, 22):
        if family_stages[family] != {1, 2, 3}:
            failures.append(f"family {family} does not expose all three stages")

    registry = set((repo / "generated/species.txt").read_text(encoding="utf-8").splitlines())
    missing_constants = sorted(set(species) - registry)
    if missing_constants:
        failures.append(f"missing generated species constants: {missing_constants}")

    report = {
        "passed": not failures,
        "species_placed": len(set(species)),
        "families_covered": len(family_stages),
        "maps_changed": len({row["map"] for row in placements}),
        "land_placements": sum(row["table"] == "land_encounters" for row in placements),
        "water_placements": sum(row["table"] != "land_encounters" for row in placements),
        "failures": failures,
    }
    print(json.dumps(report, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
