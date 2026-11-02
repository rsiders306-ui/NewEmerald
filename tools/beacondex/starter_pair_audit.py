#!/usr/bin/env python3
"""Validate all Route 201 player-pair to Barry-pair selections."""

from __future__ import annotations

import argparse
import itertools
import json
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
ROUTE_201 = REPO_ROOT / "res/field/scripts/scripts_route_201.s"
TYPE_CHART = REPO_ROOT / "src/battle/battle_lib.c"
TRAINER_ROOT = REPO_ROOT / "res/trainers/data"

STARTERS = {
    "SPECIES_GLIMBARK": "glimbark",
    "SPECIES_CALFLANK": "calflank",
    "SPECIES_ZEPHYLET": "zephylet",
    "SPECIES_TURTWIG": "turtwig",
    "SPECIES_CHIMCHAR": "chimchar",
    "SPECIES_PIPLUP": "piplup",
}

EVOLUTIONS = {
    "SPECIES_GLIMBARK": ((16, "SPECIES_WARDMANE"), (36, "SPECIES_SIDERION")),
    "SPECIES_CALFLANK": ((16, "SPECIES_GRIDIRUFF"), (36, "SPECIES_OXGUARD")),
    "SPECIES_ZEPHYLET": ((16, "SPECIES_GALECREST"), (36, "SPECIES_TERRAPTOR")),
    "SPECIES_TURTWIG": ((18, "SPECIES_GROTLE"), (32, "SPECIES_TORTERRA")),
    "SPECIES_CHIMCHAR": ((14, "SPECIES_MONFERNO"), (36, "SPECIES_INFERNAPE")),
    "SPECIES_PIPLUP": ((16, "SPECIES_PRINPLUP"), (36, "SPECIES_EMPOLEON")),
}

SPECIES_DIRECTORIES = {
    species: species.removeprefix("SPECIES_").lower()
    for species in (
        *STARTERS,
        "SPECIES_WARDMANE",
        "SPECIES_SIDERION",
        "SPECIES_GRIDIRUFF",
        "SPECIES_OXGUARD",
        "SPECIES_GALECREST",
        "SPECIES_TERRAPTOR",
        "SPECIES_GROTLE",
        "SPECIES_TORTERRA",
        "SPECIES_MONFERNO",
        "SPECIES_INFERNAPE",
        "SPECIES_PRINPLUP",
        "SPECIES_EMPOLEON",
        "SPECIES_STARAVIA",
        "SPECIES_STARAPTOR",
    )
}

LEGACY_RIVAL_STARTERS = {
    "SPECIES_TURTWIG",
    "SPECIES_GROTLE",
    "SPECIES_TORTERRA",
    "SPECIES_CHIMCHAR",
    "SPECIES_MONFERNO",
    "SPECIES_INFERNAPE",
    "SPECIES_PIPLUP",
    "SPECIES_PRINPLUP",
    "SPECIES_EMPOLEON",
}
BIRD_LINE = {"SPECIES_STARLY", "SPECIES_STARAVIA", "SPECIES_STARAPTOR"}

