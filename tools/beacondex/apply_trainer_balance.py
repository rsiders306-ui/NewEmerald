#!/usr/bin/env python3
"""Apply conservative, deterministic doubles tuning to Platinum trainers."""

from __future__ import annotations

import argparse
import copy
import json
import subprocess
from pathlib import Path
from typing import Any

from trainer_balance_common import (
    ALLY_HIT_RANGES, BANNED_BALANCE_MOVES, POWER_CAPS, REPO_ROOT, ROSTER_MANIFEST,
    TRAINER_ROOT, BalanceData, dump_json, held_item_policy, immutable_hash, is_major,
    load_json, ordered_ai_flags, progression_tier, required_ai_flags, trainer_category,
)


STRATEGY_MANIFEST = REPO_ROOT / "data" / "beacondex" / "trainer_balance_strategies.json"

CURATED_CLASS_PARTS = (
    "TRAINER_CLASS_RIVAL", "TRAINER_CLASS_LEADER_", "TRAINER_CLASS_COMMANDER_",
    "TRAINER_CLASS_GALACTIC_BOSS", "TRAINER_CLASS_ELITE_FOUR_",
    "TRAINER_CLASS_CHAMPION_CYNTHIA", "TRAINER_CLASS_TRAINER_",
)


def is_curated_major(stem: str, record: dict[str, Any]) -> bool:
    return trainer_category(stem) == "active" and any(
        part in record["class"] for part in CURATED_CLASS_PARTS
    )

CLASS_ROLE_PLANS = {
    "TRAINER_CLASS_LEADER_ROARK": ((0, "MOVE_SANDSTORM"), (1, "MOVE_ROCK_TOMB")),
    "TRAINER_CLASS_LEADER_GARDENIA": ((0, "MOVE_SUNNY_DAY"), (1, "MOVE_REFLECT")),
    "TRAINER_CLASS_LEADER_FANTINA": ((0, "MOVE_WILL_O_WISP"), (1, "MOVE_ICY_WIND")),
    "TRAINER_CLASS_LEADER_MAYLENE": ((0, "MOVE_FAKE_OUT"), (1, "MOVE_ROCK_SLIDE")),
    "TRAINER_CLASS_LEADER_WAKE": ((0, "MOVE_RAIN_DANCE"), (1, "MOVE_ICY_WIND")),
    "TRAINER_CLASS_LEADER_BYRON": ((0, "MOVE_SANDSTORM"), (1, "MOVE_ROCK_SLIDE")),
    "TRAINER_CLASS_LEADER_CANDICE": (),
    "TRAINER_CLASS_LEADER_VOLKNER": ((0, "MOVE_LIGHT_SCREEN"), (1, "MOVE_FAKE_OUT")),
    "TRAINER_CLASS_ELITE_FOUR_AARON": ((1, "MOVE_LIGHT_SCREEN"),),
    "TRAINER_CLASS_ELITE_FOUR_BERTHA": ((1, "MOVE_ROCK_SLIDE"),),
    "TRAINER_CLASS_ELITE_FOUR_FLINT": ((0, "MOVE_SUNNY_DAY"), (1, "MOVE_HELPING_HAND")),
    "TRAINER_CLASS_ELITE_FOUR_LUCIAN": ((0, "MOVE_LIGHT_SCREEN"), (1, "MOVE_HELPING_HAND"), (2, "MOVE_TRICK_ROOM")),
    "TRAINER_CLASS_CHAMPION_CYNTHIA": ((0, "MOVE_ICY_WIND"), (4, "MOVE_FOLLOW_ME")),
}

ROSTER_ORDERS = {
    "elite_four_bertha": ["SPECIES_HIPPOWDON", "SPECIES_GLISCOR", "SPECIES_WHISCASH",
                           "SPECIES_MEADOWMIRA", "SPECIES_GOLEM", "SPECIES_RHYPERIOR"],
    "elite_four_bertha_rematch": ["SPECIES_HIPPOWDON", "SPECIES_GLISCOR", "SPECIES_WHISCASH",
                                   "SPECIES_GOLEM", "SPECIES_RHYPERIOR"],
    "elite_four_lucian": ["SPECIES_MR_MIME", "SPECIES_ESPEON", "SPECIES_BRONZONG",
                           "SPECIES_GALLADE", "SPECIES_ALAKAZAM", "SPECIES_SERMEDIC"],
    "elite_four_lucian_rematch": ["SPECIES_MR_MIME", "SPECIES_ESPEON", "SPECIES_BRONZONG",
                                   "SPECIES_GALLADE", "SPECIES_ALAKAZAM"],
    "champion_cynthia": ["SPECIES_SPIRITOMB", "SPECIES_ROSERADE", "SPECIES_MILOTIC",
                          "SPECIES_LUCARIO", "SPECIES_TOGEKISS", "SPECIES_GARCHOMP"],
    "champion_cynthia_rematch": ["SPECIES_SPIRITOMB", "SPECIES_ROSERADE", "SPECIES_MILOTIC",
                                  "SPECIES_LUCARIO", "SPECIES_TOGEKISS", "SPECIES_GARCHOMP"],
}

