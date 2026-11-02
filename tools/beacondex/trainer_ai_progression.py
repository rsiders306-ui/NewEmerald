#!/usr/bin/env python3
"""Apply and audit the additive whole-game Trainer AI progression policy."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
TRAINER_ROOT = ROOT / "res/trainers/data"
BASELINE_MANIFEST = ROOT / "data/beacondex/trainer_balance_rosters.json"
AI_FLAGS = (ROOT / "generated/ai_flags.txt").read_text(encoding="utf-8").splitlines()
AI_ORDER = {flag: index for index, flag in enumerate(AI_FLAGS)}
EXPECTED_CATEGORIES = {
    "sentinel": 1,
    "active": 723,
    "dummy": 185,
    "unused": 19,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="write the additive policy to trainer JSON before auditing",
    )
    parser.add_argument("--report", type=Path, help="write the full JSON report here")
    return parser.parse_args()


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def category(stem: str) -> str:
    if stem == "none":
        return "sentinel"
    if "dummy" in stem:
        return "dummy"
    if "unused" in stem:
        return "unused"
    return "active"


def max_level(record: dict[str, Any]) -> int:
    return max((member["level"] for member in record["party"]), default=0)


def required_flags(record: dict[str, Any]) -> set[str]:
    required = {"AI_FLAG_BASIC"}
    level = max_level(record)
    if level >= 20:
        required.add("AI_FLAG_EVAL_ATTACK")
    if level >= 35:
        required.add("AI_FLAG_EXPERT")
    return required


def canonical(flags: set[str]) -> list[str]:
    return sorted(flags, key=AI_ORDER.__getitem__)


def uniform_party_encoding(record: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    items = [member["item"] for member in record["party"]]
    moves = [member["moves"] for member in record["party"]]
    if items and not (all(item is None for item in items) or all(isinstance(item, str) for item in items)):
        failures.append("mixed held-item archive encoding")
    if moves and not (all(move is None for move in moves) or all(isinstance(move, list) for move in moves)):
        failures.append("mixed move archive encoding")
    return failures


def main() -> int:
    args = parse_args()
    paths = sorted(TRAINER_ROOT.glob("*.json"))
    changed: list[str] = []

    if args.apply:
        for path in paths:
            record = load(path)
            if category(path.stem) != "active":
                continue
            updated = canonical(set(record["ai_flags"]) | required_flags(record))
            if updated == record["ai_flags"]:
                continue
            record["ai_flags"] = updated
            path.write_text(
                json.dumps(record, ensure_ascii=False, indent=4) + "\n",
                encoding="utf-8",
            )
            changed.append(path.stem)

    categories: Counter[str] = Counter()
    failures: list[str] = []
    additions = Counter()
    policy_additions = Counter()
    policy_upgraded_records: list[str] = []
    baseline_flags_preserved = True
    excluded_records_unchanged = True
    records = []
    baseline_records = load(BASELINE_MANIFEST).get("records", {})
    if set(baseline_records) != {path.stem for path in paths}:
        failures.append("trainer AI baseline inventory differs from current resources")
    for path in paths:
        record = load(path)
        record_category = category(path.stem)
        categories[record_category] += 1
        record_failures = uniform_party_encoding(record)
        flags = record["ai_flags"]
        baseline_flags_list = baseline_records.get(path.stem, {}).get("ai_flags", [])
        baseline_flags = set(baseline_flags_list)
        unknown = sorted(set(flags) - set(AI_FLAGS))
        if unknown:
            record_failures.append(f"unknown AI flags: {unknown}")
        if len(flags) != len(set(flags)):
            record_failures.append("duplicate AI flags")
        if not unknown and flags != canonical(set(flags)):
            record_failures.append("AI flags are not in canonical order")

        required: set[str] = set()
        if record_category == "active":
            removed_authored = sorted(baseline_flags - set(flags), key=AI_ORDER.__getitem__)
            if removed_authored:
                baseline_flags_preserved = False
                record_failures.append(f"authored baseline AI flags were removed: {removed_authored}")
            required = required_flags(record)
            baseline_additions = required - baseline_flags
            if baseline_additions:
                policy_upgraded_records.append(path.stem)
                policy_additions.update(baseline_additions)
            missing = sorted(required - set(flags), key=AI_ORDER.__getitem__)
            for flag in missing:
                additions[flag] += 1
            if missing:
                record_failures.append(f"missing progression AI flags: {missing}")
        elif flags != baseline_flags_list:
            excluded_records_unchanged = False
            record_failures.append("excluded sentinel/dummy/unused AI flags changed from baseline")

        if record_failures:
            failures.extend(f"{path.stem}: {failure}" for failure in record_failures)
        records.append(
            {
                "trainer": path.stem,
                "category": record_category,
                "max_level": max_level(record),
                "flags": flags,
                "required_flags": canonical(required) if required else [],
                "violations": record_failures,
            }
        )

    if dict(categories) != EXPECTED_CATEGORIES:
        failures.append(
            f"trainer category inventory changed: expected {EXPECTED_CATEGORIES}, found {dict(categories)}"
        )

    ai_source = (ROOT / "src/battle/trainer_ai/trainer_ai.c").read_text(encoding="utf-8")
    runtime_tag_strategy = (
        "if (battleSys->battleType & BATTLE_TYPE_DOUBLES)" in ai_source
        and "AI_CONTEXT.thinkingMask |= AI_FLAG_TAG_STRATEGY;" in ai_source
    )
    if not runtime_tag_strategy:
        failures.append("Double Battles no longer enable AI_FLAG_TAG_STRATEGY at runtime")

    report = {
        "schema": "beacondex-trainer-ai-progression-v1",
        "passed": not failures,
        "policy": {
            "active_level_20": ["AI_FLAG_BASIC", "AI_FLAG_EVAL_ATTACK"],
            "active_level_35": [
                "AI_FLAG_BASIC",
                "AI_FLAG_EVAL_ATTACK",
                "AI_FLAG_EXPERT",
            ],
            "existing_flags_preserved": baseline_flags_preserved,
            "dummy_and_unused_records_excluded": excluded_records_unchanged,
            "tag_strategy_added_by_runtime": runtime_tag_strategy,
        },
        "coverage": {
            "trainer_records": len(paths),
            "categories": dict(categories),
            "records_checked": len(records),
            "records_changed_by_apply": len(changed),
            "policy_upgraded_records": len(policy_upgraded_records),
            "policy_flags_added": sum(policy_additions.values()),
            "policy_flag_additions": dict(policy_additions),
            "remaining_required_additions": dict(additions),
        },
        "changed_records": changed,
        "policy_upgraded_record_names": policy_upgraded_records,
        "failures": failures,
        "records": records,
    }
    output = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(output, encoding="utf-8")
    print(output, end="")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
