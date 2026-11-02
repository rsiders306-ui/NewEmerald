#!/usr/bin/env python3
"""Build a reviewable Platinum normalization candidate from the BeaconDex handoff.

This is an analysis artifact. It deliberately records every provisional value and
does not modify the pokeplatinum source tree.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PACK = REPO_ROOT.parent / "beacondex-pack" / "BeaconDex_63_Complete_Integration_Pack"


MOVE_SUBSTITUTIONS = {
    "Aurora Veil": ("Light Screen", "closest supported team-side special-damage screen"),
    "Heal Pulse": ("Wish", "closest supported healing move; it cannot directly target an ally"),
    "Pollen Puff": ("Signal Beam", "supported special Bug attack; ally-healing behavior is unavailable"),
    "Quiver Dance": ("Calm Mind", "supported special Attack/Special Defense setup move"),
    "Struggle Bug": ("Silver Wind", "supported special Bug attack"),
}


FAIRY_STAB_ADDITIONS = {
    "Gleamber": [[20, "Fairy Wind"]],
    "Loambelle": [[20, "Fairy Wind"]],
}


# The handoff repeats Play Rough at several early levels, including on special
# attackers. Keep the authored level slots, but turn them into a practical
# four-move Fairy progression: Fairy Wind early, Dazzling Gleam from level 20,
# then Play Rough or Moonblast for the appropriate attacking stat. A few
# redundant slots become existing support moves instead of relearning the same
# Fairy attack.
FAIRY_LEARNSET_BALANCE = {
    "Wardmane": {
        (16, "Gust"): "Fairy Wind",
    },
    "Siderion": {
        (1, "Gust"): "Fairy Wind",
        (16, "Play Rough"): "Focus Energy",
    },
    "Trillkit": {
        (9, "Play Rough"): "Fairy Wind",
        (13, "Play Rough"): "Sweet Kiss",
        (21, "Play Rough"): "Dazzling Gleam",
    },
    "Cantacat": {
        (18, "Return"): "Fairy Wind",
        (26, "Swift"): "Dazzling Gleam",
    },
    "Ariapurr": {
        (36, "Sing"): "Dazzling Gleam",
    },
    "Sermedic": {
        (36, "Heal Pulse"): "Dazzling Gleam",
    },
    "Groovette": {
        (9, "Play Rough"): "Fairy Wind",
        (21, "Play Rough"): "Dazzling Gleam",
        (29, "Play Rough"): "Wish",
        (45, "Play Rough"): "Calm Mind",
    },
    "Sautène": {
        (9, "Play Rough"): "Fairy Wind",
        (22, "Play Rough"): "Dazzling Gleam",
        (26, "Play Rough"): "Wish",
        (38, "Play Rough"): "Calm Mind",
        (60, "Play Rough"): "Encore",
    },
    "Veloura": {
        (1, "Play Rough"): "Fairy Wind",
        (18, "Play Rough"): "Sweet Kiss",
        (22, "Play Rough"): "Dazzling Gleam",
        (34, "Play Rough"): "Wish",
        (56, "Play Rough"): "Encore",
        (64, "Play Rough"): "Helping Hand",
    },
    "Nestelle": {
        (17, "Gust"): "Fairy Wind",
        (37, "Giga Drain"): "Dazzling Gleam",
    },
    "Heartistle": {
        (33, "Giga Drain"): "Dazzling Gleam",
    },
    "Tidelion": {
        (36, "Fairy Wind"): "Play Rough",
    },
    "Hearthalo": {
        (36, "Follow Me"): "Dazzling Gleam",
        (44, "Dazzling Gleam"): "Follow Me",
    },
    "Meadowmira": {
        (36, "Follow Me"): "Dazzling Gleam",
        (40, "Dazzling Gleam"): "Follow Me",
    },
}


ABILITY_SUBSTITUTIONS = {
    "Pixilate": ("Adaptability", "closest supported boost to Ariapurr's Normal STAB"),
    "Ice Scales": ("Thick Fat", "supported defensive ability that fits an insulated Ice moth"),
    "Discipler": ("Steadfast", "provisional thematic existing-ability replacement"),
    "Dad Strength": ("Solid Rock", "provisional tank-oriented existing-ability replacement"),
    "Mama Instinct": ("Forewarn", "provisional instinct-themed existing-ability replacement"),
    "Sermon Notes": ("Synchronize", "provisional support-themed existing-ability replacement"),
    "Deadpan Drive": ("Motor Drive", "provisional existing drive-themed replacement"),
    "Family First": ("Battle Armor", "provisional protector-themed existing-ability replacement"),
    "Friend Guard": ("Filter", "closest supported 25-percent damage-reduction mechanic, but self-only"),
}


# Template values supply missing low-level fields (measurements, body shape/color,
# Pokedex scaling, footprint classification, Pal Park defaults, and temporary cry).
FAMILY_TEMPLATES = {
    1: ("riolu", "luxio", "lucario"),
    2: ("aron", "lairon", "aggron"),
    3: ("starly", "staravia", "staraptor"),
    4: ("skitty", "delcatty", "purugly"),
    5: ("mime_jr", "kirlia", "gardevoir"),
    6: ("poochyena", "mightyena", "houndoom"),
    7: ("buneary", "lopunny", "ninetales"),
    8: ("machop", "machoke", "machamp"),
    9: ("budew", "roselia", "roserade"),
    10: ("buizel", "floatzel", "lapras"),
    11: ("caterpie", "metapod", "mothim"),
    12: ("nincada", "ninjask", "shedinja"),
    13: ("magby", "magmar", "magmortar"),
    14: ("spheal", "sealeo", "walrein"),
    15: ("trapinch", "vibrava", "flygon"),
    16: ("geodude", "graveler", "golem"),
    17: ("turtwig", "grotle", "torterra"),
    18: ("bidoof", "bibarel", "raticate"),
    19: ("swinub", "piloswine", "mamoswine"),
    20: ("kricketot", "kricketune", "volbeat"),
    21: ("growlithe", "mightyena", "arcanine"),
}


FAMILY_EGG_GROUPS = {
    1: ("EGG_GROUP_FIELD", "EGG_GROUP_HUMAN_LIKE"),
    2: ("EGG_GROUP_FIELD", "EGG_GROUP_MINERAL"),
    3: ("EGG_GROUP_FLYING", "EGG_GROUP_FIELD"),
    4: ("EGG_GROUP_FIELD", "EGG_GROUP_FAIRY"),
    5: ("EGG_GROUP_HUMAN_LIKE", "EGG_GROUP_FAIRY"),
    6: ("EGG_GROUP_FIELD", "EGG_GROUP_FIELD"),
    7: ("EGG_GROUP_HUMAN_LIKE", "EGG_GROUP_FAIRY"),
    8: ("EGG_GROUP_HUMAN_LIKE", "EGG_GROUP_FIELD"),
    9: ("EGG_GROUP_GRASS", "EGG_GROUP_FAIRY"),
    10: ("EGG_GROUP_FIELD", "EGG_GROUP_WATER_1"),
    11: ("EGG_GROUP_BUG", "EGG_GROUP_BUG"),
    12: ("EGG_GROUP_BUG", "EGG_GROUP_AMORPHOUS"),
    13: ("EGG_GROUP_AMORPHOUS", "EGG_GROUP_FAIRY"),
    14: ("EGG_GROUP_WATER_1", "EGG_GROUP_AMORPHOUS"),
    15: ("EGG_GROUP_BUG", "EGG_GROUP_DRAGON"),
    16: ("EGG_GROUP_MINERAL", "EGG_GROUP_AMORPHOUS"),
    17: ("EGG_GROUP_FIELD", "EGG_GROUP_FAIRY"),
    18: ("EGG_GROUP_FIELD", "EGG_GROUP_MINERAL"),
    19: ("EGG_GROUP_FIELD", "EGG_GROUP_FIELD"),
    20: ("EGG_GROUP_BUG", "EGG_GROUP_BUG"),
    21: ("EGG_GROUP_FIELD", "EGG_GROUP_MINERAL"),
}


UNIVERSAL_TMS = {
    "TM06", "TM10", "TM17", "TM21", "TM27", "TM32", "TM42", "TM43",
    "TM44", "TM45", "TM58", "TM78", "TM82", "TM83", "TM87", "TM90",
}


TYPE_TMS = {
    "Normal": {"TM05", "TM54", "TM67"},
    "Fighting": {"TM01", "TM08", "TM31", "TM52", "TM56", "TM75"},
    "Flying": {"TM40", "TM47", "TM51", "TM88", "TM89"},
    "Rock": {"TM26", "TM28", "TM37", "TM39", "TM69", "TM71", "TM76", "TM80"},
    "Steel": {"TM23", "TM74", "TM91"},
    "Fairy": {"TM04", "TM16", "TM20", "TM33", "TM48", "TM73", "TM77", "TM92"},
    "Water": {"TM03", "TM07", "TM13", "TM14", "TM18", "TM55"},
    "Bug": {"TM19", "TM62", "TM81", "TM89"},
    "Ice": {"TM07", "TM13", "TM14", "TM72"},
    "Ghost": {"TM12", "TM29", "TM30", "TM41", "TM46", "TM61", "TM65", "TM79"},
    "Fire": {"TM11", "TM35", "TM38", "TM50", "TM61"},
    "Poison": {"TM36", "TM84"},
    "Dragon": {"TM02", "TM23", "TM59"},
    "Ground": {"TM26", "TM28", "TM37", "TM39", "TM71", "TM76", "TM80"},
    "Grass": {"TM09", "TM11", "TM19", "TM22", "TM53", "TM70", "TM75", "TM86"},
    "Psychic": {"TM04", "TM16", "TM20", "TM29", "TM33", "TM48", "TM67", "TM73", "TM77", "TM85", "TM92"},
    "Dark": {"TM12", "TM30", "TM41", "TM46", "TM49", "TM56", "TM63", "TM66", "TM79"},
}


FAMILY_HMS = {
    10: {1: {"HM03"}, 2: {"HM03"}, 3: {"HM03", "HM04", "HM07"}},
    11: {3: {"HM05"}},
    12: {2: {"HM01"}, 3: {"HM01", "HM05"}},
    13: {3: {"HM04"}},
    14: {1: {"HM03"}, 2: {"HM03"}, 3: {"HM03", "HM07"}},
    15: {1: {"HM01"}, 2: {"HM01", "HM02", "HM05"}, 3: {"HM01", "HM02", "HM05"}},
    16: {2: {"HM04", "HM06"}, 3: {"HM04", "HM06", "HM08"}},
    17: {1: {"HM01"}, 2: {"HM01", "HM04"}, 3: {"HM01", "HM04", "HM06"}},
    18: {1: {"HM01"}, 2: {"HM01", "HM06"}, 3: {"HM01", "HM04", "HM06"}},
    19: {2: {"HM04", "HM06"}, 3: {"HM04", "HM06", "HM08"}},
    20: {2: {"HM01"}, 3: {"HM01", "HM05"}},
    21: {2: {"HM04", "HM06"}, 3: {"HM04", "HM06", "HM08"}},
}


PROMOTED_HIDDEN_ABILITY = {
    "Siderion", "Oxguard", "Ariapurr", "Sermedic", "Talladevil", "Aegicare"
}


def normalized(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def machine_sort_key(machine: str) -> tuple[str, int]:
    return machine[:2], int(machine[2:])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pack",
        type=Path,
        default=Path(os.environ.get("BEACONDEX_PACK", DEFAULT_PACK)),
        help="extracted BeaconDex integration-pack root",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "data" / "beacondex" / "species_normalized.json",
        help="output manifest path",
    )
    return parser.parse_args()


def load_template(name: str) -> dict:
    return json.loads((REPO_ROOT / "res" / "pokemon" / name / "data.json").read_text())


def main() -> None:
    args = parse_args()
    pack = args.pack.resolve()
    if not (pack / "metadata" / "species_master_63.json").is_file():
        raise SystemExit(f"BeaconDex pack not found at {pack}")

    master = json.loads((pack / "metadata" / "species_master_63.json").read_text())
    species = master["species"]

    move_constants = [line.strip() for line in (REPO_ROOT / "generated" / "moves.txt").read_text().splitlines()]
    move_by_name = {
        normalized(line.removeprefix("MOVE_")): line
        for line in move_constants
        if line.startswith("MOVE_") and line not in {"MOVE_NONE", "MAX_MOVES"}
    }
    ability_constants = [line.strip() for line in (REPO_ROOT / "generated" / "abilities.txt").read_text().splitlines()]
    ability_by_name = {
        normalized(line.removeprefix("ABILITY_")): line
        for line in ability_constants
        if line.startswith("ABILITY_") and line != "ABILITY_NONE"
    }
    supported_machines = {
        path.stem.upper()
        for path in (REPO_ROOT / "res" / "items" / "data").glob("[th]m[0-9][0-9].json")
    }

    first_by_family = {family: next(s for s in species if s["family_index"] == family and s["stage"] == 1)
                       for family in range(1, 22)}
    rows = []

    for source in species:
        row = {
            "beacondex_id": source["dex_id"],
            "proposed_national_dex": 493 + source["dex_id"],
            "proposed_sinnoh_dex": 210 + source["dex_id"],
            "code_name": f"SPECIES_{source['code_name']}",
            "display_name": source["name"],
            "family_index": source["family_index"],
            "stage": source["stage"],
            "types": [f"TYPE_{t.upper()}" for t in source["types"]],
            "base_stats": {
                "hp": source["base_stats"]["hp"],
                "attack": source["base_stats"]["attack"],
                "defense": source["base_stats"]["defense"],
                "speed": source["base_stats"]["speed"],
                "special_attack": source["base_stats"]["sp_attack"],
                "special_defense": source["base_stats"]["sp_defense"],
            },
            "bst": source["bst"],
            "source_status": {
                "pokedex_entry": source["pokedex_entry_status"],
                "evolution": source["evolution_status"],
                "learnset": source["level_up_status"],
                "tm_hm": source["tm_hm_status"],
                "sprite": source["sprite_status"],
            },
        }

        # Gen IV has two runtime ability slots and no hidden-ability mechanic.
        source_abilities = [source.get("ability_1"), source.get("ability_2")]
        runtime_abilities = []
        ability_notes = []
        for ability in source_abilities:
            if not ability:
                continue
            if ability in ABILITY_SUBSTITUTIONS:
                replacement, reason = ABILITY_SUBSTITUTIONS[ability]
                ability_notes.append({"from": ability, "to": replacement, "reason": reason})
                ability = replacement
            runtime_abilities.append(ability_by_name[normalized(ability)])
        hidden = source.get("hidden_ability")
        hidden_candidate = None
        if hidden:
            replacement, reason = ABILITY_SUBSTITUTIONS.get(hidden, (hidden, "already supported"))
            hidden_candidate = {
                "source": hidden,
                "supported_candidate": ability_by_name[normalized(replacement)],
                "reason": reason,
                "runtime_policy": "promote_to_slot_2" if source["name"] in PROMOTED_HIDDEN_ABILITY else "metadata_only_no_gen4_hidden_slot",
            }
            if source["name"] in PROMOTED_HIDDEN_ABILITY:
                runtime_abilities.append(hidden_candidate["supported_candidate"])
        while len(runtime_abilities) < 2:
            runtime_abilities.append("ABILITY_NONE")
        row["abilities"] = {
            "runtime_slots": runtime_abilities[:2],
            "substitutions": ability_notes,
            "hidden_candidate": hidden_candidate,
        }

        # All nonfinal families use a deterministic, playable evolution path.
        if source["stage"] == 3:
            evolution = None
        else:
            family_members = sorted((s for s in species if s["family_index"] == source["family_index"]), key=lambda s: s["stage"])
            target = family_members[source["stage"]]
            if source["name"] == "Timblet":
                evolution = ["EVO_LEVEL_HAPPINESS", f"SPECIES_{target['code_name']}"]
            elif source["name"] == "Nestelle":
                evolution = ["EVO_LEVEL_KNOW_MOVE", "MOVE_WISH", f"SPECIES_{target['code_name']}"]
            else:
                level = 16 if source["family_index"] <= 3 and source["stage"] == 1 else 36 if source["stage"] == 2 else 18
                evolution = ["EVO_LEVEL", level, f"SPECIES_{target['code_name']}"]
        row["evolution"] = evolution

        by_level = []
        substitutions = []
        for move in source.get("level_up_moves") or []:
            move_name = move["move"]
            balanced_move = FAIRY_LEARNSET_BALANCE.get(source["name"], {}).get((move["level"], move_name))
            if balanced_move is not None:
                substitutions.append({
                    "level": move["level"],
                    "from": move_name,
                    "to": balanced_move,
                    "reason": "Fairy STAB balance: use low-power attacks early, match the stronger attack to the user's stats, and avoid duplicate Fairy moves",
                })
                move_name = balanced_move
            if move_name in MOVE_SUBSTITUTIONS:
                replacement, reason = MOVE_SUBSTITUTIONS[move_name]
                substitutions.append({"level": move["level"], "from": move_name, "to": replacement, "reason": reason})
                move_name = replacement
            by_level.append([move["level"], move_by_name[normalized(move_name)]])
        for level, move_name in FAIRY_STAB_ADDITIONS.get(source["name"], []):
            by_level.append([level, move_by_name[normalized(move_name)]])
        by_level.sort(key=lambda entry: entry[0])
        repeated = {move: levels for move, levels in ((move, [level for level, candidate in by_level if candidate == move])
                                                     for move in {candidate for _, candidate in by_level}) if len(levels) > 1}
        row["learnset"] = {
            "by_level": by_level,
            "substitutions": substitutions,
            "repeated_moves_requiring_balance_review": repeated,
            "by_tutor": [],
            "tutor_policy": "empty for the first compile; author type-appropriate tutor compatibility during balance pass",
            "egg_moves": [],
            "egg_moves_policy": "empty but breeding remains functional; authoring is deferred",
        }

        if source["source_group"] == "original_27":
            machines = {f"TM{tm}" for tm in (source.get("tm") or [])} | set(source.get("hm") or [])
            provenance = "normalized legacy candidate; TM01-TM50 retain their Platinum meanings; HM05 changed from Flash to Defog"
        else:
            machines = set(UNIVERSAL_TMS)
            for species_type in source["types"]:
                machines |= TYPE_TMS.get(species_type, set())
            if source["stage"] == 3:
                machines |= {"TM15", "TM68"}
            machines |= FAMILY_HMS.get(source["family_index"], {}).get(source["stage"], set())
            provenance = "provisional deterministic Platinum type-role defaults; requires balance review"
        row["machines"] = {
            "by_tm_hm": sorted(machines, key=machine_sort_key),
            "provenance": provenance,
        }

        template_name = FAMILY_TEMPLATES[source["family_index"]][source["stage"] - 1]
        template = load_template(template_name)
        stat_key_order = ["hp", "attack", "defense", "speed", "special_attack", "special_defense"]
        highest = max(stat_key_order, key=lambda key: (row["base_stats"][key], -stat_key_order.index(key)))
        ev_yields = {key: 0 for key in stat_key_order}
        ev_yields[highest] = source["stage"]
        row["documented_defaults"] = {
            "template_species": f"SPECIES_{template_name.upper()}",
            "template_fields_copied": [
                "pokedex height/weight", "body shape", "body color", "pokedex display scaling",
                "footprint classification", "Pal Park/catching-show defaults", "temporary cry",
            ],
            "height_inches": template["pokedex_data"]["height_inches"],
            "weight_pounds": template["pokedex_data"]["weight_pounds"],
            "body_shape": template["pokedex_data"]["body_shape"],
            "body_color": template["body_color"],
            "pokedex_display_scaling": {
                key: value
                for key, value in template["pokedex_data"].items()
                if key.startswith("trainer_") or key.startswith("pokemon_")
            },
            "footprint_classification": template["footprint"],
            "catching_show": template["catching_show"],
            "flip_sprite": template["flip_sprite"],
            "temporary_icon_palette": template["icon_palette"],
            "cry_species": f"SPECIES_{template_name.upper()}",
            "catch_rate": 45 if source["family_index"] <= 3 else {1: 190, 2: 90, 3: 45}[source["stage"]],
            "base_exp_reward": {1: 64, 2: 142, 3: 220}[source["stage"]],
            "ev_yields": ev_yields,
            "held_items": {"common": "ITEM_NONE", "rare": "ITEM_NONE"},
            "gender_ratio": "GENDER_RATIO_FEMALE_12_5" if source["family_index"] <= 3 else "GENDER_RATIO_FEMALE_50",
            "hatch_cycles": 25 if source["family_index"] == 15 else 20,
            "base_friendship": 70,
            "exp_rate": "EXP_RATE_MEDIUM_SLOW" if source["family_index"] in {1, 2, 3, 15} else "EXP_RATE_MEDIUM_FAST",
            "egg_groups": list(FAMILY_EGG_GROUPS[source["family_index"]]),
            "offspring": f"SPECIES_{first_by_family[source['family_index']]['code_name']}",
            "safari_flee_rate": 0,
            "sprite_data_template_species": f"SPECIES_{template_name.upper()}",
            "icon_art_policy": (
                "use supplied legacy icon after DS conversion"
                if source["source_group"] == "original_27"
                else "generate a reviewed DS party icon from the front draft; template icon is placeholder only"
            ),
            "footprint_art_policy": (
                "use supplied legacy footprint after DS conversion"
                if source["source_group"] == "original_27"
                else "author from silhouette; template footprint is placeholder only"
            ),
        }
        category = source["category"].removeprefix("The ")
        row["pokedex"] = {
            "category_en": category,
            "entry_en": source["pokedex_entry"],
            "locale_policy": "copy English fallback into FR/DE/IT/ES/JP banks until translations are authored",
            "approval": source["pokedex_entry_status"],
        }

        conflicts = list(source.get("notes") or [])
        if source["name"] == "Terraptor":
            conflicts.append("Use manifest/user-override BST 545; another recap says 550")
        if source["name"] in {"Nilecub", "Reedmane", "Tidelion"}:
            conflicts.append("Moses-line types, moves, and abilities remain provisional")
        if source["name"] == "Heartistle":
            conflicts.append("Selected spelling is Heartistle; old Hearthistle asset references are aliases only")
        if source["source_group"] == "original_27":
            conflicts.append("Legacy typing/learnset/machine data remain review candidates")
        if source["name"] in FAIRY_STAB_ADDITIONS:
            conflicts.append("Fairy Wind at level 20 is a documented STAB default added because the source learnset had no Fairy attack")
        row["conflicts_and_review"] = conflicts
        rows.append(row)

    output = {
        "schema": "beacondex-platinum-normalization-candidate-v1",
        "authority": "approved user requirements > user_override_27_source.json > species_master_63.json > documented defaults",
        "allocation": {
            "national_dex": "494-556, inserted before EGG/BAD_EGG sentinels",
            "sinnoh_dex": "211-273 provisional appended regional entries",
            "replaces_original_species": False,
        },
        "runtime_policies": {
            "fairy_type": "retain and implement TYPE_FAIRY; never coerce to another type",
            "fairy_moves": "Fairy Wind, Dazzling Gleam, Play Rough, and Moonblast use native TYPE_FAIRY move data with supported Gen-IV battle effects",
            "hidden_abilities": "Platinum has two ability slots and no hidden-ability mechanic; promote the six original-27 final-stage candidates into vacant slot 2, retain other hidden candidates as metadata",
            "localization": "English source text is a technical fallback for all required language banks, clearly marked untranslated",
            "habitat": "Platinum has no per-species habitat field; express habitat through encounters",
            "egg_moves": "empty for initial integration; breeding and offspring mapping remain functional",
            "cries": "reuse documented vanilla template cries until authored audio exists",
        },
        "move_substitutions": {key: {"to": value[0], "reason": value[1]} for key, value in MOVE_SUBSTITUTIONS.items()},
        "ability_substitutions": {key: {"to": value[0], "reason": value[1]} for key, value in ABILITY_SUBSTITUTIONS.items()},
        "species": rows,
        "validation": {
            "species_count": len(rows),
            "family_count": len({row["family_index"] for row in rows}),
            "national_ids_unique": len({row["proposed_national_dex"] for row in rows}) == len(rows),
            "all_runtime_moves_supported": all(move in move_constants for row in rows for _, move in row["learnset"]["by_level"]),
            "all_runtime_abilities_supported": all(ability == "ABILITY_NONE" or ability in ability_constants for row in rows for ability in row["abilities"]["runtime_slots"]),
            "all_machine_ids_supported": all(machine in supported_machines for row in rows for machine in row["machines"]["by_tm_hm"]),
            "all_bst_sums_match": all(sum(row["base_stats"].values()) == row["bst"] for row in rows),
            "all_display_names_fit_ten_characters": all(len(row["display_name"]) <= 10 for row in rows),
            "all_252_sprite_paths_exist": all(
                (pack / sprite_path).is_file()
                for source in species
                for sprite_path in source["sprite_paths"].values()
            ),
            "all_original_27_icons_exist": all(
                (pack / "source_palettes_27" / source["name"].lower() / "icon.png").is_file()
                for source in species if source["source_group"] == "original_27"
            ),
            "all_original_27_footprints_exist": all(
                (pack / "source_palettes_27" / source["name"].lower() / "footprint.png").is_file()
                for source in species if source["source_group"] == "original_27"
            ),
            "fairy_engine_status": "TYPE_FAIRY and four official Fairy moves integrated",
            "starter_names": ["Glimbark", "Calflank", "Zephylet", "Turtwig", "Chimchar", "Piplup"],
            "source_move_name_count": len({move["move"] for source in species for move in source.get("level_up_moves") or []}),
            "unsupported_source_move_names": sorted(MOVE_SUBSTITUTIONS),
            "species_with_repeated_levelup_moves": sum(bool(row["learnset"]["repeated_moves_requiring_balance_review"]) for row in rows),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n")
    print(args.output)


if __name__ == "__main__":
    main()