SIGNATURE_MOVE_EXCEPTIONS = {
    "elite_four_aaron": {0: {"MOVE_AIR_SLASH", "MOVE_BUG_BUZZ"}, 3: {"MOVE_MEGAHORN"}},
}

EXACT_MEMBER_MOVESETS = {
    "cheryl_eterna_forest": {
        0: ["MOVE_SOFTBOILED", "MOVE_REFRESH", "MOVE_HELPING_HAND", "MOVE_ICY_WIND"],
    },
    "leader_fantina": {
        1: ["MOVE_SHADOW_BALL", "MOVE_SUCKER_PUNCH", "MOVE_HYPNOSIS", "MOVE_ICY_WIND"],
    },
    "leader_roark_rematch": {
        2: ["MOVE_STONE_EDGE", "MOVE_BRICK_BREAK", "MOVE_FIRE_PUNCH", "MOVE_ROCK_SLIDE"],
    },
    "leader_wake": {
        0: ["MOVE_WATERFALL", "MOVE_ICE_FANG", "MOVE_BITE", "MOVE_RAIN_DANCE"],
    },
    "elite_four_bertha": {
        0: ["MOVE_EARTHQUAKE", "MOVE_STONE_EDGE", "MOVE_CRUNCH", "MOVE_YAWN"],
        1: ["MOVE_ICE_FANG", "MOVE_FIRE_FANG", "MOVE_THUNDER_FANG", "MOVE_ROCK_SLIDE"],
        2: ["MOVE_EARTH_POWER", "MOVE_AQUA_TAIL", "MOVE_ZEN_HEADBUTT", "MOVE_SANDSTORM"],
        3: ["MOVE_EARTH_POWER", "MOVE_DAZZLING_GLEAM", "MOVE_HELPING_HAND", "MOVE_HEALING_WISH"],
        4: ["MOVE_ROCK_SLIDE", "MOVE_FIRE_PUNCH", "MOVE_THUNDER_PUNCH", "MOVE_SANDSTORM"],
        5: ["MOVE_STONE_EDGE", "MOVE_ROCK_SLIDE", "MOVE_AVALANCHE", "MOVE_HAMMER_ARM"],
    },
    "elite_four_flint": {
        1: ["MOVE_FIRE_FANG", "MOVE_SUPERPOWER", "MOVE_HELPING_HAND", "MOVE_WILL_O_WISP"],
        2: ["MOVE_FLARE_BLITZ", "MOVE_MEGAHORN", "MOVE_POISON_JAB", "MOVE_SUNNY_DAY"],
        4: ["MOVE_FLAMETHROWER", "MOVE_THUNDERBOLT", "MOVE_FOCUS_BLAST", "MOVE_HEAT_WAVE"],
    },
    "elite_four_lucian": {
        1: ["MOVE_PSYCHIC", "MOVE_SHADOW_BALL", "MOVE_HELPING_HAND", "MOVE_SIGNAL_BEAM"],
        2: ["MOVE_PSYCHIC", "MOVE_GYRO_BALL", "MOVE_TRICK_ROOM", "MOVE_CALM_MIND"],
    },
    "leader_candice": {
        0: ["MOVE_SLASH", "MOVE_AERIAL_ACE", "MOVE_PROTECT", "MOVE_ICE_SHARD"],
        1: ["MOVE_AVALANCHE", "MOVE_STONE_EDGE", "MOVE_ICY_WIND", "MOVE_HAIL"],
    },
    "leader_candice_rematch": {
        0: ["MOVE_AVALANCHE", "MOVE_SLASH", "MOVE_PROTECT", "MOVE_TAUNT"],
        1: ["MOVE_AVALANCHE", "MOVE_ROCK_SLIDE", "MOVE_ICY_WIND", "MOVE_HAIL"],
    },
    "champion_cynthia": {
        2: ["MOVE_HYDRO_PUMP", "MOVE_ICE_BEAM", "MOVE_DRAGON_PULSE", "MOVE_AQUA_RING"],
        4: ["MOVE_AIR_SLASH", "MOVE_AURA_SPHERE", "MOVE_FOLLOW_ME", "MOVE_THUNDER_WAVE"],
        5: ["MOVE_DRAGON_RUSH", "MOVE_EARTHQUAKE", "MOVE_ROCK_SLIDE", "MOVE_FIRE_FANG"],
    },
    "champion_cynthia_rematch": {
        2: ["MOVE_HYDRO_PUMP", "MOVE_ICE_BEAM", "MOVE_DRAGON_PULSE", "MOVE_AQUA_RING"],
        4: ["MOVE_AIR_SLASH", "MOVE_AURA_SPHERE", "MOVE_FOLLOW_ME", "MOVE_THUNDER_WAVE"],
        5: ["MOVE_DRAGON_RUSH", "MOVE_EARTHQUAKE", "MOVE_ROCK_SLIDE", "MOVE_FIRE_FANG"],
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="write the reviewed balance changes")
    parser.add_argument("--initialize-rosters", action="store_true", help="capture the untouched baseline")
    return parser.parse_args()


def trainer_records() -> list[tuple[Path, dict[str, Any]]]:
    return [(path, load_json(path)) for path in sorted(TRAINER_ROOT.glob("*.json"))]


def initialize_rosters(records: list[tuple[Path, dict[str, Any]]]) -> None:
    if ROSTER_MANIFEST.exists():
        raise SystemExit(f"refusing to replace existing baseline: {ROSTER_MANIFEST}")
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, check=True, text=True, capture_output=True
    ).stdout.strip()
    manifest = {
        "schema": "beacondex-trainer-balance-baseline-v2", "source_commit": commit,
        "immutable_fields": ["name", "class", "trainer bag items", "double_battle", "messages",
                             "party species/form/level/iv_scale/ball_seal"], "records": {},
    }
    for path, record in records:
        manifest["records"][path.stem] = {
            "immutable_hash": immutable_hash(record), "ai_flags": record["ai_flags"],
            "party_moves": [member["moves"] for member in record["party"]],
            "party_items": [member["item"] for member in record["party"]],
            "party_identity": [
                {key: member[key] for key in ("species", "form", "level", "iv_scale", "ball_seal")}
                for member in record["party"]
            ],
        }
    dump_json(ROSTER_MANIFEST, manifest)


