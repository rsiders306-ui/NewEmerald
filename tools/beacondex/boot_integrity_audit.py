#!/usr/bin/env python3
"""Audit boot-critical NDS header fields and SDAT payload offsets."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
REFERENCE_RAW_SECURE_CRC = 0xFA2A
REFERENCE_SECURE_CRC = 0xF8B8
SOUND_PATH = ("data", "sound", "pl_sound_data.sdat")
SOUND_MAGICS = {b"SSEQ", b"SSAR", b"SBNK", b"SWAR", b"STRM"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--rom",
        type=Path,
        default=REPO_ROOT / "build-cloud-r1" / "pokeplatinum.us.nds",
    )
    parser.add_argument(
        "--sdat",
        type=Path,
        default=REPO_ROOT / "build-cloud-r1" / "res" / "sound" / "pl_sound_data.sdat",
    )
    parser.add_argument("--report", type=Path)
    return parser.parse_args()


def u16(data: bytes, offset: int) -> int:
    return struct.unpack_from("<H", data, offset)[0]


def u32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def crc16(data: bytes, initial: int = 0xFFFF) -> int:
    crc = initial
    for value in data:
        crc ^= value
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc & 0xFFFF


def align(value: int, boundary: int) -> int:
    return (value + boundary - 1) & -boundary


def find_file_id(rom: bytes, components: tuple[str, ...]) -> int:
    fnt_offset = u32(rom, 0x40)
    fnt_size = u32(rom, 0x44)
    fnt = rom[fnt_offset : fnt_offset + fnt_size]
    directory = 0

    for component_index, component in enumerate(components):
        table_offset, first_file, _ = struct.unpack_from("<IHH", fnt, directory * 8)
        cursor = table_offset
        file_id = first_file
        found_directory: int | None = None

        while cursor < len(fnt) and fnt[cursor] != 0:
            descriptor = fnt[cursor]
            cursor += 1
            name_size = descriptor & 0x7F
            name = fnt[cursor : cursor + name_size].decode("ascii")
            cursor += name_size
            is_directory = bool(descriptor & 0x80)

            if is_directory:
                child = u16(fnt, cursor) & 0x0FFF
                cursor += 2
                if name == component and component_index < len(components) - 1:
                    found_directory = child
                    break
            else:
                if name == component and component_index == len(components) - 1:
                    return file_id
                file_id += 1

        if found_directory is None:
            raise ValueError(f"NitroFS path not found: {'/'.join(components)}")
        directory = found_directory

    raise ValueError(f"NitroFS path not found: {'/'.join(components)}")


def extract_file(rom: bytes, file_id: int) -> bytes:
    fat_offset = u32(rom, 0x48)
    fat_size = u32(rom, 0x4C)
    if (file_id + 1) * 8 > fat_size:
        raise ValueError(f"NitroFS file ID {file_id} is outside the FAT")
    start, end = struct.unpack_from("<II", rom, fat_offset + file_id * 8)
    if not (start <= end <= len(rom)):
        raise ValueError(f"NitroFS file ID {file_id} has invalid bounds")
    return rom[start:end]


def audit_sdat(data: bytes, failures: list[str]) -> dict[str, object]:
    result: dict[str, object] = {
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }
    if len(data) < 0x40 or data[:4] != b"SDAT":
        failures.append("sound archive is not an SDAT file")
        return result

    declared_size = u32(data, 0x08)
    header_size = u16(data, 0x0C)
    block_count = u16(data, 0x0E)
    if declared_size != len(data):
        failures.append(
            f"SDAT declares size {declared_size:#x}, actual size is {len(data):#x}"
        )
    if header_size < 0x10 or 0x10 + block_count * 8 > len(data):
        failures.append("SDAT block table is out of bounds")
        return result

    blocks: dict[bytes, tuple[int, int]] = {}
    for index in range(block_count):
        offset, size = struct.unpack_from("<II", data, 0x10 + index * 8)
        if offset + size > len(data) or size < 0x0C:
            failures.append(f"SDAT block {index} has invalid bounds")
            continue
        blocks[data[offset : offset + 4]] = (offset, size)

    if b"FAT " not in blocks or b"FILE" not in blocks:
        failures.append("SDAT is missing its FAT or FILE block")
        return result

    fat_offset, fat_size = blocks[b"FAT "]
    file_offset, file_size = blocks[b"FILE"]
    file_count = u32(data, fat_offset + 8)
    result.update(
        {
            "block_count": block_count,
            "file_count": file_count,
            "fat_offset": fat_offset,
            "file_offset": file_offset,
        }
    )
    if fat_size != 0x0C + file_count * 0x10:
        failures.append("SDAT FAT size does not match its file count")
        return result
    if file_count != 2135:
        failures.append(f"SDAT should contain 2,135 files, found {file_count}")

    cursor = align(file_offset + 0x0C, 0x20)
    magic_counts: dict[str, int] = {}
    layout_complete = True
    for file_id in range(file_count):
        entry = fat_offset + 0x0C + file_id * 0x10
        payload_offset, payload_size = struct.unpack_from("<II", data, entry)
        if payload_offset != cursor:
            failures.append(
                f"SDAT FAT[{file_id}] offset is {payload_offset:#x}; expected {cursor:#x}"
            )
            layout_complete = False
            break
        if payload_size < 4 or payload_offset + payload_size > len(data):
            failures.append(f"SDAT FAT[{file_id}] has invalid payload bounds")
            layout_complete = False
            break
        magic = data[payload_offset : payload_offset + 4]
        if magic not in SOUND_MAGICS:
            failures.append(
                f"SDAT FAT[{file_id}] points to invalid magic {magic.hex()}"
            )
            layout_complete = False
            break
        name = magic.decode("ascii")
        magic_counts[name] = magic_counts.get(name, 0) + 1
        cursor = align(payload_offset + payload_size, 0x20)

    if layout_complete and cursor != file_offset + file_size:
        failures.append(
            f"SDAT FILE payload ends at {cursor:#x}; block ends at {file_offset + file_size:#x}"
        )
    result["magic_counts"] = magic_counts
    return result


def main() -> int:
    args = parse_args()
    failures: list[str] = []
    rom_path = args.rom.resolve()
    sdat_path = args.sdat.resolve()
    if not rom_path.is_file():
        failures.append(f"ROM does not exist: {rom_path}")
        rom = b""
    else:
        rom = rom_path.read_bytes()

    header: dict[str, object] = {}
    embedded_sdat = b""
    file_id: int | None = None
    if rom:
        if len(rom) < 0x8000:
            failures.append("ROM is too small to contain an NDS secure area")
        else:
            arm9_offset = u32(rom, 0x20)
            raw_secure_crc = crc16(rom[arm9_offset : arm9_offset + 0x4000])
            expected_secure_crc = (
                REFERENCE_SECURE_CRC
                ^ REFERENCE_RAW_SECURE_CRC
                ^ raw_secure_crc
            )
            actual_secure_crc = u16(rom, 0x6C)
            expected_header_crc = crc16(rom[:0x15E])
            actual_header_crc = u16(rom, 0x15E)
            header = {
                "title": rom[:12].rstrip(b"\0").decode("ascii", errors="replace"),
                "game_code": rom[0x0C:0x10].decode("ascii", errors="replace"),
                "revision": rom[0x1E],
                "arm9_offset": arm9_offset,
                "raw_secure_crc": f"0x{raw_secure_crc:04X}",
                "secure_crc": f"0x{actual_secure_crc:04X}",
                "expected_secure_crc": f"0x{expected_secure_crc:04X}",
                "header_crc": f"0x{actual_header_crc:04X}",
                "expected_header_crc": f"0x{expected_header_crc:04X}",
            }
            if rom[:12].rstrip(b"\0") != b"POKEMON PL":
                failures.append("ROM title is not POKEMON PL")
            if rom[0x0C:0x10] != b"CPUE" or rom[0x1E] != 1:
                failures.append("ROM is not the US Rev 1 build")
            if actual_secure_crc != expected_secure_crc:
                failures.append(
                    f"secure-area CRC is {actual_secure_crc:#06x}; expected {expected_secure_crc:#06x}"
                )
            if actual_header_crc != expected_header_crc:
                failures.append(
                    f"header CRC is {actual_header_crc:#06x}; expected {expected_header_crc:#06x}"
                )

            try:
                file_id = find_file_id(rom, SOUND_PATH)
                embedded_sdat = extract_file(rom, file_id)
            except (UnicodeDecodeError, ValueError, struct.error) as error:
                failures.append(str(error))

    standalone_matches = False
    if not sdat_path.is_file():
        failures.append(f"built SDAT does not exist: {sdat_path}")
    elif embedded_sdat:
        standalone_matches = sdat_path.read_bytes() == embedded_sdat
        if not standalone_matches:
            failures.append("embedded SDAT does not match the generated build artifact")

    sdat = audit_sdat(embedded_sdat, failures) if embedded_sdat else {}
    report = {
        "schema": "beacondex-boot-integrity-audit-v1",
        "passed": not failures,
        "rom": {
            "path": str(rom_path),
            "size": len(rom),
            "sha256": hashlib.sha256(rom).hexdigest() if rom else None,
        },
        "header": header,
        "sound_archive_file_id": file_id,
        "standalone_sdat_matches": standalone_matches,
        "sdat": sdat,
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
