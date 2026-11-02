#!/usr/bin/env python3
"""Inventory every field trainer-battle command and its reviewed eligibility gate.

This is a deliberately finite regression manifest rather than a general script
interpreter. A new or moved battle call fails the audit until its surrounding
event flow is reviewed and the expected counts below are updated.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_ROOT = REPO_ROOT / "res" / "field" / "scripts"

# file: (reviewed StartTrainerBattle count, minimum CheckHasTwoAliveMons count)
# One guard may dominate several rival/team dispatch branches. Sequential
# battles have a second check or an explicit heal before the next start.
REVIEWED_DIRECT_STARTS = {
    "scripts_battleground.s": (1, 4),
    "scripts_battles.s": (4, 2),
    "scripts_canalave_city.s": (3, 1),
    "scripts_canalave_city_gym.s": (1, 1),
    "scripts_celestic_town.s": (1, 1),
    "scripts_celestic_town_cave.s": (2, 2),
    "scripts_distortion_world_b7f.s": (1, 1),
    "scripts_eterna_city_gym.s": (4, 4),
    "scripts_floaroma_meadow.s": (2, 1),
    "scripts_galactic_hq_4f.s": (1, 1),
    "scripts_galactic_hq_control_room.s": (1, 1),
    "scripts_hearthome_city_dp_gym_leader_room.s": (1, 1),
    "scripts_hearthome_city_gym_leader_room.s": (1, 1),
    "scripts_iron_island_b2f_left_room.s": (1, 0),
    "scripts_lake_verity.s": (1, 1),
    "scripts_oreburgh_city_gym.s": (1, 1),
    "scripts_pastoria_city.s": (3, 1),
    "scripts_pastoria_city_gym.s": (1, 1),
    "scripts_pokemon_center_daily_trainers.s": (1, 1),
    "scripts_pokemon_league_aaron_room.s": (2, 1),
    "scripts_pokemon_league_bertha_room.s": (2, 1),
    "scripts_pokemon_league_champion_room.s": (2, 1),
    "scripts_pokemon_league_flint_room.s": (2, 1),
    "scripts_pokemon_league_lucian_room.s": (2, 1),
    "scripts_pokemon_league_north_pokecenter_1f.s": (3, 1),
    "scripts_pokemon_mansion.s": (6, 6),
    "scripts_restaurant.s": (18, 18),
    "scripts_route_203.s": (3, 1),
    "scripts_route_209_gate_to_hearthome_city.s": (3, 1),
    "scripts_snowpoint_city_gym.s": (1, 1),
    "scripts_spear_pillar.s": (1, 1),
    "scripts_stark_mountain_room_1.s": (2, 1),
    "scripts_sunyshore_city_gym_room_3.s": (1, 1),
    "scripts_survival_area.s": (6, 1),
    "scripts_team_galactic_eterna_building_4f.s": (1, 1),
    "scripts_trainers_school.s": (6, 2),
    "scripts_valley_windworks_building.s": (1, 1),
    "scripts_valley_windworks_outside.s": (1, 1),
    "scripts_valor_cavern.s": (1, 1),
    "scripts_valor_lakefront.s": (1, 1),
    "scripts_veilstone_city_gym.s": (1, 1),
}

SHARED_DISPATCHER = "scripts_battles.s"
AI_PARTNER_FILE = "scripts_iron_island_b2f_left_room.s"
ROUTE_201_FILE = "scripts_route_201.s"

COMMAND_RE = re.compile(
    r"^\s*(StartTrainerBattle|StartFirstBattle|StartTagBattle)\b(.*)$"
)
LABEL_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):\s*$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit JSON")
    parser.add_argument("--report", type=Path, help="write JSON to this path")
    return parser.parse_args()


def calls_in(path: Path) -> list[dict[str, object]]:
    calls = []
    label = "<preamble>"
    for line_number, raw in enumerate(path.read_text().splitlines(), 1):
        label_match = LABEL_RE.match(raw.strip())
        if label_match:
            label = label_match.group(1)
        command_match = COMMAND_RE.match(raw)
        if command_match:
            calls.append(
                {
                    "file": path.relative_to(REPO_ROOT).as_posix(),
                    "line": line_number,
                    "label": label,
                    "command": command_match.group(1),
                    "arguments": command_match.group(2).strip(),
                }
            )
    return calls


def main() -> int:
    args = parse_args()
    paths = sorted(SCRIPT_ROOT.glob("*.s"))
    calls = [call for path in paths for call in calls_in(path)]
    violations: list[str] = []

    actual_direct_files = {
        Path(call["file"]).name
        for call in calls
        if call["command"] == "StartTrainerBattle"
    }
    expected_direct_files = set(REVIEWED_DIRECT_STARTS)
    for name in sorted(actual_direct_files - expected_direct_files):
        violations.append(f"unreviewed StartTrainerBattle file: {name}")
    for name in sorted(expected_direct_files - actual_direct_files):
        violations.append(f"reviewed battle file no longer has a direct start: {name}")

    file_results = []
    for name, (expected_starts, minimum_checks) in sorted(REVIEWED_DIRECT_STARTS.items()):
        path = SCRIPT_ROOT / name
        source = path.read_text()
        actual_starts = source.count("StartTrainerBattle ")
        actual_checks = source.count("CheckHasTwoAliveMons")
        status = "safe"
        reason = "reviewed two-usable-Pokemon guard"

        if name == SHARED_DISPATCHER:
            reason = "shared talk/sight/rematch dispatcher guards ordinary and rematch paths"
        elif name == AI_PARTNER_FILE:
            reason = "battle sets an active AI partner immediately before the start"
            if not re.search(r"SetHasPartner\s*\n\s*StartTrainerBattle", source):
                violations.append(f"{name}: AI partner is no longer set immediately before battle")
                status = "unsafe"

        if actual_starts != expected_starts:
            violations.append(
                f"{name}: expected {expected_starts} StartTrainerBattle calls, found {actual_starts}"
            )
            status = "unsafe"
        if actual_checks < minimum_checks:
            violations.append(
                f"{name}: expected at least {minimum_checks} eligibility checks, found {actual_checks}"
            )
            status = "unsafe"

        file_results.append(
            {
                "file": f"res/field/scripts/{name}",
                "start_trainer_battle": actual_starts,
                "two_alive_checks": actual_checks,
                "status": status,
                "reason": reason,
            }
        )

    for path in paths:
        source = path.read_text()
        if "CommonStrings_Text_BeaconDexTwoPokemonRequired" in source:
            if '#include "res/text/bank/common_strings.h"' not in source:
                violations.append(f"{path.name}: missing common_strings.h include")

    first_calls = [call for call in calls if call["command"] == "StartFirstBattle"]
    if len(first_calls) != 3 or {Path(call["file"]).name for call in first_calls} != {ROUTE_201_FILE}:
        violations.append("StartFirstBattle inventory changed; review the two-starter atomic grant")

    route_201_source = (SCRIPT_ROOT / ROUTE_201_FILE).read_text()
    route_201_markers = (
        "GoToIfEq VAR_0x8000, VAR_PLAYER_STARTER, Route201_StarterMustBeDifferent",
        "GivePokemon VAR_PLAYER_STARTER, 5, ITEM_NONE, VAR_RESULT",
        "GivePokemon VAR_PLAYER_SECOND_STARTER, 5, ITEM_NONE, VAR_RESULT",
    )
    route_201_pair_safe = all(marker in route_201_source for marker in route_201_markers)
    if route_201_pair_safe:
        first_grant = route_201_source.index(route_201_markers[1])
        second_grant = route_201_source.index(route_201_markers[2])
        first_battle = route_201_source.index("StartFirstBattle ")
        route_201_pair_safe = first_grant < second_grant < first_battle
    if not route_201_pair_safe:
        violations.append(
            "Route 201 no longer grants two distinct starters before its first trainer battle"
        )

    tag_calls = [call for call in calls if call["command"] == "StartTagBattle"]
    if len(tag_calls) != 4:
        violations.append(f"expected 4 reviewed tag battles, found {len(tag_calls)}")

    for call in calls:
        name = Path(call["file"]).name
        if call["command"] == "StartTagBattle":
            call["status"] = "safe"
            call["reason"] = "tag battle supplies an AI partner"
        elif call["command"] == "StartFirstBattle":
            call["status"] = "safe" if route_201_pair_safe else "unsafe"
            call["reason"] = (
                "Route 201 grants two distinct level-five starters before the battle"
                if route_201_pair_safe
                else "Route 201 starter-pair grant failed its structural audit"
            )
        else:
            result = next((item for item in file_results if Path(item["file"]).name == name), None)
            call["status"] = result["status"] if result else "unsafe"
            call["reason"] = result["reason"] if result else "unreviewed file"

    report = {
        "schema": "beacondex-trainer-battle-flow-v1",
        "battle_calls": len(calls),
        "start_trainer_battle": sum(call["command"] == "StartTrainerBattle" for call in calls),
        "start_first_battle": len(first_calls),
        "start_tag_battle": len(tag_calls),
        "safe": sum(call["status"] == "safe" for call in calls),
        "deferred": sum(call["status"] == "deferred" for call in calls),
        "violations": violations,
        "reviewed_files": file_results,
        "calls": calls,
    }
    output = json.dumps(report, indent=2) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(output)
    if args.json:
        print(output, end="")
    else:
        print(
            f"trainer battle calls: {report['battle_calls']} "
            f"(trainer={report['start_trainer_battle']}, first={report['start_first_battle']}, "
            f"tag={report['start_tag_battle']})"
        )
        print(f"safe: {report['safe']}; deferred: {report['deferred']}")
        print(f"violations: {len(violations)}")
        for violation in violations:
            print(f"  {violation}")
    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
