#!/usr/bin/env python3
"""Verify BeaconDex coverage and the reviewed trainer assignment manifest."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
TRAINER_ROOT = REPO_ROOT / "res" / "trainers" / "data"
MANIFEST_PATH = REPO_ROOT / "data" / "beacondex" / "species_normalized.json"
ASSIGNMENT_PATH = REPO_ROOT / "data" / "beacondex" / "trainer_distribution.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, help="write the JSON audit here")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    species_manifest = json.loads(MANIFEST_PATH.read_text())
    assignment_manifest = json.loads(ASSIGNMENT_PATH.read_text())
    expected = {row["code_name"] for row in species_manifest["species"]}

    trainers = {
        path.stem: json.loads(path.read_text())
        for path in sorted(TRAINER_ROOT.glob("*.json"))
    }
    occurrences: dict[str, list[str]] = defaultdict(list)
    for trainer_name, trainer in trainers.items():
        for member in trainer["party"]:
            if member["species"] in expected:
                occurrences[member["species"]].append(trainer_name)

    failures: list[str] = []
    assignments = assignment_manifest["assignments"]
    reported_species = [row["species"] for row in assignments]
    reported_trainers = [row["trainer"] for row in assignments]

    missing = sorted(expected - set(occurrences))
    extra = sorted(set(occurrences) - expected)
    duplicates = {
        species: locations
        for species, locations in sorted(occurrences.items())
        if len(locations) != 1
    }
    if missing:
        failures.append(f"missing custom trainer species: {missing}")
    if extra:
        failures.append(f"unexpected custom trainer species: {extra}")
    if duplicates:
        failures.append(f"custom species with non-unique coverage: {duplicates}")
    if Counter(reported_species) != Counter(expected):
        failures.append("assignment manifest does not list every custom species exactly once")
    if len(set(reported_trainers)) != len(reported_trainers):
        failures.append("assignment manifest reuses a trainer")

    for row in assignments:
        trainer_name = row["trainer"]
        trainer = trainers.get(trainer_name)
        if trainer is None:
            failures.append(f"missing trainer record: {trainer_name}")
            continue
        actual_species = [member["species"] for member in trainer["party"]]
        if row["species"] not in actual_species:
            failures.append(f"{trainer_name} no longer contains {row['species']}")
        if len(trainer["party"]) != row["new_party_size"]:
            failures.append(
                f"{trainer_name} party size is {len(trainer['party'])}, "
                f"expected {row['new_party_size']}"
            )

    party_sizes = Counter(len(trainer["party"]) for trainer in trainers.values())
    report = {
        "schema": "beacondex-trainer-distribution-audit-v1",
        "passed": not failures,
        "species_covered": len(occurrences),
        "custom_occurrences": sum(len(value) for value in occurrences.values()),
        "unique_trainers": len({name for values in occurrences.values() for name in values}),
        "story_boss_assignments": sum(bool(row["story_boss"]) for row in assignments),
        "party_sizes": {str(size): count for size, count in sorted(party_sizes.items())},
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
