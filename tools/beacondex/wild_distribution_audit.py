#!/usr/bin/env python3
"""Validate the permanent BeaconDex wild-encounter distribution."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path


ENCOUNTER_TABLES = (
    "land_encounters",
    "surf_encounters",
    "old_rod_encounters",
    "good_rod_encounters",
    "super_rod_encounters",
)
STARTER_CHOICES = {
    "SPECIES_GLIMBARK",
    "SPECIES_CALFLANK",
    "SPECIES_ZEPHYLET",
    "SPECIES_TURTWIG",
    "SPECIES_CHIMCHAR",
    "SPECIES_PIPLUP",
}
GREAT_MARSH_MAPS = {f"great_marsh_{area}" for area in range(1, 7)}


def dynamic_slot_status(map_name: str, table: str, slot: int) -> tuple[str, str] | None:
    """Describe engine replacements that can hide a base encounter slot.

    Great Marsh land slots 6 and 7 are a special case: the player can only
    encounter Pokémon there while the Safari Game is active, and that state
    always replaces both slots with the area's daily species. Other replacement
    mechanisms are conditional, so their base species remain reachable in a
    normal configuration.
    """

    if table != "land_encounters":
        return None
    if map_name in GREAT_MARSH_MAPS and slot in (6, 7):
        return (
            "always",
            "Great Marsh Safari encounters always replace land slots 6 and 7",
        )
    if map_name == "trophy_garden" and slot in (6, 7):
        return (
            "conditional",
            "Trophy Garden daily encounters replace land slots 6 and 7",
        )
    if slot in (0, 1):
        return ("conditional", "an active swarm can replace land slots 0 and 1")
    if slot in (2, 3):
        return ("conditional", "day and night tables replace land slots 2 and 3")
    if slot in (8, 9):
        return ("conditional", "a dual-slot cartridge can replace land slots 8 and 9")
    return None


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
    starter_recovery = manifest["starter_recovery_placements"]
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
    reachable_encounter_counts = Counter()
    for path in (repo / "res/field/encounters").glob("encounters_*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        map_name = path.stem.removeprefix("encounters_")
        for table in ENCOUNTER_TABLES:
            for slot_index, encounter in enumerate(data.get(table, [])):
                species_name = encounter["species"]
                status = dynamic_slot_status(map_name, table, slot_index)
                if status is None or status[0] != "always":
                    reachable_encounter_counts[species_name] += 1

    conditional_dynamic_slots = []
    for row in placements + starter_recovery:
        status = dynamic_slot_status(row["map"], row["table"], row["slot"])
        if status and status[0] == "always":
            failures.append(f"{row['species']} is unreachable: {status[1]}")
        elif status:
            conditional_dynamic_slots.append(
                {
                    "species": row["species"],
                    "map": row["map"],
                    "slot": row["slot"],
                    "reason": status[1],
                }
            )

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
        if reachable_encounter_counts[row["species"]] < 1:
            failures.append(f"{row['species']} has no runtime-reachable wild encounter")
        replaced = row["replaced_species"]
        if replaced != "SPECIES_NONE" and reachable_encounter_counts[replaced] < 1:
            failures.append(f"replaced original species is no longer wild: {replaced}")

    for row in placements:
        family_stages[row["family"]].add(row["stage"])
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

    recovery_species = {row["species"] for row in starter_recovery}
    expected_recovery = {"SPECIES_TURTWIG", "SPECIES_CHIMCHAR", "SPECIES_PIPLUP"}
    if recovery_species != expected_recovery:
        failures.append(f"unexpected Sinnoh starter recovery set: {sorted(recovery_species)}")

    reachable_starters = {
        row["species"]
        for row in placements + starter_recovery
        if dynamic_slot_status(row["map"], row["table"], row["slot"])
        is None
    }
    for chosen_pair in combinations(sorted(STARTER_CHOICES), 2):
        unavailable = STARTER_CHOICES.difference(chosen_pair).difference(reachable_starters)
        if unavailable:
            failures.append(
                f"starter pair {chosen_pair} leaves unobtainable choices: {sorted(unavailable)}"
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
        "maps_changed": len({row["map"] for row in placements + starter_recovery}),
        "land_placements": sum(row["table"] == "land_encounters" for row in placements),
        "water_placements": sum(row["table"] != "land_encounters" for row in placements),
        "starter_recovery_placements": len(starter_recovery),
        "starter_pair_combinations_checked": len(list(combinations(STARTER_CHOICES, 2))),
        "conditional_dynamic_slots": conditional_dynamic_slots,
        "failures": failures,
    }
    print(json.dumps(report, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
