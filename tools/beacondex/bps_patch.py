#!/usr/bin/env python3
"""Create, apply, and verify BPS patches without external dependencies."""

from __future__ import annotations

import argparse
import struct
import zlib
from pathlib import Path


BPS_MAGIC = b"BPS1"
SOURCE_READ = 0
TARGET_READ = 1
SOURCE_COPY = 2


def encode_number(value: int) -> bytes:
    if value < 0:
        raise ValueError("BPS numbers must be nonnegative")
    encoded = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value == 0:
            encoded.append(byte | 0x80)
            return bytes(encoded)
        encoded.append(byte)
        value -= 1


def decode_number(data: bytes, offset: int) -> tuple[int, int]:
    value = 0
    shift = 1
    while True:
        if offset >= len(data):
            raise ValueError("truncated BPS number")
        byte = data[offset]
        offset += 1
        value += (byte & 0x7F) * shift
        if byte & 0x80:
            return value, offset
        shift <<= 7
        value += shift


def encode_signed(value: int) -> bytes:
    encoded = (abs(value) << 1) | (1 if value < 0 else 0)
    return encode_number(encoded)


def append_read_action(
    patch: bytearray,
    mode: int,
    target: memoryview,
    start: int,
    end: int,
) -> None:
    if end <= start:
        return
    patch.extend(encode_number((((end - start) - 1) << 2) | mode))
    if mode == TARGET_READ:
        patch.extend(target[start:end])


def longest_match(
    source: memoryview,
    target: memoryview,
    source_start: int,
    target_start: int,
) -> int:
    maximum = min(len(source) - source_start, len(target) - target_start)
    matched = 0
    for chunk_size in (65536, 1024, 64, 1):
        while matched + chunk_size <= maximum:
            source_chunk = source[source_start + matched : source_start + matched + chunk_size]
            target_chunk = target[target_start + matched : target_start + matched + chunk_size]
            if source_chunk != target_chunk:
                break
            matched += chunk_size
    return matched


def create_patch(source: bytes, target: bytes, block_size: int = 64) -> bytes:
    if block_size < 16 or block_size % 4:
        raise ValueError("block size must be a multiple of four and at least 16")

    patch = bytearray(BPS_MAGIC)
    patch.extend(encode_number(len(source)))
    patch.extend(encode_number(len(target)))
    patch.extend(encode_number(0))  # no metadata

    source_view = memoryview(source)
    target_view = memoryview(target)
    seed_size = 16
    source_index = {
        zlib.crc32(source_view[position : position + seed_size]): position
        for position in range(0, len(source) - seed_size + 1, block_size)
    }

    position = 0
    literal_start = 0
    source_relative = 0
    minimum_match = block_size

    while position < len(target):
        remaining = len(target) - position
        match_length = 0
        match_source = -1

        if (
            remaining >= seed_size
            and position + seed_size <= len(source)
            and source_view[position : position + seed_size]
            == target_view[position : position + seed_size]
        ):
            match_length = longest_match(
                source_view, target_view, position, position
            )
            match_source = position

        if match_length < minimum_match and remaining >= seed_size:
            key = zlib.crc32(target_view[position : position + seed_size])
            candidate = source_index.get(key)
            if (
                candidate is not None
                and source_view[candidate : candidate + seed_size]
                == target_view[position : position + seed_size]
            ):
                candidate_length = longest_match(
                    source_view, target_view, candidate, position
                )
                if candidate_length > match_length:
                    match_length = candidate_length
                    match_source = candidate

        if match_length >= minimum_match:
            append_read_action(
                patch, TARGET_READ, target_view, literal_start, position
            )
            if match_source == position:
                append_read_action(
                    patch, SOURCE_READ, target_view, position, position + match_length
                )
            else:
                patch.extend(
                    encode_number(((match_length - 1) << 2) | SOURCE_COPY)
                )
                patch.extend(encode_signed(match_source - source_relative))
                source_relative = match_source + match_length
            position += match_length
            literal_start = position
        else:
            position += min(4, remaining)

    append_read_action(patch, TARGET_READ, target_view, literal_start, position)

    patch.extend(struct.pack("<I", zlib.crc32(source)))
    patch.extend(struct.pack("<I", zlib.crc32(target)))
    patch.extend(struct.pack("<I", zlib.crc32(patch)))
    return bytes(patch)


