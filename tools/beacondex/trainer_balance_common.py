#!/usr/bin/env python3
"""Shared deterministic policy and data access for trainer balance."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[2]
TRAINER_ROOT = REPO_ROOT / "res" / "trainers" / "data"
ROSTER_MANIFEST = REPO_ROOT / "data" / "beacondex" / "trainer_balance_rosters.json"

MAJOR_CLASS_PARTS = (
    "TRAINER_CLASS_RIVAL", "TRAINER_CLASS_LEADER_", "TRAINER_CLASS_ELITE_FOUR_",
    "TRAINER_CLASS_CHAMPION_", "TRAINER_CLASS_COMMANDER_", "TRAINER_CLASS_GALACTIC_BOSS",
    "TRAINER_CLASS_TRAINER_", "TRAINER_CLASS_TOWER_TYCOON", "TRAINER_CLASS_FACTORY_HEAD",
    "TRAINER_CLASS_ARCADE_STAR", "TRAINER_CLASS_CASTLE_VALET", "TRAINER_CLASS_HALL_MATRON",
)
SKILLED_CLASS_PARTS = (
    "ACE_TRAINER", "VETERAN", "DRAGON_TAMER", "GALACTIC_", "BLACK_BELT", "PSYCHIC_",
)
AI_ORDER = (
    "AI_FLAG_BASIC", "AI_FLAG_EVAL_ATTACK", "AI_FLAG_EXPERT", "AI_FLAG_SETUP_FIRST_TURN",
    "AI_FLAG_RISKY", "AI_FLAG_PRIORITIZE_DAMAGE", "AI_FLAG_PRIORITIZE_EXTREMES",
    "AI_FLAG_BATON_PASS", "AI_FLAG_TAG_STRATEGY", "AI_FLAG_CHECK_HP", "AI_FLAG_WEATHER",
    "AI_FLAG_HARRASSMENT",
)
ALLY_HIT_RANGES = {"RANGE_ALL_ADJACENT"}
OPPONENT_SPREAD_RANGE = "RANGE_ADJACENT_OPPONENTS"

# Protect is intentionally absent. Ally-hitting attacks are admitted only when
# their ordered partner has a natural immunity, so generic Protect is unnecessary.
DOUBLES_SUPPORT = {
    "MOVE_HELPING_HAND": 130, "MOVE_FOLLOW_ME": 125, "MOVE_FAKE_OUT": 120,
    "MOVE_TAILWIND": 118, "MOVE_TRICK_ROOM": 116, "MOVE_REFLECT": 112,
    "MOVE_LIGHT_SCREEN": 112, "MOVE_ICY_WIND": 110, "MOVE_MUDDY_WATER": 108,
    "MOVE_ROCK_SLIDE": 108, "MOVE_HEAT_WAVE": 108, "MOVE_BLIZZARD": 106,
    "MOVE_SAFEGUARD": 105, "MOVE_HYPER_VOICE": 104, "MOVE_AIR_CUTTER": 102,
    "MOVE_RAZOR_LEAF": 100, "MOVE_SWIFT": 98, "MOVE_THUNDER_WAVE": 94,
    "MOVE_WILL_O_WISP": 94, "MOVE_TAUNT": 92, "MOVE_ENCORE": 92,
    "MOVE_RAIN_DANCE": 90, "MOVE_SUNNY_DAY": 90, "MOVE_SANDSTORM": 90,
    "MOVE_HAIL": 90, "MOVE_GROWL": 82, "MOVE_LEER": 82, "MOVE_TAIL_WHIP": 82,
    "MOVE_STRING_SHOT": 82, "MOVE_SAND_ATTACK": 80, "MOVE_SWEET_SCENT": 80,
}
WEATHER_TYPES = {
    "MOVE_RAIN_DANCE": {"TYPE_WATER", "TYPE_ELECTRIC"},
    "MOVE_SUNNY_DAY": {"TYPE_FIRE", "TYPE_GRASS"},
    "MOVE_SANDSTORM": {"TYPE_ROCK", "TYPE_GROUND", "TYPE_STEEL"},
    "MOVE_HAIL": {"TYPE_ICE"},
}
BANNED_BALANCE_MOVES = {
    "MOVE_NONE", "MOVE_SELFDESTRUCT", "MOVE_EXPLOSION", "MOVE_MEMENTO", "MOVE_PERISH_SONG",
    "MOVE_FISSURE", "MOVE_GUILLOTINE", "MOVE_HORN_DRILL", "MOVE_SHEER_COLD",
    "MOVE_HYPER_BEAM", "MOVE_GIGA_IMPACT", "MOVE_FOCUS_PUNCH", "MOVE_SKY_ATTACK",
    "MOVE_LAST_RESORT", "MOVE_RAZOR_WIND", "MOVE_SOLAR_BEAM", "MOVE_FLY", "MOVE_DIG",
    "MOVE_DIVE", "MOVE_BOUNCE", "MOVE_SKULL_BASH",
}
RIVAL_STARTER_FAMILIES = (
    "SPECIES_GLIMBARK", "SPECIES_WARDMANE", "SPECIES_SIDERION",
    "SPECIES_CALFLANK", "SPECIES_GRIDIRUFF", "SPECIES_OXGUARD",
    "SPECIES_ZEPHYLET", "SPECIES_GALECREST", "SPECIES_TERRAPTOR",
    "SPECIES_TURTWIG", "SPECIES_GROTLE", "SPECIES_TORTERRA",
    "SPECIES_CHIMCHAR", "SPECIES_MONFERNO", "SPECIES_INFERNAPE",
    "SPECIES_PIPLUP", "SPECIES_PRINPLUP", "SPECIES_EMPOLEON",
)
RIVAL_FAMILY_SUPPORT = {
    "SPECIES_GLIMBARK": "MOVE_HELPING_HAND", "SPECIES_WARDMANE": "MOVE_HELPING_HAND",
    "SPECIES_SIDERION": "MOVE_HELPING_HAND", "SPECIES_CALFLANK": "MOVE_ROCK_TOMB",
    "SPECIES_GRIDIRUFF": "MOVE_ROCK_TOMB", "SPECIES_OXGUARD": "MOVE_ROCK_TOMB",
    "SPECIES_ZEPHYLET": "MOVE_SAND_ATTACK", "SPECIES_GALECREST": "MOVE_SAND_ATTACK",
    "SPECIES_TERRAPTOR": "MOVE_SAND_ATTACK", "SPECIES_TURTWIG": "MOVE_RAZOR_LEAF",
    "SPECIES_GROTLE": "MOVE_RAZOR_LEAF", "SPECIES_TORTERRA": "MOVE_RAZOR_LEAF",
    "SPECIES_CHIMCHAR": "MOVE_LEER", "SPECIES_MONFERNO": "MOVE_LEER",
    "SPECIES_INFERNAPE": "MOVE_LEER", "SPECIES_PIPLUP": "MOVE_GROWL",
    "SPECIES_PRINPLUP": "MOVE_GROWL", "SPECIES_EMPOLEON": "MOVE_GROWL",
}

POWER_CAPS = {"early": 60, "developing": 80, "midgame": 100, "endgame": 120}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=4) + "\n", encoding="utf-8")


def trainer_category(stem: str) -> str:
    if stem == "none":
        return "sentinel"
    if "dummy" in stem:
        return "dummy"
    if "unused" in stem:
        return "unused"
    return "active"


def is_major(stem: str, record: dict[str, Any]) -> bool:
    return trainer_category(stem) == "active" and any(
        part in record["class"] for part in MAJOR_CLASS_PARTS
    )


def is_skilled(record: dict[str, Any]) -> bool:
    return any(part in record["class"] for part in SKILLED_CLASS_PARTS)


def max_level(record: dict[str, Any]) -> int:
    return max((member["level"] for member in record["party"]), default=0)


def progression_tier(record: dict[str, Any]) -> str:
    level = max_level(record)
    if level <= 15:
        return "early"
    if level <= 29:
        return "developing"
    if level <= 44:
        return "midgame"
    return "endgame"


def required_ai_flags(stem: str, record: dict[str, Any]) -> set[str]:
    if trainer_category(stem) == "sentinel":
        return set()
    level, major = max_level(record), is_major(stem, record)
    required = {"AI_FLAG_BASIC"}
    if level >= 20 or major:
        required.add("AI_FLAG_EVAL_ATTACK")
    if level >= 35 or (major and level >= 12) or (is_skilled(record) and level >= 25):
        required.add("AI_FLAG_EXPERT")
    if major and level >= 45:
        required.add("AI_FLAG_CHECK_HP")
    return required


def ordered_ai_flags(flags: Iterable[str]) -> list[str]:
    flags = set(flags)
    return [flag for flag in AI_ORDER if flag in flags] + sorted(flags - set(AI_ORDER))


def immutable_payload(record: dict[str, Any]) -> dict[str, Any]:
    roster = [
        {key: member[key] for key in ("species", "form", "level", "iv_scale", "ball_seal")}
        for member in record["party"]
    ]
    return {
        "name": record["name"], "class": record["class"], "bag_items": record["items"],
        "double_battle": record["double_battle"], "messages": record["messages"],
        "roster": sorted(roster, key=lambda member: json.dumps(member, sort_keys=True)),
    }


def immutable_hash(record: dict[str, Any]) -> str:
    raw = json.dumps(immutable_payload(record), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


class BalanceData:
    def __init__(self, repo: Path = REPO_ROOT) -> None:
        self.repo = repo
        self.move_data = {
            "MOVE_" + path.parent.name.upper(): load_json(path)
            for path in sorted((repo / "res" / "moves").glob("*/data.json"))
        }
        self.item_ids = set((repo / "generated" / "items.txt").read_text().splitlines())
        self.move_ids = set((repo / "generated" / "moves.txt").read_text().splitlines())
        self.ai_ids = set((repo / "generated" / "ai_flags.txt").read_text().splitlines())
        self.tm_moves = {}
        for path in sorted((repo / "res" / "items" / "data").glob("[th]m*.json")):
            self.tm_moves[path.stem.upper()] = load_json(path)["teachesMove"]
        self.species_data, self.species_paths = {}, {}
        for path in sorted((repo / "res" / "pokemon").glob("*/data.json")):
            species = "SPECIES_" + path.parent.name.upper()
            self.species_data[species], self.species_paths[species] = load_json(path), path
        self.parents: dict[str, set[str]] = defaultdict(set)
        for species, data in self.species_data.items():
            for evolution in data.get("evolutions", []):
                target = evolution[-1]
                if isinstance(target, str) and target.startswith("SPECIES_"):
                    self.parents[target].add(species)

    def ancestors(self, species: str) -> list[str]:
        distances, queue = {species: 0}, deque([species])
        while queue:
            current = queue.popleft()
            for parent in self.parents.get(current, ()):
                if parent not in distances:
                    distances[parent] = distances[current] + 1
                    queue.append(parent)
        return sorted(distances, key=lambda value: (-distances[value], value))

    def natural_moves(self, species: str, level: int) -> list[str]:
        ordered = []
        for ancestor in self.ancestors(species):
            for move_level, move in self.species_data[ancestor]["learnset"].get("by_level", []):
                if move_level <= level:
                    if move in ordered:
                        ordered.remove(move)
                    ordered.append(move)
        return ordered

    def engine_default_moves(self, species: str, level: int) -> list[str]:
        """Mirror BoxPokemon_SetDefaultMoves for a freshly initialized mon."""
        moves: list[str] = []
        for move_level, move in self.species_data[species]["learnset"].get("by_level", []):
            if move_level > level:
                break
            if move in moves:
                continue
            if len(moves) == 4:
                moves.pop(0)
            moves.append(move)
        return moves

    def legal_moves(self, species: str, level: int) -> set[str]:
        if species == "SPECIES_SMEARGLE":
            return self.move_ids - BANNED_BALANCE_MOVES
        legal = set(self.natural_moves(species, level))
        for ancestor in self.ancestors(species):
            learnset = self.species_data[ancestor]["learnset"]
            legal.update(self.tm_moves[item] for item in learnset.get("by_tm", []) if item in self.tm_moves)
            legal.update(learnset.get("by_tutor", []))
            legal.update(learnset.get("egg_moves", []))
        return legal - {"MOVE_NONE"}

    def types(self, species: str) -> set[str]:
        return set(self.species_data[species]["types"])

    def abilities(self, species: str) -> set[str]:
        return set(self.species_data[species]["abilities"])

    def weather_matches(self, move: str, party: list[dict[str, Any]]) -> bool:
        relevant = WEATHER_TYPES.get(move)
        if relevant is None:
            return True
        matches = sum(bool(self.types(member["species"]) & relevant) for member in party)
        return matches >= max(2, (len(party) + 1) // 2)

    def partner_is_safe(self, move: str, partner_species: str) -> bool:
        move_type = self.move_data[move]["type"]
        types, abilities = self.types(partner_species), self.abilities(partner_species)
        if move_type == "TYPE_GROUND":
            return "TYPE_FLYING" in types or "ABILITY_LEVITATE" in abilities
        if move_type == "TYPE_ELECTRIC":
            return "TYPE_GROUND" in types or bool(abilities & {"ABILITY_VOLT_ABSORB", "ABILITY_MOTOR_DRIVE"})
        if move_type == "TYPE_WATER":
            return bool(abilities & {"ABILITY_WATER_ABSORB", "ABILITY_DRY_SKIN"})
        if move_type == "TYPE_FIRE":
            return "ABILITY_FLASH_FIRE" in abilities
        if move_type == "TYPE_NORMAL":
            return "TYPE_GHOST" in types
        return False

    @staticmethod
    def paired_partner(party: list[dict[str, Any]], slot: int) -> dict[str, Any] | None:
        partner_slot = slot - 1 if slot % 2 else slot + 1
        return party[partner_slot] if 0 <= partner_slot < len(party) else None

    def move_is_synergy(self, move: str, party: list[dict[str, Any]]) -> bool:
        data = self.move_data[move]
        if data["range"] == OPPONENT_SPREAD_RANGE:
            return True
        if move in DOUBLES_SUPPORT and self.weather_matches(move, party):
            return True
        return data["range"] in {"RANGE_ALLY", "RANGE_USER_SIDE", "RANGE_USER_OR_ALLY", "RANGE_FIELD"}

    def synergy_score(self, move: str, party: list[dict[str, Any]]) -> int:
        if not self.move_is_synergy(move, party):
            return -1
        data = self.move_data[move]
        return DOUBLES_SUPPORT.get(move, 75) + (min(data["power"], 120) // 2 if data["power"] else 0)


def held_item_policy(stem: str, record: dict[str, Any]) -> list[str | None]:
    party = record["party"]
    if not party:
        return []
    level, major = max_level(record), is_major(stem, record)
    existing = [member["item"] for member in party]
    item_format = any(isinstance(item, str) for item in existing)
    item_format |= major and level >= 12
    item_format |= is_skilled(record) and level >= 45
    if not item_format:
        return [None] * len(party)
    result = [item if isinstance(item, str) else "ITEM_NONE" for item in existing]
    if not major:
        if is_skilled(record) and level >= 45:
            result[-1] = "ITEM_SITRUS_BERRY"
        return result
    # Preserve authored held items and add only a few progression-appropriate
    # roles. Every member still uses the string layout required by trainerproc.
    result = [item if isinstance(item, str) else "ITEM_NONE" for item in existing]
    if level < 12:
        return result
    if level < 20:
        if result[-1] == "ITEM_NONE":
            result[-1] = "ITEM_ORAN_BERRY"
    elif level < 35:
        if not any(item != "ITEM_NONE" for item in result):
            result[-1] = "ITEM_ORAN_BERRY"
    elif level < 45:
        if result[-1] == "ITEM_NONE":
            result[-1] = "ITEM_SITRUS_BERRY"
    else:
        if result[0] == "ITEM_NONE":
            result[0] = "ITEM_SITRUS_BERRY"
        if result[-1] == "ITEM_NONE":
            ace_items = ("ITEM_LEFTOVERS", "ITEM_EXPERT_BELT", "ITEM_FOCUS_SASH", "ITEM_LUM_BERRY")
            result[-1] = ace_items[sum(stem.encode("utf-8")) % len(ace_items)]
    return result