LABEL_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):$")
FIRST_DISPATCH_RE = re.compile(
    r"^\s*GoToIfEq VAR_PLAYER_STARTER, (SPECIES_[A-Z0-9_]+), "
    r"(Route201_ChooseRivalPairFrom[A-Za-z]+)$"
)
SECOND_DISPATCH_RE = re.compile(
    r"^\s*GoToIfEq VAR_PLAYER_SECOND_STARTER, (SPECIES_[A-Z0-9_]+), "
    r"(Route201_SetRivalPair_[A-Za-z_]+)$"
)
FIRST_RIVAL_RE = re.compile(
    r"^\s*SetVar VAR_RIVAL_STARTER, (SPECIES_[A-Z0-9_]+)$"
)
SECOND_RIVAL_RE = re.compile(
    r"^\s*SetVar VAR_RIVAL_SECOND_STARTER, (SPECIES_[A-Z0-9_]+)$"
)
TYPE_MATCHUP_RE = re.compile(
    r"\{ (TYPE_[A-Z_]+), (TYPE_[A-Z_]+), TYPE_MULTI_SUPER_EFF \}"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit JSON")
    parser.add_argument("--report", type=Path, help="write JSON to this path")
    return parser.parse_args()


def script_sections(source: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    label: str | None = None

    for line in source.splitlines():
        match = LABEL_RE.match(line)
        if match:
            label = match.group(1)
            sections[label] = []
        elif label is not None:
            sections[label].append(line)

    return sections


def parse_dispatch(
    sections: dict[str, list[str]], violations: list[str]
) -> tuple[dict[str, str], dict[str, dict[str, str]]]:
    choose_lines = sections.get("Route201_ChooseRivalStarterPair", [])
    first_dispatch = {
        match.group(1): match.group(2)
        for line in choose_lines
        if (match := FIRST_DISPATCH_RE.match(line))
    }
    if set(first_dispatch) != set(STARTERS):
        violations.append(
            "first-starter dispatch does not cover the six starter species exactly"
        )

    second_dispatch: dict[str, dict[str, str]] = {}
    for first, label in first_dispatch.items():
        entries = {
            match.group(1): match.group(2)
            for line in sections.get(label, [])
            if (match := SECOND_DISPATCH_RE.match(line))
        }
        expected = set(STARTERS) - {first}
        if set(entries) != expected:
            violations.append(
                f"{label} does not cover the five distinct second choices exactly"
            )
        second_dispatch[first] = entries

    return first_dispatch, second_dispatch


def parse_rival_pairs(
    sections: dict[str, list[str]], violations: list[str]
) -> dict[str, tuple[str, str]]:
    pairs: dict[str, tuple[str, str]] = {}
    labels = sorted(
        label for label in sections if label.startswith("Route201_SetRivalPair_")
    )
    if len(labels) != 15:
        violations.append(f"expected 15 rival-pair labels, found {len(labels)}")

    for label in labels:
        first = [
            match.group(1)
            for line in sections[label]
            if (match := FIRST_RIVAL_RE.match(line))
        ]
        second = [
            match.group(1)
            for line in sections[label]
            if (match := SECOND_RIVAL_RE.match(line))
        ]
        if len(first) != 1 or len(second) != 1:
            violations.append(f"{label} must set each rival starter exactly once")
            continue
        pairs[label] = (first[0], second[0])

    return pairs


def load_starter_types(violations: list[str]) -> dict[str, tuple[str, ...]]:
    types: dict[str, tuple[str, ...]] = {}
    for species, directory in STARTERS.items():
        data_path = REPO_ROOT / f"res/pokemon/{directory}/data.json"
        data = json.loads(data_path.read_text())
        species_types = tuple(dict.fromkeys(data["types"]))
        if not species_types:
            violations.append(f"{species} has no base type")
        types[species] = species_types
    return types


def is_super_effective(
    attacker: str,
    defender: str,
    starter_types: dict[str, tuple[str, ...]],
    super_effective: set[tuple[str, str]],
) -> bool:
    return any(
        (attack_type, defend_type) in super_effective
        for attack_type in starter_types[attacker]
        for defend_type in starter_types[defender]
    )


def has_two_hard_counters(
    attackers: tuple[str, str],
    defenders: tuple[str, str],
    starter_types: dict[str, tuple[str, ...]],
    super_effective: set[tuple[str, str]],
) -> bool:
    return any(
        all(
            is_super_effective(attacker, defender, starter_types, super_effective)
            for attacker, defender in zip(attackers, defender_order)
        )
        for defender_order in (defenders, defenders[::-1])
    )


def evolve_rival_starter(species: str, level: int) -> str:
    result = species
    for evolution_level, evolved_species in EVOLUTIONS[species]:
        if level >= evolution_level:
            result = evolved_species
    return result


def default_level_moves(
    species: str, level: int, violations: list[str]
) -> tuple[str, ...]:
    """Mirror BoxPokemon_SetDefaultMoves for a freshly initialized trainer mon."""
    directory = SPECIES_DIRECTORIES[species]
    pokemon_data = json.loads(
        (REPO_ROOT / f"res/pokemon/{directory}/data.json").read_text()
    )
    moves: list[str] = []
    for move_level, move in pokemon_data["learnset"]["by_level"]:
        if move_level > level:
            break
        if move in moves:
            continue
        if len(moves) == 4:
            moves.pop(0)
        moves.append(move)

    for move in moves:
        move_directory = move.removeprefix("MOVE_").lower()
        move_path = REPO_ROOT / f"res/moves/{move_directory}/data.json"
        if not move_path.exists():
            violations.append(
                f"{species} default level-up set references missing {move}"
            )
    return tuple(moves)


def has_damaging_move(moves: tuple[str, ...]) -> bool:
    return any(
        json.loads(
            (
                REPO_ROOT
                / f"res/moves/{move.removeprefix('MOVE_').lower()}/data.json"
            ).read_text()
        )["power"]
        > 0
        for move in moves
        if (
            REPO_ROOT
            / f"res/moves/{move.removeprefix('MOVE_').lower()}/data.json"
        ).exists()
    )


def transformed_rival_roster(
    party: list[dict[str, object]], rival_pair: tuple[str, str]
) -> tuple[list[str], list[int]]:
    species = [mon["species"] for mon in party]
    replaced_slots = [0, 1]
    species[0] = evolve_rival_starter(rival_pair[0], party[0]["level"])
    species[1] = evolve_rival_starter(rival_pair[1], party[1]["level"])

    for slot, mon in enumerate(party[2:], 2):
        if mon["species"] in LEGACY_RIVAL_STARTERS:
            species[slot] = (
                "SPECIES_STARAPTOR" if mon["level"] >= 34 else "SPECIES_STARAVIA"
            )
            replaced_slots.append(slot)

    return species, replaced_slots


def audit_rival_rosters(
    pair_results: list[dict[str, object]], violations: list[str]
) -> tuple[int, int]:
    records = []
    for path in sorted(TRAINER_ROOT.glob("*.json")):
        data = json.loads(path.read_text())
        if data.get("class") == "TRAINER_CLASS_RIVAL":
            records.append((path.name, data["party"]))

    if len(records) != 33:
        violations.append(f"expected 33 Barry records, found {len(records)}")

    runtime_rosters = 0
    for filename, party in records:
        if len(party) < 2:
            violations.append(f"{filename} has fewer than two party members")
            continue
        if any(
            mon.get("form", 0) != 0
            or mon.get("item") not in (None, "ITEM_NONE")
            or mon.get("ball_seal", 0) != 0
            for mon in party[:2]
        ):
            violations.append(
                f"{filename} dynamic slots carry a displaced form, item, or seal"
            )

        late_legacy_slots = [
            slot
            for slot, mon in enumerate(party[2:], 2)
            if mon["species"] in LEGACY_RIVAL_STARTERS
        ]
        if len(late_legacy_slots) > 1:
            violations.append(f"{filename} has multiple later legacy starters")

        for pair_result in pair_results:
            rival_pair = tuple(pair_result["rival"])
            if not all(species in STARTERS for species in rival_pair):
                continue

            transformed, replaced_slots = transformed_rival_roster(party, rival_pair)
            runtime_rosters += 1
            if len(set(transformed)) != len(transformed):
                violations.append(
                    f"{filename} produces a duplicate species for {' + '.join(rival_pair)}"
                )

            expected_birds = len(late_legacy_slots)
            actual_birds = sum(species in BIRD_LINE for species in transformed)
            if actual_birds != expected_birds or actual_birds > 1:
                violations.append(
                    f"{filename} produces {actual_birds} bird-line members; "
                    f"expected {expected_birds}"
                )

            for slot in replaced_slots:
                if party[slot].get("form", 0) != 0:
                    violations.append(
                        f"{filename} replacement slot {slot} has a nonzero form"
                    )
                moves = default_level_moves(
                    transformed[slot], party[slot]["level"], violations
                )
                if not moves:
                    violations.append(
                        f"{filename} replacement slot {slot} has an empty "
                        "default level-up move set"
                    )
                elif not has_damaging_move(moves):
                    violations.append(
                        f"{filename} replacement slot {slot} has no damaging "
                        f"move in its actual default set at level "
                        f"{party[slot]['level']}: {', '.join(moves)}"
                    )

            if filename.startswith("rival_spear_pillar_"):
                if "SPECIES_MUNCHLAX" not in transformed:
                    violations.append(f"{filename} loses Barry's Munchlax identity")
            elif len(party) == 6 and "SPECIES_SNORLAX" not in transformed:
                violations.append(f"{filename} loses Barry's Snorlax identity")
            if len(party) >= 5 and "SPECIES_HERACROSS" not in transformed:
                violations.append(f"{filename} loses Barry's Heracross identity")

    return len(records), runtime_rosters


def audit_custom_starter_fallbacks(violations: list[str]) -> int:
    checks = 0
    sandgem = (
        REPO_ROOT / "res/field/scripts/scripts_sandgem_town_pokemon_research_lab.s"
    ).read_text()
    for species in ("SPECIES_GLIMBARK", "SPECIES_CALFLANK", "SPECIES_ZEPHYLET"):
        marker = (
            f"GoToIfEq VAR_0x8008, {species}, "
            "SandgemTownLab_PokemonSeemsRatherHappy"
        )
        checks += 1
        if marker not in sandgem:
            violations.append(f"Sandgem Lab treats {species} as already evolved")

    cosmetic_defaults = {
        "res/field/scripts/scripts_veilstone_store_1f.s": (
            "SetVar LOCAL_VAR_ACCESSORY_ID, ACCESSORY_PIPLUP_MASK"
        ),
        "res/field/scripts/scripts_pastoria_city.s": (
            "SetVar VAR_0x8004, ACCESSORY_CHIMCHAR_MASK"
        ),
        "res/field/scripts/scripts_jubilife_tv_2f.s": (
            "SetVar VAR_0x8004, ACCESSORY_TURTWIG_MASK"
        ),
    }
    for relative_path, marker in cosmetic_defaults.items():
        checks += 1
        source = (REPO_ROOT / relative_path).read_text()
        if marker not in source or source.index(marker) > source.index(
            "GetPlayerStarterSpecies VAR_RESULT"
        ):
            violations.append(f"{relative_path} lacks a valid custom-starter default")

    system_vars = (REPO_ROOT / "src/system_vars.c").read_text()
    counterpart_fallback = re.compile(
        r"else if \(playerStarter == SPECIES_PIPLUP\) \{\s*"
        r"counterpartStarter = SPECIES_CHIMCHAR;\s*"
        r"\} else \{\s*counterpartStarter = SPECIES_PIPLUP;",
        re.DOTALL,
    )
    checks += 1
    if counterpart_fallback.search(system_vars) is None:
        violations.append(
            "custom-first counterpart fallback does not match the Piplup partner teams"
        )

    # The original three-way script branches intentionally use a deterministic
    # legacy branch for the three BeaconDex starters. Keep those defaults
    # explicit so a future refactor cannot leave VAR_0x8004 unset or select a
    # counterpart team that disagrees with SystemVars_GetPlayerCounterpartStarter.
    partner_defaults = {
        "res/field/scripts/scripts_jubilife_city.s": (
            "SetVar VAR_0x8004, TRAINER_DAWN_JUBILIFE_CITY_TURTWIG",
            "SetVar VAR_0x8004, TRAINER_LUCAS_JUBILIFE_CITY_TURTWIG",
        ),
        "res/field/scripts/scripts_veilstone_city.s": (
            "SetVar VAR_0x8004, TRAINER_DAWN_VEILSTONE_CITY_TURTWIG",
            "SetVar VAR_0x8004, TRAINER_LUCAS_VEILSTONE_CITY_TURTWIG",
        ),
        "res/field/scripts/scripts_fight_area.s": (
            "SetVar VAR_0x8004, TRAINER_RIVAL_FIGHT_AREA_PIPLUP",
        ),
        "res/field/scripts/scripts_spear_pillar.s": (
            "SetVar VAR_0x8004, TRAINER_RIVAL_SPEAR_PILLAR_PIPLUP",
        ),
    }
    for relative_path, markers in partner_defaults.items():
        source = (REPO_ROOT / relative_path).read_text()
        for marker in markers:
            checks += 1
            if marker not in source:
                violations.append(
                    f"{relative_path} lacks custom-starter fallback {marker}"
                )

    # The *_TURTWIG suffix means the player chose Turtwig; these are the
    # counterpart records whose starter is Piplup, matching the C fallback.
    counterpart_records = {
        "dawn_jubilife_city_turtwig.json": "SPECIES_PIPLUP",
        "lucas_jubilife_city_turtwig.json": "SPECIES_PIPLUP",
        "dawn_veilstone_city_turtwig.json": "SPECIES_PRINPLUP",
        "lucas_veilstone_city_turtwig.json": "SPECIES_PRINPLUP",
    }
    for filename, expected_species in counterpart_records.items():
        checks += 1
        party = json.loads((TRAINER_ROOT / filename).read_text())["party"]
        if expected_species not in {mon["species"] for mon in party}:
            violations.append(
                f"{filename} does not contain counterpart fallback {expected_species}"
            )

    underground = (
        REPO_ROOT
        / "res/field/scripts/scripts_eterna_city_underground_man_house.s"
    ).read_text()
    underground_default = (
        "GoTo EternaCityUndergroundManHouse_SendPiplupDollToUndergroundPC"
    )
    checks += 1
    if underground_default not in underground:
        violations.append("Underground Man custom-starter doll fallback is not Piplup")

    return checks


def main() -> int:
    args = parse_args()
    violations: list[str] = []
    sections = script_sections(ROUTE_201.read_text())
    first_dispatch, second_dispatch = parse_dispatch(sections, violations)
    rival_pairs = parse_rival_pairs(sections, violations)
    starter_types = load_starter_types(violations)
    super_effective = set(TYPE_MATCHUP_RE.findall(TYPE_CHART.read_text()))

    results = []
    starters = tuple(STARTERS)
    for player_pair in itertools.combinations(starters, 2):
        labels = []
        for first, second in (player_pair, player_pair[::-1]):
            first_label = first_dispatch.get(first)
            labels.append(second_dispatch.get(first, {}).get(second))

        if None in labels or labels[0] != labels[1]:
            violations.append(
                f"{player_pair[0]} + {player_pair[1]} is not order-independent"
            )
            rival_pair = ("<missing>", "<missing>")
        else:
            rival_pair = rival_pairs.get(labels[0], ("<missing>", "<missing>"))

        valid_species = all(species in STARTERS for species in rival_pair)
        distinct = len(set(rival_pair)) == 2
        unchosen = not set(player_pair).intersection(rival_pair)
        double_counter = (
            has_two_hard_counters(
                rival_pair, player_pair, starter_types, super_effective
            )
            if valid_species and distinct
            else True
        )

        if not valid_species:
            violations.append(
                f"{player_pair[0]} + {player_pair[1]} has an invalid rival pair"
            )
        elif not distinct:
            violations.append(
                f"{player_pair[0]} + {player_pair[1]} gives Barry a duplicate pair"
            )
        elif not unchosen:
            violations.append(
                f"{player_pair[0]} + {player_pair[1]} reuses a player species"
            )
        elif double_counter:
            violations.append(
                f"{player_pair[0]} + {player_pair[1]} receives two hard counters"
            )

        results.append(
            {
                "player": list(player_pair),
                "rival": list(rival_pair),
                "dispatch_label": labels[0],
                "distinct": distinct,
                "unchosen": unchosen,
                "two_hard_counters": double_counter,
            }
        )

    rival_records, runtime_rosters = audit_rival_rosters(results, violations)
    custom_fallback_checks = audit_custom_starter_fallbacks(violations)

    report = {
        "schema": "beacondex-starter-pair-v1",
        "player_combinations": len(results),
        "ordered_dispatches": sum(len(entries) for entries in second_dispatch.values()),
        "valid_combinations": sum(
            result["distinct"]
            and result["unchosen"]
            and not result["two_hard_counters"]
            for result in results
        ),
        "rival_records": rival_records,
        "runtime_rosters": runtime_rosters,
        "custom_fallback_checks": custom_fallback_checks,
        "violations": violations,
        "pairs": results,
    }
    output = json.dumps(report, indent=2) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(output)
    if args.json:
        print(output, end="")
    else:
        print(
            f"starter combinations: {report['player_combinations']}; "
            f"ordered dispatches: {report['ordered_dispatches']}; "
            f"valid: {report['valid_combinations']}; "
            f"Barry records: {report['rival_records']}; "
            f"runtime rosters: {report['runtime_rosters']}; "
            f"custom fallbacks: {report['custom_fallback_checks']}"
        )
        print(f"violations: {len(violations)}")
        for violation in violations:
            print(f"  {violation}")

    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