def effective_power(move: str, data: BalanceData) -> int:
    power = data.move_data[move]["power"]
    if power == 1:
        return 65
    if power == 0 and data.move_data[move]["class"] != "CLASS_STATUS":
        return 40
    return power


def uses_weaker_stat(move: str, species: str, data: BalanceData) -> bool:
    move_data = data.move_data[move]
    if move_data["class"] == "CLASS_STATUS" or effective_power(move, data) < 70:
        return False
    stats = data.species_data[species]["base_stats"]
    used = stats["attack"] if move_data["class"] == "CLASS_PHYSICAL" else stats["special_attack"]
    other = stats["special_attack"] if move_data["class"] == "CLASS_PHYSICAL" else stats["attack"]
    return used + 25 < other


def move_safe(move: str, party: list[dict[str, Any]], slot: int, data: BalanceData) -> bool:
    if move not in data.move_data:
        return False
    if data.move_data[move]["range"] not in ALLY_HIT_RANGES:
        return True
    partner = data.paired_partner(party, slot)
    if partner is None:
        return False
    return data.partner_is_safe(move, partner["species"])


def baseline_moves_for_member(member: dict[str, Any], data: BalanceData) -> list[str]:
    if isinstance(member["moves"], list):
        return list(member["moves"])
    return data.natural_moves(member["species"], member["level"])[-4:]


