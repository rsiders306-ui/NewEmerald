#!/usr/bin/env python3
"""Regression audit for the five offline Battle Frontier doubles flows."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]

REQUIRED_SNIPPETS = {
    "src/overlay104/ov104_0223A0C4.c": (
        "case BATTLE_TOWER_MODE_SINGLE:\n    case BATTLE_TOWER_MODE_WIFI:\n    case BATTLE_TOWER_MODE_5:\n    case BATTLE_TOWER_MODE_DOUBLE:\n        return BATTLE_TYPE_FRONTIER_DOUBLES;",
    ),
    "src/overlay104/battle_castle_helpers.c": (
        "case FRONTIER_CHALLENGE_SINGLE:\n    case FRONTIER_CHALLENGE_DOUBLE:\n        return BATTLE_TYPE_FRONTIER_DOUBLES;",
    ),
    "src/overlay104/battle_arcade_helpers.c": (
        "case FRONTIER_CHALLENGE_SINGLE:\n    case FRONTIER_CHALLENGE_DOUBLE:\n        return BATTLE_TYPE_FRONTIER_DOUBLES;",
    ),
    "src/overlay104/battle_factory_helpers.c": (
        "case FRONTIER_CHALLENGE_SINGLE:\n    case FRONTIER_CHALLENGE_DOUBLE:\n        return BATTLE_TYPE_FRONTIER_DOUBLES;",
    ),
    "res/field/scripts/scripts_battle_hall.s": (
        "CallBattleHallLobbyFunction BH_LOBBY_FUNC_CHECK_PARTY_ELIGIBLE, 2, VAR_RESULT",
        "GoToIfEq VAR_RESULT, 0, BattleHall_PrintEligbilityRulesForTwoPokemon",
    ),
    "src/scrcmd_battle_hall.c": (
        "taskEnv->challengeType == FRONTIER_CHALLENGE_SINGLE\n        || taskEnv->challengeType == FRONTIER_CHALLENGE_DOUBLE",
        "partyMenu->minSelectionSlots = 2;\n        partyMenu->maxSelectionSlots = 2;",
    ),
    "src/overlay104/frscrcmd_battle_hall.c": (
        "args->challengeType == FRONTIER_CHALLENGE_SINGLE\n        || args->challengeType == FRONTIER_CHALLENGE_DOUBLE",
        "battleHall->partySlots[1]",
    ),
    "src/overlay104/battle_hall.c": (
        "BattleHall_PickNextOpponentPokemon(BattleHall_GetOpponentPartySize(battleHall->challengeType)",
    ),
    "src/overlay104/battle_hall_helpers.c": (
        "BattleHall_SetMonsPersonality(battleHall, offset + i)",
        "&battleHall->opponentMons[offset + i]",
        "return BattleHall_GetHighestLevelInParty(battleHall) / 10;",
    ),
    "res/text/battle_hall.json": (
        '"en_US": "STANDARD DOUBLE"',
    ),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, help="write the JSON audit here")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    failures: list[str] = []
    checked = 0
    for relative_path, snippets in REQUIRED_SNIPPETS.items():
        source = (REPO_ROOT / relative_path).read_text()
        for snippet in snippets:
            checked += 1
            if snippet not in source:
                failures.append(f"{relative_path}: missing reviewed marker {snippet!r}")

    report = {
        "schema": "beacondex-frontier-doubles-audit-v1",
        "passed": not failures,
        "facilities": ["Tower", "Castle", "Arcade", "Factory", "Hall"],
        "reviewed_markers": checked,
        "hall_player_party_size": 2,
        "hall_opponent_party_size": 2,
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
