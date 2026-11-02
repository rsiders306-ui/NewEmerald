#!/usr/bin/env python3
"""Build the consolidated machine-readable BeaconDex integration report."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = REPO_ROOT / "data" / "beacondex"
TRAINER_ROOT = REPO_ROOT / "res" / "trainers" / "data"
ENCOUNTER_ROOT = REPO_ROOT / "res" / "field" / "encounters"

STARTER_CHOICES = (
    "SPECIES_GLIMBARK",
    "SPECIES_CALFLANK",
    "SPECIES_ZEPHYLET",
    "SPECIES_TURTWIG",
    "SPECIES_CHIMCHAR",
    "SPECIES_PIPLUP",
)

BASE_ROM = {
    "title": "POKEMON PL",
    "game_code": "CPUE",
    "revision": 1,
    "size": 134_217_728,
    "sha1": "0862ec35b24de5c7e2dcb88c9eea0873110d755c",
    "sha256": "fbce4c4def0c7797f8dd238a3d7a5e48b4a7e3abd86890ac65f6321cef781bdb",
}

AUDITS = {
    "boot_integrity": ["tools/beacondex/boot_integrity_audit.py"],
    "trainer_parties": ["tools/beacondex/trainer_party_audit.py"],
    "trainer_battle_flow": ["tools/beacondex/trainer_battle_flow_audit.py", "--json"],
    "wild_distribution": ["tools/beacondex/wild_distribution_audit.py"],
    "trainer_distribution": ["tools/beacondex/trainer_distribution_audit.py"],
    "frontier_doubles": ["tools/beacondex/frontier_doubles_audit.py"],
    "starter_pairs": ["tools/beacondex/starter_pair_audit.py"],
    "cries": [
        "tools/beacondex/cry_sdat_audit.py",
        "--naix",
        "build-cloud-r1/res/sound/pl_sound_data.naix",
    ],
    "fairy_moves": [
        "tools/beacondex/fairy_moves_audit.py",
        "--build-dir",
        "build-cloud-r1",
    ],
    "species_runtime": [
        "tools/beacondex/species_runtime_audit.py",
        "--build",
        "build-cloud-r1",
    ],
    "save_layout": ["tools/beacondex/save_layout_audit.py"],
    "trainer_ai_progression": ["tools/beacondex/trainer_ai_progression.py"],
}

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=DATA_ROOT / "integration_report.json",
        help="report path (default: data/beacondex/integration_report.json)",
    )
    parser.add_argument(
        "--rom",
        type=Path,
        default=REPO_ROOT / "build-cloud-r1" / "pokeplatinum.us.nds",
        help="built ROM to hash when present",
    )
    parser.add_argument(
        "--patch",
        type=Path,
        default=REPO_ROOT / "dist" / "BeaconDex-Platinum-v0.1.0-US-Rev1.bps",
        help="BPS patch to hash when present",
    )
    return parser.parse_args()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def file_hashes(path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "path": path.relative_to(REPO_ROOT).as_posix()
        if path.is_relative_to(REPO_ROOT)
        else str(path),
        "present": path.is_file(),
    }
    if not path.is_file():
        return result

    sha1 = hashlib.sha1()
    sha256 = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            sha1.update(block)
            sha256.update(block)
    result.update(
        {
            "size": path.stat().st_size,
            "sha1": sha1.hexdigest(),
            "sha256": sha256.hexdigest(),
        }
    )
    return result


def verify_emulator_evidence(built_rom: dict[str, Any]) -> dict[str, Any]:
    report_path = DATA_ROOT / "emulator_boot_report.json"
    result: dict[str, Any] = {
        "path": report_path.relative_to(REPO_ROOT).as_posix(),
        "present": report_path.is_file(),
        "passed": False,
    }
    if not report_path.is_file():
        return result

    report = load_json(report_path)
    artifacts = []
    for emulator in report.get("emulators", []):
        for kind in ("screenshot", "log"):
            declared = emulator.get(kind)
            if not declared:
                continue
            artifact_path = REPO_ROOT / declared["path"]
            hashes = file_hashes(artifact_path)
            content_matches = True
            if kind == "log" and artifact_path.is_file():
                log_text = artifact_path.read_text(encoding="utf-8", errors="replace")
                content_matches = all(
                    marker in log_text for marker in declared.get("contains", [])
                )
                if declared.get("arm9_data_abort") is False:
                    content_matches = content_matches and "ARM9: data abort" not in log_text
            artifacts.append(
                {
                    "emulator": emulator["name"],
                    "kind": kind,
                    "expected_sha256": declared["sha256"],
                    "actual": hashes,
                    "content_matches": content_matches,
                    "matches": hashes.get("sha256") == declared["sha256"]
                    and content_matches,
                }
            )

    rom_matches = (
        report.get("release_rom", {}).get("sha256") == built_rom.get("sha256")
    )
    result.update(
        {
            "report": report,
            "release_rom_matches": rom_matches,
            "artifacts": artifacts,
            "passed": bool(report.get("passed"))
            and rom_matches
            and bool(artifacts)
            and all(artifact["matches"] for artifact in artifacts),
        }
    )
    return result


def source_commit() -> str | None:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip() if completed.returncode == 0 else None


def verify_bps_round_trip(target: Path, patch: Path) -> dict[str, Any]:
    base = REPO_ROOT / "build" / "pokeplatinum.us.nds"
    result: dict[str, Any] = {
        "base": file_hashes(base),
        "attempted": False,
        "passed": False,
    }
    if not (base.is_file() and target.is_file() and patch.is_file()):
        result["reason"] = "base ROM, target ROM, or BPS patch is absent"
        return result
    if result["base"].get("sha256") != BASE_ROM["sha256"]:
        result["reason"] = "local patch base does not match the exact US Rev 1 hash"
        return result

    result["attempted"] = True
    with tempfile.NamedTemporaryFile(
        prefix="beacondex-bps-", suffix=".nds", delete=False
    ) as stream:
        reconstructed = Path(stream.name)
    try:
        completed = subprocess.run(
            [
                sys.executable,
                "tools/beacondex/bps_patch.py",
                "apply",
                str(base),
                str(patch),
                str(reconstructed),
            ],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        reconstructed_hashes = file_hashes(reconstructed)
        target_hashes = file_hashes(target)
        result.update(
            {
                "exit_code": completed.returncode,
                "reconstructed": reconstructed_hashes,
                "target": target_hashes,
                "passed": completed.returncode == 0
                and reconstructed_hashes.get("sha256")
                == target_hashes.get("sha256"),
                "stderr": completed.stderr.strip(),
            }
        )
    finally:
        reconstructed.unlink(missing_ok=True)
    return result


def run_audit(arguments: list[str]) -> dict[str, Any]:
    command = [sys.executable, *arguments]
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    output = completed.stdout.strip()
    parsed: Any = output
    if output:
        try:
            parsed = json.loads(output)
        except json.JSONDecodeError:
            pass
    return {
        "command": " ".join(arguments),
        "exit_code": completed.returncode,
        "passed": completed.returncode == 0,
        "report": parsed,
        "stderr": completed.stderr.strip(),
    }


def collect_audits() -> dict[str, Any]:
    commands = dict(AUDITS)
    registered_scripts = {arguments[0] for arguments in commands.values()}
    for path in sorted((REPO_ROOT / "tools" / "beacondex").glob("*_audit.py")):
        script = path.relative_to(REPO_ROOT).as_posix()
        if script not in registered_scripts:
            commands[path.stem] = [script]
    return {name: run_audit(arguments) for name, arguments in commands.items()}


def encounter_index() -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    table_names = (
        "land_encounters",
        "surf_encounters",
        "old_rod_encounters",
        "good_rod_encounters",
        "super_rod_encounters",
    )
    for path in sorted(ENCOUNTER_ROOT.glob("encounters_*.json")):
        data = load_json(path)
        map_name = path.stem.removeprefix("encounters_")
        for table_name in table_names:
            for slot, encounter in enumerate(data.get(table_name, [])):
                species = encounter["species"]
                row = {
                    "map": map_name,
                    "table": table_name,
                    "slot": slot,
                }
                for key in ("level", "level_min", "level_max"):
                    if key in encounter:
                        row[key] = encounter[key]
                result.setdefault(species, []).append(row)
    return result


def sprite_slots(species_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    slots = []
    for species in species_rows:
        slug = species["code_name"].removeprefix("SPECIES_").lower()
        for palette, view in itertools.product(("normal", "shiny"), ("front", "back")):
            sheet = REPO_ROOT / "res" / "pokemon" / slug / f"male_{view}.png"
            palette_path = REPO_ROOT / "res" / "pokemon" / slug / f"{palette}.pal"
            slots.append(
                {
                    "species": species["code_name"],
                    "variant": palette,
                    "view": view,
                    "sheet": sheet.relative_to(REPO_ROOT).as_posix(),
                    "palette": palette_path.relative_to(REPO_ROOT).as_posix(),
                    "present": sheet.is_file() and palette_path.is_file(),
                }
            )
    return slots


def fairy_moves() -> list[dict[str, Any]]:
    result = []
    for path in sorted((REPO_ROOT / "res" / "moves").glob("*/data.json")):
        move = load_json(path)
        if move["type"] == "TYPE_FAIRY":
            result.append(
                {
                    "name": move["name"],
                    "constant": f"MOVE_{path.parent.name.upper()}",
                    "class": move["class"],
                    "power": move["power"],
                    "accuracy": move["accuracy"],
                    "range": move["range"],
                    "path": path.relative_to(REPO_ROOT).as_posix(),
                }
            )
    return result


def cry_registry(species_rows: list[dict[str, Any]]) -> dict[str, Any]:
    sound_path = REPO_ROOT / "res" / "sound" / "pl_sound_data.json"
    sound_data = load_json(sound_path)
    wave_archives = sound_data["wavarcInfo"]
    registry = []
    for species in species_rows:
        species_id = species["proposed_national_dex"]
        entry = wave_archives[species_id] if species_id < len(wave_archives) else None
        slug = species["code_name"].removeprefix("SPECIES_").lower()
        expected_file = f"{slug}/cry.swar"
        registry.append(
            {
                "species": species["code_name"],
                "species_id": species_id,
                "expected_file": expected_file,
                "wave_archive": entry,
                "matches_expected": isinstance(entry, dict)
                and entry.get("fileName") == expected_file,
            }
        )
    return {
        "source_wav_count": sum(
            (REPO_ROOT / "res" / "pokemon" / row["code_name"].removeprefix("SPECIES_").lower() / "cry.wav").is_file()
            for row in species_rows
        ),
        "registry": registry,
        "all_species_slots_registered": all(row["matches_expected"] for row in registry),
        "shaymin_sky_slots": [
            index
            for index, entry in enumerate(wave_archives)
            if isinstance(entry, dict)
            and entry.get("fileName") == "shaymin/forms/sky/cry.swar"
        ],
    }


def trainer_assignment_index() -> dict[str, dict[str, Any]]:
    manifest = load_json(DATA_ROOT / "trainer_distribution.json")
    return {row["species"]: row for row in manifest["assignments"]}


def build_report(rom_path: Path, patch_path: Path) -> dict[str, Any]:
    manifest = load_json(DATA_ROOT / "species_normalized.json")
    species_rows = manifest["species"]
    wild_manifest = load_json(DATA_ROOT / "wild_distribution.json")
    wild_by_species = {row["species"]: row for row in wild_manifest["placements"]}
    starter_recovery = wild_manifest.get("starter_recovery_placements", [])
    trainers_by_species = trainer_assignment_index()
    encounters = encounter_index()
    sprites = sprite_slots(species_rows)
    audits = collect_audits()
    fairy = fairy_moves()
    cries = cry_registry(species_rows)
    built_rom = file_hashes(rom_path)
    emulator_evidence = verify_emulator_evidence(built_rom)
    bps_patch = file_hashes(patch_path)
    bps_round_trip = verify_bps_round_trip(rom_path, patch_path)

    registry = (REPO_ROOT / "generated" / "species.txt").read_text(encoding="utf-8").splitlines()
    species_entries = []
    conflicts = []
    for row in species_rows:
        species = row["code_name"]
        entry = {
            "beacondex_id": row["beacondex_id"],
            "national_dex": row["proposed_national_dex"],
            "sinnoh_dex": row["proposed_sinnoh_dex"],
            "constant": species,
            "name": row["display_name"],
            "family": row["family_index"],
            "stage": row["stage"],
            "types": row["types"],
            "abilities": row["abilities"]["runtime_slots"],
            "evolution": row["evolution"],
            "wild_placement": wild_by_species.get(species),
            "all_static_encounters": encounters.get(species, []),
            "trainer_assignment": trainers_by_species.get(species),
            "runtime_assets": {
                "data": f"res/pokemon/{species.removeprefix('SPECIES_').lower()}/data.json",
                "icon": f"res/pokemon/{species.removeprefix('SPECIES_').lower()}/icon.png",
                "footprint": f"res/pokemon/{species.removeprefix('SPECIES_').lower()}/footprint.png",
                "cry": f"res/pokemon/{species.removeprefix('SPECIES_').lower()}/cry.wav",
            },
        }
        species_entries.append(entry)
        for conflict in row["conflicts_and_review"]:
            conflicts.append({"species": species, "issue": conflict})

    starter_pairs = [list(pair) for pair in itertools.combinations(STARTER_CHOICES, 2)]
    unavailable_starters = [species for species in STARTER_CHOICES if not encounters.get(species)]
    custom_registry_slice = registry[494:557]
    expected_custom_registry = [row["code_name"] for row in species_rows]
    core_checks = {
        "species_count_63": len(species_rows) == 63,
        "families_count_21": len({row["family_index"] for row in species_rows}) == 21,
        "custom_registry_matches_manifest": custom_registry_slice == expected_custom_registry,
        "logical_sprite_slots_252": len(sprites) == 252 and all(row["present"] for row in sprites),
        "custom_cries_63": cries["source_wav_count"] == 63
        and cries["all_species_slots_registered"],
        "shaymin_sky_reindexed_after_custom_species": cries["shaymin_sky_slots"] == [557],
        "fairy_has_offensive_moves": len(fairy) >= 4,
        "all_six_starter_choices_recoverable": not unavailable_starters,
        "all_audits_pass": all(row["passed"] for row in audits.values()),
    }
    release_checks = {
        "built_rom_present": built_rom["present"],
        "built_rom_has_ds_capacity": built_rom.get("size") == BASE_ROM["size"],
        "bps_patch_present": bps_patch["present"] and bps_patch.get("size", 0) > 0,
        "bps_round_trip_matches_built_rom": bps_round_trip["passed"],
        "emulator_boot_verified": emulator_evidence["passed"],
    }

    report = {
        "schema": "beacondex-platinum-integration-report-v1",
        "source_commit": source_commit(),
        "exact_patch_base": BASE_ROM,
        "registry": {
            "original_species_ids_preserved": registry[493] == "SPECIES_ARCEUS",
            "custom_id_range": [494, 556],
            "custom_species_count": len(species_rows),
            "family_count": len({row["family_index"] for row in species_rows}),
            "egg_id": registry.index("SPECIES_EGG"),
            "bad_egg_id": registry.index("SPECIES_BAD_EGG"),
            "custom_registry_matches_manifest": custom_registry_slice == expected_custom_registry,
            "species": species_entries,
        },
        "graphics": {
            "logical_battle_sprite_slot_count": len(sprites),
            "all_logical_slots_present": all(row["present"] for row in sprites),
            "battle_sprite_slots": sprites,
            "supplied_icons": 27,
            "generated_icons": 36,
            "supplied_footprints": 27,
            "generated_footprints": 36,
            "animation_policy": "two runtime frames currently duplicate the supplied draft pose",
        },
        "audio": cries,
        "save_layout": {
            "pokedex_bytes": 900,
            "normal_block": {
                "bytes": 53_132,
                "sectors": 13,
                "capacity": 53_248,
                "free": 116,
            },
            "pc_block": {
                "bytes": 74_212,
                "sectors": 19,
                "capacity": 77_824,
                "free": 3_612,
            },
            "main_save_sector_budget": 32,
            "battle_hall_page": {
                "bytes_including_footer": 3_372,
                "capacity": 4_096,
                "free": 724,
            },
            "fresh_saves_supported": True,
            "vanilla_save_migration_supported": False,
        },
        "fairy": {
            "type_constant": "TYPE_FAIRY",
            "move_count": len(fairy),
            "moves": fairy,
        },
        "starters": {
            "choices": list(STARTER_CHOICES),
            "choose_count": 2,
            "distinct_required": True,
            "level": 5,
            "unordered_pair_count": len(starter_pairs),
            "unordered_pairs": starter_pairs,
            "selection_script": "res/field/scripts/scripts_route_201.s",
            "player_variables": ["VAR_PLAYER_STARTER", "VAR_PLAYER_SECOND_STARTER"],
            "rival_variables": ["VAR_RIVAL_STARTER", "VAR_RIVAL_SECOND_STARTER"],
            "static_recovery_encounters": {
                species: encounters.get(species, []) for species in STARTER_CHOICES
            },
            "all_choices_obtainable_outside_selection": not unavailable_starters,
            "choices_without_static_recovery_encounter": unavailable_starters,
        },
        "distribution": {
            "custom_wild_placements": wild_manifest["placements"],
            "custom_wild_species_count": len(wild_by_species),
            "starter_recovery_placements": starter_recovery,
            "all_modified_wild_map_count": len(
                {row["map"] for row in wild_manifest["placements"] + starter_recovery}
            ),
            "custom_trainer_assignments": list(trainers_by_species.values()),
            "custom_trainer_species_count": len(trainers_by_species),
        },
        "validation": {
            "static_validation_passed": all(core_checks.values()),
            "release_validation_passed": all(core_checks.values())
            and all(release_checks.values()),
            "core_checks": core_checks,
            "release_checks": release_checks,
            "audits": audits,
            "built_rom": built_rom,
            "bps_patch": bps_patch,
            "bps_round_trip": bps_round_trip,
            "emulator_boot_verified": emulator_evidence["passed"],
            "emulator_playthrough_completed": emulator_evidence.get("report", {}).get(
                "full_playthrough_completed", False
            ),
            "emulator_evidence": emulator_evidence,
        },
        "design_conflicts": conflicts,
        "known_limitations": [
            "Boot through the title animation is verified in melonDS and DeSmuME; a complete story playthrough has not been completed.",
            "Fresh saves are required; migration from a vanilla Platinum save has not been implemented or tested.",
            "The 252 battle images are draft art and use duplicated animation frames pending an in-emulator art pass.",
            "Thirty-six party icons and footprints are generated draft placeholders.",
            "BeaconDex cries use documented vanilla audio templates pending authored recordings.",
            "BeaconDex egg-move and tutor lists are empty pending a later content pass.",
            "Ordinary trainer teams retain audited ally-hit and legacy move warnings for emulator balance testing.",
            "English Pokédex text is copied into the other language banks as a technical fallback.",
        ],
    }
    return report


def main() -> int:
    args = parse_args()
    report = build_report(args.rom.resolve(), args.patch.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "output": str(args.output),
                "species": report["registry"]["custom_species_count"],
                "sprite_slots": report["graphics"]["logical_battle_sprite_slot_count"],
                "fairy_moves": report["fairy"]["move_count"],
                "static_validation_passed": report["validation"]["static_validation_passed"],
                "release_validation_passed": report["validation"]["release_validation_passed"],
            },
            indent=2,
        )
    )
    return 0 if report["validation"]["release_validation_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