def replacement_candidates(member: dict[str, Any], party: list[dict[str, Any]], slot: int, data: BalanceData) -> list[str]:
    legal = data.legal_moves(member["species"], member["level"])
    natural = set(data.natural_moves(member["species"], member["level"]))
    level = member["level"]
    cap = 60 if level <= 15 else (80 if level <= 29 else (100 if level <= 44 else 120))
    candidates = []
    for move in legal:
        if move in BANNED_BALANCE_MOVES or not move_safe(move, party, slot, data):
            continue
        move_data = data.move_data[move]
        if move_data["class"] != "CLASS_STATUS" and effective_power(move, data) > cap:
            continue
        if uses_weaker_stat(move, member["species"], data):
            continue
        candidates.append(move)
    def quality(move: str) -> tuple[int, int, int, int, str]:
        move_data = data.move_data[move]
        damaging = move_data["class"] != "CLASS_STATUS"
        return (
            int(damaging), int(move_data["type"] in data.types(member["species"])),
            effective_power(move, data) if damaging else 0, int(move in natural), move,
        )
    return sorted(candidates, key=quality, reverse=True)


def repair_moves(member: dict[str, Any], party: list[dict[str, Any]], slot: int, data: BalanceData,
                 remove_gimmicks: bool = False, signature_moves: set[str] | None = None) -> tuple[list[str], list[str]]:
    species, level = member["species"], member["level"]
    legal, original = data.legal_moves(species, level), baseline_moves_for_member(member, data)
    kept, rationale = [], []
    signature_moves = signature_moves or set()
    for move in original:
        if remove_gimmicks and move in BANNED_BALANCE_MOVES:
            rationale.append(f"removed doubles-hostile {move}")
        elif move in signature_moves and move_safe(move, party, slot, data):
            kept.append(move)
        elif move in legal and move_safe(move, party, slot, data) and move not in kept:
            kept.append(move)
        elif move not in legal:
            rationale.append(f"replaced illegal {move}")
        else:
            rationale.append(f"replaced partner-unsafe {move}")
    target = min(4, max(1, len(original)))
    if len(kept) < target:
        for move in replacement_candidates(member, party, slot, data):
            if move not in kept:
                kept.append(move)
            if len(kept) >= target:
                break
    if not kept:
        raise ValueError(f"no legal move for {species} at level {level}")
    return kept[:4], rationale


def strategy_candidates(record: dict[str, Any], slot: int, data: BalanceData, used: set[str]) -> list[str]:
    member, party = record["party"][slot], record["party"]
    cap = POWER_CAPS[progression_tier(record)]
    candidates = []
    for move in sorted(data.legal_moves(member["species"], member["level"])):
        if move in used or move in BANNED_BALANCE_MOVES or not move_safe(move, party, slot, data):
            continue
        if not data.move_is_synergy(move, party):
            continue
        move_data = data.move_data[move]
        if move_data["class"] != "CLASS_STATUS" and effective_power(move, data) > cap:
            continue
        if uses_weaker_stat(move, member["species"], data):
            continue
        candidates.append(move)
    return sorted(candidates, key=lambda move: (-data.synergy_score(move, party),
                                                -int(data.move_data[move]["type"] in data.types(member["species"])), move))


def least_important_slot(moves: list[str], member: dict[str, Any], party: list[dict[str, Any]], data: BalanceData) -> int:
    scores = []
    for index, move in enumerate(moves):
        move_data = data.move_data[move]
        if data.move_is_synergy(move, party):
            score = 10000
        elif move_data["class"] == "CLASS_STATUS":
            score = 0
        else:
            score = effective_power(move, data)
            if move_data["type"] in data.types(member["species"]):
                score += 100
            if uses_weaker_stat(move, member["species"], data):
                score -= 50
        scores.append((score, -index, index))
    return min(scores)[2]


def add_strategy_move(record: dict[str, Any], slot: int, move: str, data: BalanceData) -> str:
    member, party, moves = record["party"][slot], record["party"], record["party"][slot]["moves"]
    if move in moves:
        return f"preserved {move}"
    if len(moves) < 4:
        moves.append(move)
        return f"added {move}"
    replace_slot = least_important_slot(moves, member, party, data)
    replaced, moves[replace_slot] = moves[replace_slot], move
    return f"replaced low-role {replaced} with {move}"


def apply_class_plan(record: dict[str, Any], data: BalanceData) -> tuple[list[str], set[int]]:
    rationale, slots = [], set()
    for slot, move in CLASS_ROLE_PLANS.get(record["class"], ()):
        if slot >= len(record["party"]):
            continue
        member = record["party"][slot]
        if move not in data.legal_moves(member["species"], member["level"]):
            continue
        if move in BANNED_BALANCE_MOVES or not move_safe(move, record["party"], slot, data):
            continue
        move_data = data.move_data[move]
        cap = POWER_CAPS[progression_tier(record)]
        if move_data["class"] != "CLASS_STATUS" and effective_power(move, data) > cap:
            continue
        rationale.append(f"reviewed role slot {slot}: {add_strategy_move(record, slot, move, data)}")
        slots.add(slot)
    return rationale, slots


