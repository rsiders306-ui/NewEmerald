#!/usr/bin/env python3
"""Audit and deterministically complete regular trainer parties for doubles."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
TRAINER_DIR = REPO_ROOT / "res" / "trainers" / "data"

RIVAL_201_PARTNERS = {
    "rival_route_201_chimchar": "SPECIES_TURTWIG",
    "rival_route_201_piplup": "SPECIES_CHIMCHAR",
    "rival_route_201_turtwig": "SPECIES_PIPLUP",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--emit-patch",
        action="store_true",
        help="emit an apply_patch patch that completes every one-Pokémon party",
    )
    parser.add_argument(
        "--report",
        type=Path,
        help="write the machine-readable audit to this path",
    )
    return parser.parse_args()


def load_records() -> list[tuple[Path, dict]]:
    return [
        (path, json.loads(path.read_text()))
        for path in sorted(TRAINER_DIR.glob("*.json"))
    ]


def category(path: Path) -> str:
    if path.stem == "none":
        return "sentinel"
    if path.stem.startswith("dummy_"):
        return "dummy"
    if "unused" in path.stem:
        return "unused"
    return "active"


def partner_pools(records: list[tuple[Path, dict]]) -> dict[str, list[tuple[Path, dict]]]:
    pools: dict[str, list[tuple[Path, dict]]] = defaultdict(list)
    for path, record in records:
        for member in record["party"]:
            pools[record["class"]].append((path, member))
    return pools


def choose_partner(
    path: Path,
    record: dict,
    pools: dict[str, list[tuple[Path, dict]]],
) -> dict:
    first = record["party"][0]

    if path.stem in RIVAL_201_PARTNERS:
        partner = copy.deepcopy(first)
        partner["species"] = RIVAL_201_PARTNERS[path.stem]
        return partner

    candidates = [
        (source_path, member)
        for source_path, member in pools[record["class"]]
        if member["species"] != first["species"]
    ]
    if candidates:
        _, selected = min(
            candidates,
            key=lambda candidate: (
                abs(candidate[1]["level"] - first["level"]),
                candidate[1]["level"] > first["level"] + 3,
                candidate[0].name,
                candidate[1]["species"],
            ),
        )
        partner = copy.deepcopy(selected)
    else:
        partner = copy.deepcopy(first)

    partner["level"] = first["level"]
    partner["iv_scale"] = first["iv_scale"]
    partner["ball_seal"] = 0

    if isinstance(first["item"], str):
        if not isinstance(partner["item"], str):
            partner["item"] = "ITEM_NONE"
    else:
        partner["item"] = None

    if isinstance(first["moves"], list):
        if not isinstance(partner["moves"], list) or not partner["moves"]:
            partner["moves"] = copy.deepcopy(first["moves"])
    else:
        partner["moves"] = None

    return partner


def render(record: dict) -> str:
    return json.dumps(record, ensure_ascii=False, indent=4) + "\n"


def emit_patch(records: list[tuple[Path, dict]]) -> int:
    pools = partner_pools(records)
    patches = []

    for path, record in records:
        if path.stem == "none" or len(record["party"]) != 1:
            continue

        old = path.read_text()
        updated = copy.deepcopy(record)
        updated["party"].append(choose_partner(path, record, pools))
        new = render(updated)

        hunk = [f"*** Update File: {path}", "@@"]
        hunk.extend(f"-{line}" for line in old.splitlines())
        hunk.extend(f"+{line}" for line in new.splitlines())
        patches.extend(hunk)

    if not patches:
        print("No one-Pokémon trainer parties require completion.", file=sys.stderr)
        return 0

    print("*** Begin Patch")
    print("\n".join(patches))
    print("*** End Patch")
    return 0


def build_report(records: list[tuple[Path, dict]]) -> dict:
    party_sizes = Counter(len(record["party"]) for _, record in records)
    categories = Counter(category(path) for path, _ in records)
    one_mon_categories = Counter(
        category(path)
        for path, record in records
        if len(record["party"]) == 1
    )
    violations = [
        str(path.relative_to(REPO_ROOT))
        for path, record in records
        if path.stem != "none" and len(record["party"]) < 2
    ]
    return {
        "schema": "beacondex-trainer-double-coverage-v1",
        "trainer_records": len(records),
        "party_sizes": {str(size): count for size, count in sorted(party_sizes.items())},
        "categories": dict(sorted(categories.items())),
        "one_pokemon_categories": dict(sorted(one_mon_categories.items())),
        "minimum_party_size": 2,
        "violations": violations,
        "all_regular_trainers_double_ready": not violations,
        "format_policy": (
            "offline non-Frontier NPC trainer DTOs are forced to doubles in "
            "FieldBattleDTO_New; JSON double_battle remains reserved for paired NPC scripts"
        ),
    }


def main() -> int:
    args = parse_args()
    records = load_records()

    if args.emit_patch:
        return emit_patch(records)

    report = build_report(records)
    output = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(output)
    print(output, end="")
    return 0 if report["all_regular_trainers_double_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
