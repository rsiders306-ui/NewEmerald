#!/usr/bin/env python3
"""Audit all trainers and the reviewed major-team doubles balance changes."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from apply_trainer_balance import (
    SIGNATURE_MOVE_EXCEPTIONS, STRATEGY_MANIFEST, effective_power, is_curated_major,
    move_safe, uses_weaker_stat,
)
from trainer_balance_common import (
    ALLY_HIT_RANGES, BANNED_BALANCE_MOVES, POWER_CAPS, REPO_ROOT, RIVAL_FAMILY_SUPPORT,
    RIVAL_STARTER_FAMILIES, ROSTER_MANIFEST, TRAINER_ROOT, BalanceData, immutable_hash,
    load_json, progression_tier, required_ai_flags, trainer_category,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, help="write the machine-readable report")
    return parser.parse_args()


def rival_runtime_audit(data: BalanceData) -> tuple[list[str], dict[str, Any]]:
    failures = []
    source = (REPO_ROOT / "src" / "trainer_data.c").read_text(encoding="utf-8")
    fragments = [
        "static u16 TrainerData_RivalDoublesMove(u16 species, u8 level)",
        "static void TrainerData_ApplyRivalDoublesSupport(Pokemon *mon, u16 species, u8 level)",
        "if (level <= 5)",
        "dto->trainer[battler].header.trainerType == TRAINER_CLASS_RIVAL && i < 2 && useLevelUpMoves == TRUE",
        "TrainerData_ApplyRivalDoublesSupport(mon, species, trmon[i].level);",
        "Pokemon_GetValue(mon, MON_DATA_MOVE1 + moveSlot, NULL)",
        "emptySlot >= 0 ? emptySlot : 3",
        "case SPECIES_GLIMBARK:", "return MOVE_HELPING_HAND;", "case SPECIES_CALFLANK:",
        "MOVE_ROCK_TOMB", "case SPECIES_ZEPHYLET:", "return MOVE_SAND_ATTACK;",
        "case SPECIES_TURTWIG:", "MOVE_RAZOR_LEAF", "case SPECIES_PIPLUP:",
        "return MOVE_GROWL;",
    ]
    for fragment in fragments:
        if fragment not in source:
            failures.append(f"rival runtime hook missing: {fragment}")
    call = "TrainerData_ApplyRivalDoublesSupport(mon, species, trmon[i].level);"
    if source.count(call) != 4:
        failures.append("rival support must cover both dynamic slots in all four trainer archive layouts")

    minimum_level = {
        "SPECIES_GLIMBARK": 6, "SPECIES_CALFLANK": 18, "SPECIES_ZEPHYLET": 6,
        "SPECIES_TURTWIG": 13, "SPECIES_CHIMCHAR": 6, "SPECIES_PIPLUP": 6,
        "SPECIES_WARDMANE": 16, "SPECIES_GRIDIRUFF": 18, "SPECIES_GALECREST": 16,
        "SPECIES_GROTLE": 18, "SPECIES_MONFERNO": 14, "SPECIES_PRINPLUP": 16,
        "SPECIES_SIDERION": 36, "SPECIES_OXGUARD": 36, "SPECIES_TERRAPTOR": 36,
        "SPECIES_TORTERRA": 32, "SPECIES_INFERNAPE": 36, "SPECIES_EMPOLEON": 36,
    }
    assignments = []
    for species in RIVAL_STARTER_FAMILIES:
        move = RIVAL_FAMILY_SUPPORT[species]
        level = minimum_level[species]
        legal = move in data.legal_moves(species, level)
        assignments.append({"species": species, "minimum_runtime_level": level, "move": move, "legal": legal})
        if not legal:
            failures.append(f"runtime rival move is not learnable: {species} {move} at {level}")
    route_species = [
        "SPECIES_GLIMBARK", "SPECIES_CALFLANK", "SPECIES_ZEPHYLET",
        "SPECIES_TURTWIG", "SPECIES_CHIMCHAR", "SPECIES_PIPLUP",
    ]
    route_pairs = []
    for left_index, left in enumerate(route_species):
        for right in route_species[left_index + 1:]:
            move_sets = {
                species: data.engine_default_moves(species, 5)
                for species in (left, right)
            }
            role_moves = [
                move for moves in move_sets.values() for move in moves
                if data.move_is_synergy(move, [
                    {"species": left, "level": 5}, {"species": right, "level": 5}
                ])
            ]
            route_pairs.append({
                "pair": [left, right], "level": 5, "moves": move_sets,
                "natural_level_up_only": True, "has_doubles_control": bool(role_moves),
                "control_moves": role_moves,
            })
    return failures, {
        "passed": not failures, "assignments": assignments,
        "route_201_pairs": route_pairs,
        "route_201_pairs_with_control": sum(row["has_doubles_control"] for row in route_pairs),
    }


def baseline_record_view(baseline: dict[str, Any]) -> dict[str, Any]:
    return {
        "ai_flags": baseline["ai_flags"], "moves": baseline["party_moves"],
        "items": baseline["party_items"],
        "roster": [member["species"] for member in baseline["party_identity"]],
    }


def current_record_view(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "ai_flags": record["ai_flags"], "moves": [member["moves"] for member in record["party"]],
        "items": [member["item"] for member in record["party"]],
        "roster": [member["species"] for member in record["party"]],
    }


def main() -> int:
    args = parse_args()
    data = BalanceData()
    baseline_manifest = load_json(ROSTER_MANIFEST)
    strategy_manifest = load_json(STRATEGY_MANIFEST)
    baselines = baseline_manifest["records"]
    strategies = {row["trainer"]: row for row in strategy_manifest["strategies"]}
    records = [(path, load_json(path)) for path in sorted(TRAINER_ROOT.glob("*.json"))]

    failures: list[str] = []
    warnings: list[str] = []
    runtime_failures, runtime_report = rival_runtime_audit(data)
    failures.extend(runtime_failures)
    summaries = []
    categories, tiers, party_sizes = Counter(), Counter(), Counter()
    moves_checked = resolved_level_moves = legal_curated_moves = 0
    inherited_move_anomalies, unsafe_spreads, introduced_moves = [], [], []
    curated_unsafe_spreads = inherited_unsafe_spreads = 0
    curated_records = content_changed_records = ai_changed_records = 0
    curated_changed_records = curated_with_lead_role = 0
    retained_support_checked = 0

    actual_names = {path.stem for path, _ in records}
    if actual_names != set(baselines):
        failures.append("baseline trainer record set differs from current resources")

    for path, record in records:
        stem = path.stem
        category, tier = trainer_category(stem), progression_tier(record)
        categories[category] += 1
        tiers[tier] += 1
        party_sizes[len(record["party"])] += 1
        curated = is_curated_major(stem, record)
        if curated:
            curated_records += 1
        record_failures, record_warnings = [], []
        baseline = baselines.get(stem)
        if baseline is None:
            record_failures.append("missing baseline record")
            continue
        if immutable_hash(record) != baseline["immutable_hash"]:
            record_failures.append("species/levels/forms/story identity changed")
        if category != "sentinel" and len(record["party"]) < 2:
            record_failures.append("party has fewer than two members")

        current_view, before_view = current_record_view(record), baseline_record_view(baseline)
        content_changed = any(
            current_view[key] != before_view[key]
            for key in ("moves", "items", "roster")
        )
        ai_changed = current_view["ai_flags"] != before_view["ai_flags"]
        if content_changed:
            content_changed_records += 1
        if ai_changed:
            ai_changed_records += 1
        if curated and (content_changed or ai_changed):
            curated_changed_records += 1
        if content_changed and not curated:
            record_failures.append("non-curated trainer was modified")

        strategy = strategies.get(stem)
        if curated:
            if strategy is None:
                record_failures.append("curated trainer lacks a reviewed strategy entry")
            else:
                if strategy["before"] != before_view:
                    record_failures.append("strategy before snapshot differs from baseline")
                if strategy["after"] != current_view:
                    record_failures.append("strategy after snapshot differs from current data")
                if not strategy.get("rationale"):
                    record_failures.append("strategy has no rationale")

        unknown_ai = sorted(set(record["ai_flags"]) - data.ai_ids)
        if unknown_ai:
            record_failures.append(f"unknown AI flags: {unknown_ai}")
        if curated:
            missing_ai = sorted(required_ai_flags(stem, record) - set(record["ai_flags"]))
            if missing_ai:
                record_failures.append(f"missing progression AI flags: {missing_ai}")

        item_layout = {isinstance(member["item"], str) for member in record["party"]}
        if len(item_layout) > 1:
            record_failures.append("mixed held-item archive layout")
        held_count = 0
        for member in record["party"]:
            item = member["item"]
            if isinstance(item, str):
                if item not in data.item_ids:
                    record_failures.append(f"unknown held item {item}")
                held_count += item != "ITEM_NONE"
        if curated and max(member["level"] for member in record["party"]) >= 45 and held_count > 3:
            record_failures.append(f"late major has uniform/excessive held items ({held_count})")
        if record["class"] == "TRAINER_CLASS_RIVAL":
            for slot, member in enumerate(record["party"][:2]):
                if member["item"] not in (None, "ITEM_NONE"):
                    record_failures.append(f"runtime rival slot {slot} must remain itemless")

        synergy_slots = set()
        baseline_support: dict[int, set[str]] = {}
        current_support: dict[int, set[str]] = {}
        identity_keys = ("species", "form", "level", "iv_scale", "ball_seal")
        remaining_baseline_slots = list(range(len(baseline["party_identity"])))
        baseline_slot_for_current = []
        for member in record["party"]:
            member_key = tuple(member[key] for key in identity_keys)
            baseline_slot = next(
                index for index in remaining_baseline_slots
                if tuple(baseline["party_identity"][index][key] for key in identity_keys) == member_key
            )
            remaining_baseline_slots.remove(baseline_slot)
            baseline_slot_for_current.append(baseline_slot)
        runtime_party = [dict(member) for member in record["party"]]
        legacy_starters = {
            "SPECIES_TURTWIG", "SPECIES_GROTLE", "SPECIES_TORTERRA",
            "SPECIES_CHIMCHAR", "SPECIES_MONFERNO", "SPECIES_INFERNAPE",
            "SPECIES_PIPLUP", "SPECIES_PRINPLUP", "SPECIES_EMPOLEON",
        }
        if record["class"] == "TRAINER_CLASS_RIVAL":
            for runtime_slot, runtime_member in enumerate(runtime_party[2:], start=2):
                if runtime_member["species"] in legacy_starters:
                    runtime_member["species"] = (
                        "SPECIES_STARAPTOR" if runtime_member["level"] >= 34 else "SPECIES_STARAVIA"
                    )
                    runtime_member["moves"] = data.engine_default_moves(
                        runtime_member["species"], runtime_member["level"]
                    )
        for slot, member in enumerate(record["party"]):
            baseline_slot = baseline_slot_for_current[slot]
            runtime_member = runtime_party[slot]
            static_moves = member["moves"]
            current_moves = runtime_member["moves"]
            if current_moves is None:
                audited_moves = data.engine_default_moves(runtime_member["species"], runtime_member["level"])
                resolved_level_moves += len(audited_moves)
            elif isinstance(current_moves, list) and 1 <= len(current_moves) <= 4:
                audited_moves = current_moves
            else:
                record_failures.append(f"slot {slot} has invalid move layout")
                continue
            if len(audited_moves) != len(set(audited_moves)):
                record_failures.append(f"slot {slot} has duplicate moves")
            legal = data.legal_moves(runtime_member["species"], runtime_member["level"])
            for move in audited_moves:
                moves_checked += 1
                if move not in data.move_ids or move not in data.move_data:
                    record_failures.append(f"slot {slot} has unknown move {move}")
                    continue
                signature_exception = move in SIGNATURE_MOVE_EXCEPTIONS.get(stem, {}).get(baseline_slot, set())
                if move not in legal and not signature_exception:
                    detail = {"trainer": stem, "slot": slot, "species": runtime_member["species"],
                              "level": runtime_member["level"], "move": move}
                    if curated:
                        record_failures.append(f"slot {slot} cannot learn {move} by level {member['level']}")
                    else:
                        inherited_move_anomalies.append(detail)
                        record_warnings.append(f"inherited baseline move mismatch: slot {slot} {move}")
                elif curated:
                    legal_curated_moves += 1
                if data.move_is_synergy(move, record["party"]):
                    synergy_slots.add(slot)
                    current_support.setdefault(slot, set()).add(move)
                if data.move_data[move]["range"] in ALLY_HIT_RANGES:
                    if not move_safe(move, runtime_party, slot, data):
                        detail = {"trainer": stem, "slot": slot, "move": move}
                        unsafe_spreads.append(detail)
                        if curated:
                            curated_unsafe_spreads += 1
                            record_failures.append(f"slot {slot} {move} has no immune/protecting ordered partner")
                        else:
                            inherited_unsafe_spreads += 1

            before_moves = baseline["party_moves"][baseline_slot]
            if isinstance(before_moves, list):
                for move in before_moves:
                    if move in data.move_data and data.move_is_synergy(move, record["party"]):
                        baseline_support.setdefault(slot, set()).add(move)
            if isinstance(static_moves, list):
                before_set = set(before_moves or [])
                for move in set(static_moves) - before_set:
                    detail = {"trainer": stem, "slot": slot, "species": member["species"],
                              "level": member["level"], "move": move}
                    introduced_moves.append(detail)
                    if move in BANNED_BALANCE_MOVES:
                        record_failures.append(f"introduced doubles-hostile move {move}")
                    if data.move_data[move]["class"] != "CLASS_STATUS":
                        if effective_power(move, data) > POWER_CAPS[tier]:
                            record_failures.append(f"introduced {move} exceeds {tier} power cap")
                        if uses_weaker_stat(move, member["species"], data):
                            record_failures.append(f"introduced {move} uses the clearly weaker offense")

        if curated:
            # Existing legal doubles support is a protected identity field. Exact
            # safety replacements may add roles, but cannot silently discard one.
            for slot, moves in baseline_support.items():
                for move in moves:
                    retained_support_checked += 1
                    if move not in set(record["party"][slot]["moves"]) and not current_support.get(slot):
                        record_failures.append(f"lost existing boss support move {move} from slot {slot}")
            effective_lead = bool(synergy_slots & {0, 1})
            route_201 = stem.startswith("rival_route_201_")
            if record["class"] == "TRAINER_CLASS_RIVAL" and runtime_report["passed"] and not route_201:
                effective_lead = True
            if route_201 and not all(row["has_doubles_control"] for row in runtime_report["route_201_pairs"]):
                record_warnings.append(
                    "Route 201 keeps natural level-up moves; audited pair matrix includes a no-control pairing"
                )
            if effective_lead:
                curated_with_lead_role += 1
            elif not route_201:
                record_failures.append("ordered lead pair has no doubles role")
            protect_count = sum(
                "MOVE_PROTECT" in (member["moves"] or []) or "MOVE_DETECT" in (member["moves"] or [])
                for member in record["party"]
            )
            if protect_count > 3:
                record_failures.append(f"excessive Protect/Detect injection ({protect_count})")

        if record_failures:
            failures.extend(f"{stem}: {message}" for message in record_failures)
        if record_warnings:
            warnings.extend(f"{stem}: {message}" for message in record_warnings)
        summaries.append({
            "trainer": stem, "category": category, "class": record["class"], "curated_major": curated,
            "tier": tier, "party_size": len(record["party"]),
            "content_changed": content_changed, "ai_changed": ai_changed,
            "synergy_slots": sorted(synergy_slots), "held_items": held_count,
            "before": before_view, "after": current_view,
            "rationale": strategy["rationale"] if strategy else [],
            "failures": record_failures, "warnings": record_warnings,
        })

    if len(strategies) != curated_records:
        failures.append(f"strategy manifest has {len(strategies)} entries for {curated_records} curated records")
    if strategy_manifest.get("records_changed") != curated_changed_records:
        failures.append(
            "strategy manifest changed-record count differs from the current curated changes: "
            f"{strategy_manifest.get('records_changed')} != {curated_changed_records}"
        )

    report = {
        "schema": "beacondex-conservative-doubles-trainer-balance-v2",
        "passed": not failures,
        "source_commit": baseline_manifest["source_commit"],
        "policy": {
            "all_records_audited": True,
            "curated_scope": "Gym leaders/rematches, Barry, Galactic commanders/boss, Elite Four/Champion, partner majors",
            "unchanged_baseline_move_mismatches_are_warnings": True,
            "introduced_move_power_caps": POWER_CAPS,
            "ally_hit_spread_safety": "ordered partner has a guaranteed immunity or absorption",
            "runtime_rival_slots_itemless": True,
        },
        "coverage": {
            "trainer_records": len(records), "record_summaries": len(summaries),
            "categories": dict(sorted(categories.items())), "tiers": dict(sorted(tiers.items())),
            "party_sizes": {str(key): value for key, value in sorted(party_sizes.items())},
            "curated_major_records": curated_records, "curated_with_ordered_lead_role": curated_with_lead_role,
            "content_changed_records": content_changed_records,
            "ai_changed_records": ai_changed_records,
            "curated_changed_records": curated_changed_records,
            "moves_checked": moves_checked,
            "resolved_engine_level_moves": resolved_level_moves, "legal_curated_moves": legal_curated_moves,
            "introduced_moves": len(introduced_moves), "baseline_support_moves_checked": retained_support_checked,
            "inherited_unchanged_move_anomalies": len(inherited_move_anomalies),
            "unsafe_spread_moves": len(unsafe_spreads),
            "curated_unsafe_spread_moves": curated_unsafe_spreads,
            "inherited_unchanged_unsafe_spread_moves": inherited_unsafe_spreads,
        },
        "rival_runtime": runtime_report,
        "inherited_move_anomalies": inherited_move_anomalies,
        "unsafe_spreads": unsafe_spreads,
        "introduced_moves": introduced_moves,
        "failures": failures, "warnings": warnings, "records": summaries,
    }
    output = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(output, encoding="utf-8")
    print(output, end="")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