def apply_exact_movesets(stem: str, record: dict[str, Any], data: BalanceData) -> list[str]:
    rationale = []
    for slot, moves in EXACT_MEMBER_MOVESETS.get(stem, {}).items():
        member = record["party"][slot]
        legal = data.legal_moves(member["species"], member["level"])
        if not set(moves) <= legal:
            raise ValueError(f"reviewed {stem} slot {slot} has illegal moves: {sorted(set(moves) - legal)}")
        member["moves"] = list(moves)
    for slot, moves in EXACT_MEMBER_MOVESETS.get(stem, {}).items():
        if not all(move_safe(move, record["party"], slot, data) for move in moves):
            raise ValueError(f"reviewed {stem} slot {slot} has an unsafe spread move")
        rationale.append(f"reviewed exact role for slot {slot}: {', '.join(moves)}")
    return rationale


def tune_major(stem: str, record: dict[str, Any], data: BalanceData) -> list[str]:
    if record["class"] == "TRAINER_CLASS_RIVAL":
        return ["runtime selected lead receives family-specific legal doubles support"]
    rationale = apply_exact_movesets(stem, record, data)
    rationale.extend(apply_class_plan(record, data)[0])
    party = record["party"]
    used = {move for member in party for move in member["moves"]}
    synergy_slots = {slot for slot, member in enumerate(party)
                     if any(data.move_is_synergy(move, party) for move in member["moves"])}
    order = list(range(min(2, len(party)))) + list(range(2, len(party)))
    if any(slot < 2 for slot in synergy_slots):
        if not rationale:
            slot = min(slot for slot in synergy_slots if slot < 2)
            existing = next(move for move in party[slot]["moves"] if data.move_is_synergy(move, party))
            rationale.append(f"ordered lead pair preserves {existing} on slot {slot}")
        return rationale
    for slot in order:
        if slot < 2 and slot in synergy_slots:
            existing = next(move for move in party[slot]["moves"] if data.move_is_synergy(move, party))
            rationale.append(f"lead {slot} preserves {existing}")
            continue
        if any(value < 2 for value in synergy_slots):
            break
        candidates = strategy_candidates(record, slot, data, used)
        if not candidates:
            continue
        move = candidates[0]
        rationale.append(f"slot {slot}: {add_strategy_move(record, slot, move, data)}")
        used.add(move)
        synergy_slots.add(slot)
    if not rationale:
        rationale.append("existing ordered-pair support and spread roles retained")
    return rationale


def restore_baseline(record: dict[str, Any], baseline: dict[str, Any]) -> None:
    identity_keys = ("species", "form", "level", "iv_scale", "ball_seal")
    remaining = list(record["party"])
    restored = []
    for identity in baseline["party_identity"]:
        key = tuple(identity[field] for field in identity_keys)
        index = next(
            i for i, member in enumerate(remaining)
            if tuple(member[field] for field in identity_keys) == key
        )
        restored.append(remaining.pop(index))
    record["party"] = restored
    record["ai_flags"] = copy.deepcopy(baseline["ai_flags"])
    for member, moves, item in zip(record["party"], baseline["party_moves"], baseline["party_items"]):
        member["moves"], member["item"] = copy.deepcopy(moves), item


def reorder_party(stem: str, record: dict[str, Any]) -> list[str]:
    order = ROSTER_ORDERS.get(stem)
    if order is None:
        return []
    members = {member["species"]: member for member in record["party"]}
    if set(members) != set(order):
        raise ValueError(f"reviewed roster order does not match {stem}")
    record["party"] = [members[species] for species in order]
    return [f"reviewed safe pair order: {', '.join(order)}"]


def tune_rival(record: dict[str, Any]) -> list[str]:
    rationale = ["runtime slots 0/1 retain generated level-up moves and remain itemless"]
    for slot, member in enumerate(record["party"]):
        if not isinstance(member["moves"], list) or "MOVE_GIGA_IMPACT" not in member["moves"]:
            continue
        member["moves"] = ["MOVE_BODY_SLAM" if move == "MOVE_GIGA_IMPACT" else move for move in member["moves"]]
        rationale.append(f"slot {slot}: replaced recharge MOVE_GIGA_IMPACT with MOVE_BODY_SLAM")
    return rationale