def apply_patch(source: bytes, patch: bytes) -> bytes:
    if len(patch) < 16 or not patch.startswith(BPS_MAGIC):
        raise ValueError("not a BPS patch")
    source_crc, target_crc, patch_crc = struct.unpack("<III", patch[-12:])
    if zlib.crc32(patch[:-4]) != patch_crc:
        raise ValueError("BPS patch checksum mismatch")
    if zlib.crc32(source) != source_crc:
        raise ValueError("source file checksum mismatch")

    offset = len(BPS_MAGIC)
    source_size, offset = decode_number(patch, offset)
    target_size, offset = decode_number(patch, offset)
    metadata_size, offset = decode_number(patch, offset)
    if source_size != len(source):
        raise ValueError(f"source size is {len(source)}, expected {source_size}")
    offset += metadata_size
    action_end = len(patch) - 12
    output = bytearray()
    source_relative = 0
    target_relative = 0

    while len(output) < target_size:
        if offset >= action_end:
            raise ValueError("truncated BPS action stream")
        action, offset = decode_number(patch, offset)
        mode = action & 3
        length = (action >> 2) + 1
        if mode == SOURCE_READ:
            start = len(output)
            end = start + length
            if end > len(source):
                raise ValueError("source-read action exceeds source size")
            output.extend(source[start:end])
        elif mode == TARGET_READ:
            end = offset + length
            if end > action_end:
                raise ValueError("target-read action exceeds patch data")
            output.extend(patch[offset:end])
            offset = end
        elif mode == 2:  # SourceCopy, supported for third-party BPS patches
            encoded, offset = decode_number(patch, offset)
            source_relative += -(encoded >> 1) if encoded & 1 else encoded >> 1
            end = source_relative + length
            if source_relative < 0 or end > len(source):
                raise ValueError("source-copy action exceeds source size")
            output.extend(source[source_relative:end])
            source_relative = end
        else:  # TargetCopy
            encoded, offset = decode_number(patch, offset)
            target_relative += -(encoded >> 1) if encoded & 1 else encoded >> 1
            if target_relative < 0 or target_relative >= len(output):
                raise ValueError("invalid target-copy offset")
            for _ in range(length):
                output.append(output[target_relative])
                target_relative += 1

    if len(output) != target_size or offset != action_end:
        raise ValueError("BPS action stream has an invalid final size")
    if zlib.crc32(output) != target_crc:
        raise ValueError("target file checksum mismatch")
    return bytes(output)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    create = subparsers.add_parser("create", help="create and self-verify a patch")
    create.add_argument("source", type=Path)
    create.add_argument("target", type=Path)
    create.add_argument("patch", type=Path)
    create.add_argument("--block-size", type=int, default=64)

    apply = subparsers.add_parser("apply", help="apply a BPS patch")
    apply.add_argument("source", type=Path)
    apply.add_argument("patch", type=Path)
    apply.add_argument("output", type=Path)

    verify = subparsers.add_parser("verify", help="verify a patch against a target")
    verify.add_argument("source", type=Path)
    verify.add_argument("target", type=Path)
    verify.add_argument("patch", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = args.source.read_bytes()
    if args.command == "create":
        target = args.target.read_bytes()
        patch = create_patch(source, target, args.block_size)
        if apply_patch(source, patch) != target:
            raise RuntimeError("new patch failed its reconstruction check")
        args.patch.parent.mkdir(parents=True, exist_ok=True)
        args.patch.write_bytes(patch)
        print(f"wrote {len(patch)} bytes to {args.patch}")
    elif args.command == "apply":
        output = apply_patch(source, args.patch.read_bytes())
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(output)
        print(f"wrote {len(output)} bytes to {args.output}")
    else:
        target = args.target.read_bytes()
        output = apply_patch(source, args.patch.read_bytes())
        if output != target:
            raise RuntimeError("patch output differs from expected target")
        print("BPS patch reconstructs the expected target byte-for-byte")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
