#!/usr/bin/env python3
"""Validate the native Fairy attacks and BeaconDex STAB coverage."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MAX_LEARNSET_ENTRIES = 20
MOVE_STEMS = {
    "MOVE_FAIRY_WIND": "fairy_wind",
    "MOVE_DAZZLING_GLEAM": "dazzling_gleam",
    "MOVE_PLAY_ROUGH": "play_rough",
    "MOVE_MOONBLAST": "moonblast",
}
EXPECTED = {
    "MOVE_FAIRY_WIND": ("CLASS_SPECIAL", 40, 100, 30, "BATTLE_EFFECT_HIT", 0, "RANGE_SINGLE_TARGET"),
    "MOVE_DAZZLING_GLEAM": ("CLASS_SPECIAL", 80, 100, 10, "BATTLE_EFFECT_HIT", 0, "RANGE_ADJACENT_OPPONENTS"),
    "MOVE_PLAY_ROUGH": ("CLASS_PHYSICAL", 90, 90, 10, "BATTLE_EFFECT_LOWER_ATTACK_HIT", 10, "RANGE_SINGLE_TARGET"),
    "MOVE_MOONBLAST": ("CLASS_SPECIAL", 95, 100, 15, "BATTLE_EFFECT_LOWER_SP_ATK_HIT", 30, "RANGE_SINGLE_TARGET"),
}
EXPECTED_NAMES = {
    "MOVE_FAIRY_WIND": "Fairy Wind",
    "MOVE_DAZZLING_GLEAM": "Dazzling Gleam",
    "MOVE_PLAY_ROUGH": "Play Rough",
    "MOVE_MOONBLAST": "Moonblast",
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    species_header = (ROOT / "include/struct_defs/species.h").read_text(encoding="utf-8")
    if f"#define MAX_LEARNSET_ENTRIES        {MAX_LEARNSET_ENTRIES}" not in species_header:
        raise SystemExit("unexpected engine learnset-entry limit")

    move_constants = (ROOT / "generated/moves.txt").read_text(encoding="utf-8").splitlines()
    ids = {name: move_constants.index(name) for name in MOVE_STEMS}
    if list(ids.values()) != [468, 469, 470, 471]:
        raise SystemExit(f"unexpected Fairy move IDs: {ids}")
    if move_constants.index("MAX_MOVES") != 472:
        raise SystemExit("MAX_MOVES must follow Moonblast at ID 472")
    if max(ids.values()) >= 0x1FF:
        raise SystemExit("Fairy move ID exceeds the 9-bit learnset field")

    animation_sources = []
    for constant, stem in MOVE_STEMS.items():
        directory = ROOT / "res/moves" / stem
        data = load(directory / "data.json")
        actual = (
            data["class"], data["power"], data["accuracy"], data["pp"],
            data["effect"]["type"], data["effect"]["chance"], data["range"],
        )
        if data["type"] != "TYPE_FAIRY" or actual != EXPECTED[constant]:
            raise SystemExit(f"invalid move data for {constant}: {data['type']} {actual}")
        if data["name"] != EXPECTED_NAMES[constant]:
            raise SystemExit(f"invalid move name for {constant}: {data['name']!r}")
        if not data["description"] or not all(line.endswith("\n") for line in data["description"]):
            raise SystemExit(f"invalid move description for {constant}")
        for filename in ("anim.s", "script.s"):
            if not (directory / filename).is_file():
                raise SystemExit(f"missing {directory / filename}")
        animation_sources.append((directory / "anim.s").read_text(encoding="utf-8"))

    if len(set(animation_sources)) != len(MOVE_STEMS):
        raise SystemExit("Fairy moves must have four distinct animation scripts")

    moveproc = (ROOT / "tools/dataproc/src/moveproc.c").read_text(encoding="utf-8")
    if moveproc.count("for (size_t i = MAX_MOVES;") != 2:
        raise SystemExit("extra move-script archive entries must begin at MAX_MOVES")

    manifest = load(ROOT / "data/beacondex/species_normalized.json")
    if set(MOVE_STEMS) & set(manifest["move_substitutions"]):
        raise SystemExit("a native Fairy move is still declared as a substitution")

    manifest_by_code = {row["code_name"]: row for row in manifest["species"]}
    oversized_learnsets = {
        row["code_name"]: len(row["learnset"]["by_level"])
        for row in manifest["species"]
        if len(row["learnset"]["by_level"]) > MAX_LEARNSET_ENTRIES
    }
    if oversized_learnsets:
        raise SystemExit(f"learnsets exceed the {MAX_LEARNSET_ENTRIES}-entry archive limit: {oversized_learnsets}")
    fairy_species = []
    for data_path in sorted((ROOT / "res/pokemon").glob("*/data.json")):
        data = load(data_path)
        if "TYPE_FAIRY" not in data.get("types", []):
            continue
        constant = "SPECIES_" + data_path.parent.name.upper()
        fairy_species.append(constant)
        fairy_entries = [(level, move) for level, move in data["learnset"]["by_level"] if move in MOVE_STEMS]
        if not fairy_entries:
            raise SystemExit(f"{constant} has no native Fairy STAB move")
        duplicate_fairy_moves = [move for move, count in Counter(move for _, move in fairy_entries).items() if count > 1]
        if duplicate_fairy_moves:
            raise SystemExit(f"{constant} repeats Fairy attacks: {duplicate_fairy_moves}")
        too_strong_early = [
            (level, move)
            for level, move in fairy_entries
            if level < 20 and EXPECTED[move][1] > 60
        ]
        if too_strong_early:
            raise SystemExit(f"{constant} has an overpowered early Fairy attack: {too_strong_early}")
        manifest_moves = manifest_by_code[constant]["learnset"]["by_level"]
        if data["learnset"]["by_level"] != manifest_moves:
            raise SystemExit(f"runtime and normalized learnsets differ for {constant}")

    if len(fairy_species) != 16:
        raise SystemExit(f"expected 16 Fairy BeaconDex species, found {len(fairy_species)}")

    easy_chat = (ROOT / "src/easy_chat_word_list.c").read_text(encoding="utf-8")
    for constant in MOVE_STEMS:
        if easy_chat.count(f"MOVE_WORD({constant})") != 2:
            raise SystemExit(f"{constant} is missing from an Easy Chat index")

    # Battle Recorder and Wi-Fi replay validation used literal 467 bounds in
    # retail. New moves must survive both validators; the separate held-item
    # bound intentionally remains 467 because it is an item ID.
    recorder = (ROOT / "src/unk_0202F1D4.c").read_text(encoding="utf-8")
    if "unk_1C[v5] > NUM_VALID_MOVES" not in recorder or "heldItem > 467" not in recorder:
        raise SystemExit("Battle Recorder move/item bounds are not separated correctly")
    wifi = (ROOT / "src/overlay065/ov65_0222DCE0.c").read_text(encoding="utf-8")
    if "NUM_VALID_MOVES < param0->unk_0C[v0]" not in wifi:
        raise SystemExit("Wi-Fi replay validation still rejects expanded move IDs")
    television = (ROOT / "src/tv_segment.c").read_text(encoding="utf-8")
    if "LCRNG_Next() % NUM_VALID_MOVES" not in television:
        raise SystemExit("TV move selection still assumes the retail move count")

    # When a build tree is present, verify the generated text and archive order
    # use four separate entries at IDs 468-471. This also proves long names and
    # descriptions passed the text generator.
    # `build/` is the deliberately preserved unmodified US Rev 1 baseline.
    # Inspect only modified build trees so its retail 468-entry move table does
    # not masquerade as a failed BeaconDex build.
    for build_dir in sorted(path for path in ROOT.glob("build*") if path.name != "build"):
        move_output = build_dir / "res/moves"
        anim_order = move_output / "anim_scripts.order"
        script_order = move_output / "move_scripts.order"
        names_path = move_output / "move_names.json"
        descriptions_path = move_output / "move_descriptions.json"
        if not all(path.is_file() for path in (anim_order, script_order, names_path, descriptions_path)):
            continue
        expected_stems = list(MOVE_STEMS.values())
        anim_entries = anim_order.read_text(encoding="utf-8").splitlines()
        script_entries = script_order.read_text(encoding="utf-8").splitlines()
        if anim_entries[468:472] != [f"{stem}/anim" for stem in expected_stems]:
            raise SystemExit(f"invalid generated Fairy animation indices in {build_dir}")
        if script_entries[468:472] != [f"{stem}/script" for stem in expected_stems]:
            raise SystemExit(f"invalid generated Fairy script indices in {build_dir}")
        names = load(names_path)["messages"]
        descriptions = load(descriptions_path)["messages"]
        for constant, move_id in ids.items():
            if names[move_id]["en_US"] != EXPECTED_NAMES[constant]:
                raise SystemExit(f"compiled move name mismatch for {constant}")
            if not descriptions[move_id]["en_US"]:
                raise SystemExit(f"compiled move description missing for {constant}")

    print(f"Fairy moves: {len(MOVE_STEMS)} (IDs 468-471)")
    print(f"Fairy BeaconDex species with level-up STAB: {len(fairy_species)}")
    print("Fairy move audit: PASS")


if __name__ == "__main__":
    main()