def process_record(path: Path, record: dict[str, Any], baseline: dict[str, Any], data: BalanceData) -> tuple[bool, dict[str, Any] | None]:
    stem = path.stem
    restore_baseline(record, baseline)
    if trainer_category(stem) == "sentinel":
        return False, None
    before, major, repair_notes, repaired = copy.deepcopy(record), is_curated_major(stem, record), [], []
    if not major:
        return False, None
    rationale = reorder_party(stem, record)
    if record["class"] == "TRAINER_CLASS_RIVAL":
        rationale.extend(tune_rival(record))
        record["ai_flags"] = ordered_ai_flags(set(record["ai_flags"]) | required_ai_flags(stem, record))
        changed = before != record
        if changed:
            dump_json(path, record)
        return changed, {
            "trainer": stem, "major": True, "tier": progression_tier(record),
            "ordered_lead": [member["species"] for member in record["party"][:2]],
            "rationale": rationale,
            "before": {"ai_flags": before["ai_flags"], "moves": [m["moves"] for m in before["party"]],
                       "items": [m["item"] for m in before["party"]],
                       "roster": [m["species"] for m in before["party"]]},
            "after": {"ai_flags": record["ai_flags"], "moves": [m["moves"] for m in record["party"]],
                      "items": [m["item"] for m in record["party"]],
                      "roster": [m["species"] for m in record["party"]]},
        }
    for slot, member in enumerate(record["party"]):
        moves, notes = repair_moves(
            member, record["party"], slot, data, remove_gimmicks=True,
            signature_moves=SIGNATURE_MOVE_EXCEPTIONS.get(stem, {}).get(slot, set()),
        )
        repaired.append(moves)
        repair_notes.extend(f"slot {slot}: {note}" for note in notes)
    if major or any(isinstance(member["moves"], list) for member in record["party"]):
        for member, moves in zip(record["party"], repaired):
            member["moves"] = moves
    rationale.extend(repair_notes)
    if major:
        rationale.extend(tune_major(stem, record, data))
        record["ai_flags"] = ordered_ai_flags(set(record["ai_flags"]) | required_ai_flags(stem, record))
        for member, item in zip(record["party"], held_item_policy(stem, record)):
            member["item"] = item
        if record["class"] == "TRAINER_CLASS_RIVAL":
            for member in record["party"][:2]:
                member["item"] = "ITEM_NONE" if isinstance(member["item"], str) else None
    changed = before != record
    if changed:
        dump_json(path, record)
    strategy = {
        "trainer": stem, "major": major, "tier": progression_tier(record),
        "ordered_lead": [member["species"] for member in record["party"][:2]],
        "rationale": rationale or ["preserved existing legal team"],
        "before": {"ai_flags": before["ai_flags"], "moves": [m["moves"] for m in before["party"]],
                   "items": [m["item"] for m in before["party"]],
                   "roster": [m["species"] for m in before["party"]]},
        "after": {"ai_flags": record["ai_flags"], "moves": [m["moves"] for m in record["party"]],
                  "items": [m["item"] for m in record["party"]],
                  "roster": [m["species"] for m in record["party"]]},
    }
    return changed, strategy


def main() -> int:
    args, records = parse_args(), trainer_records()
    if args.initialize_rosters:
        initialize_rosters(records)
    if not args.apply:
        print(f"loaded {len(records)} records; pass --apply to write reviewed tuning")
        return 0
    if not ROSTER_MANIFEST.exists():
        raise SystemExit("initialize the untouched baseline before applying")
    manifest, data, changed, strategies = load_json(ROSTER_MANIFEST), BalanceData(), 0, []
    for path, record in records:
        baseline = manifest["records"][path.stem]
        if baseline["immutable_hash"] != immutable_hash(record):
            raise SystemExit(f"immutable roster/story data changed: {path.stem}")
        did_change, strategy = process_record(path, record, baseline, data)
        changed += did_change
        if strategy is not None:
            strategies.append(strategy)
    dump_json(STRATEGY_MANIFEST, {"schema": "beacondex-reviewed-trainer-strategies-v1",
                                  "source_commit": manifest["source_commit"],
                                  "records_changed": changed, "strategies": strategies})
    print(json.dumps({"trainer_records_audited": len(records), "records_changed": changed,
                      "strategies": len(strategies)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
