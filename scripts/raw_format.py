#!/usr/bin/env python3

from __future__ import annotations

import csv
import lzma
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, List, Tuple

MAGIC = b"LLR1"
VERSION = 1

UNIT_NAMES = ("ns", "us", "ms", "s")
UNIT_ENUM = {name: idx for idx, name in enumerate(UNIT_NAMES)}
UNIT_SCALE_NS = {
    "ns": 1,
    "us": 1_000,
    "ms": 1_000_000,
    "s": 1_000_000_000,
}


@dataclass
class RawHeader:
    case_name: str
    tags: List[str]
    args: List[str]
    iters: int
    warmup: int
    pin_cpu: int
    unit: str
    sample_count: int


def choose_unit_from_min(min_ns: int) -> str:
    if min_ns >= 100_000_000_000:
        return "s"
    if min_ns >= 100_000_000:
        return "ms"
    if min_ns >= 100_000:
        return "us"
    return "ns"


def read_raw_csv_samples(path: Path) -> Iterable[int]:
    with path.open(newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader, None)
        for row in reader:
            if not row:
                continue
            if len(row) < 2:
                raise ValueError(f"invalid raw.csv row: {row}")
            yield int(row[1])


def _scan_raw_csv(path: Path) -> Tuple[int, int]:
    min_ns = None
    count = 0
    for value in read_raw_csv_samples(path):
        count += 1
        if min_ns is None or value < min_ns:
            min_ns = value
    if min_ns is None:
        min_ns = 0
    return min_ns, count


def read_raw_csv_list(path: Path) -> List[int]:
    return list(read_raw_csv_samples(path))


def _zigzag_encode(value: int) -> int:
    if value < -(1 << 63) or value > (1 << 63) - 1:
        raise ValueError("delta out of int64 range")
    return (value << 1) ^ (value >> 63)


def _zigzag_decode(value: int) -> int:
    return (value >> 1) ^ -(value & 1)


def _write_varint(value: int, buffer: bytearray) -> None:
    if value < 0:
        raise ValueError("varint expects unsigned value")
    while True:
        chunk = value & 0x7F
        value >>= 7
        if value:
            buffer.append(chunk | 0x80)
        else:
            buffer.append(chunk)
            return


def _read_varint(data: bytes, offset: int) -> Tuple[int, int]:
    value = 0
    shift = 0
    while True:
        if offset >= len(data):
            raise ValueError("truncated varint")
        byte = data[offset]
        offset += 1
        value |= (byte & 0x7F) << shift
        if not (byte & 0x80):
            return value, offset
        shift += 7
        if shift > 70:
            raise ValueError("varint too large")


def _write_header(handle, header: RawHeader) -> None:
    case_bytes = header.case_name.encode("utf-8")
    tag_bytes = [tag.encode("utf-8") for tag in header.tags]
    arg_bytes = [arg.encode("utf-8") for arg in header.args]
    handle.write(MAGIC)
    handle.write(struct.pack("<BBH", VERSION, UNIT_ENUM[header.unit], 0))
    handle.write(
        struct.pack(
            "<QQQiI",
            header.sample_count,
            header.iters,
            header.warmup,
            header.pin_cpu,
            len(tag_bytes),
        )
    )
    handle.write(struct.pack("<I", len(case_bytes)))
    handle.write(case_bytes)
    for tag in tag_bytes:
        handle.write(struct.pack("<I", len(tag)))
        handle.write(tag)
    handle.write(struct.pack("<I", len(arg_bytes)))
    for arg in arg_bytes:
        handle.write(struct.pack("<I", len(arg)))
        handle.write(arg)


def _read_header(handle) -> RawHeader:
    magic = handle.read(4)
    if magic != MAGIC:
        raise ValueError("invalid raw file magic")
    header_bytes = handle.read(4)
    if len(header_bytes) != 4:
        raise ValueError("truncated raw header")
    version, unit_enum, _reserved = struct.unpack("<BBH", header_bytes)
    if version != VERSION:
        raise ValueError(f"unsupported raw version: {version}")
    if unit_enum >= len(UNIT_NAMES):
        raise ValueError(f"invalid unit enum: {unit_enum}")
    unit = UNIT_NAMES[unit_enum]
    fixed = handle.read(32)
    if len(fixed) != 32:
        raise ValueError("truncated raw header")
    sample_count, iters, warmup, pin_cpu, tag_count = struct.unpack(
        "<QQQiI", fixed
    )
    case_len_bytes = handle.read(4)
    if len(case_len_bytes) != 4:
        raise ValueError("truncated raw header")
    (case_len,) = struct.unpack("<I", case_len_bytes)
    case_bytes = handle.read(case_len)
    if len(case_bytes) != case_len:
        raise ValueError("truncated case name")
    tags = []
    for _ in range(tag_count):
        tag_len_bytes = handle.read(4)
        if len(tag_len_bytes) != 4:
            raise ValueError("truncated tag length")
        (tag_len,) = struct.unpack("<I", tag_len_bytes)
        tag_bytes = handle.read(tag_len)
        if len(tag_bytes) != tag_len:
            raise ValueError("truncated tag")
        tags.append(tag_bytes.decode("utf-8"))
    arg_count_bytes = handle.read(4)
    if len(arg_count_bytes) != 4:
        raise ValueError("truncated arg count")
    (arg_count,) = struct.unpack("<I", arg_count_bytes)
    args = []
    for _ in range(arg_count):
        arg_len_bytes = handle.read(4)
        if len(arg_len_bytes) != 4:
            raise ValueError("truncated arg length")
        (arg_len,) = struct.unpack("<I", arg_len_bytes)
        arg_bytes = handle.read(arg_len)
        if len(arg_bytes) != arg_len:
            raise ValueError("truncated arg")
        args.append(arg_bytes.decode("utf-8"))
    return RawHeader(
        case_name=case_bytes.decode("utf-8"),
        tags=tags,
        args=args,
        iters=iters,
        warmup=warmup,
        pin_cpu=pin_cpu,
        unit=unit,
        sample_count=sample_count,
    )


def _encode_samples(
    samples: Iterable[int],
    handle,
    unit: str,
) -> None:
    scale = UNIT_SCALE_NS[unit]
    prev = 0
    buffer = bytearray()
    for ns_value in samples:
        scaled = (ns_value + (scale // 2)) // scale
        delta = scaled - prev
        prev = scaled
        encoded = _zigzag_encode(delta)
        _write_varint(encoded, buffer)
        if len(buffer) >= 64 * 1024:
            handle.write(buffer)
            buffer.clear()
    if buffer:
        handle.write(buffer)


def encode_samples_to_llr(
    samples: List[int],
    out_path: Path,
    header: RawHeader,
    unit: str = "auto",
) -> RawHeader:
    if unit == "auto":
        min_ns = min(samples) if samples else 0
        unit = choose_unit_from_min(min_ns)
    if unit not in UNIT_ENUM:
        raise ValueError(f"unknown unit: {unit}")
    header.unit = unit
    header.sample_count = len(samples)
    preset = 9 | lzma.PRESET_EXTREME

    with lzma.open(out_path, "wb", preset=preset) as handle:
        _write_header(handle, header)
        _encode_samples(samples, handle, unit)

    return header


def encode_raw_csv_to_llr(
    raw_csv_path: Path,
    out_path: Path,
    header: RawHeader,
    unit: str = "auto",
) -> RawHeader:
    min_ns, count = _scan_raw_csv(raw_csv_path)
    if unit == "auto":
        unit = choose_unit_from_min(min_ns)
    if unit not in UNIT_ENUM:
        raise ValueError(f"unknown unit: {unit}")
    header.unit = unit
    header.sample_count = count

    scale = UNIT_SCALE_NS[unit]
    preset = 9 | lzma.PRESET_EXTREME

    with lzma.open(out_path, "wb", preset=preset) as handle:
        _write_header(handle, header)
        _encode_samples(read_raw_csv_samples(raw_csv_path), handle, unit)

    return header


def iter_llr_samples(path: Path, unit: str = "ns") -> Iterator[int]:
    with lzma.open(path, "rb") as handle:
        header = _read_header(handle)
        payload = handle.read()
    if unit not in UNIT_ENUM:
        raise ValueError(f"unknown unit: {unit}")
    from_scale = UNIT_SCALE_NS[header.unit]
    to_scale = UNIT_SCALE_NS[unit]
    if to_scale == 0:
        raise ValueError("invalid unit scale")

    offset = 0
    prev = 0
    count = 0
    while offset < len(payload) and count < header.sample_count:
        raw_value, offset = _read_varint(payload, offset)
        delta = _zigzag_decode(raw_value)
        prev += delta
        count += 1
        ns_value = prev * from_scale
        yield (ns_value + (to_scale // 2)) // to_scale


def read_llr(path: Path, unit: str = "ns") -> Tuple[RawHeader, List[int]]:
    with lzma.open(path, "rb") as handle:
        header = _read_header(handle)
        payload = handle.read()
    if unit not in UNIT_ENUM:
        raise ValueError(f"unknown unit: {unit}")
    from_scale = UNIT_SCALE_NS[header.unit]
    to_scale = UNIT_SCALE_NS[unit]
    samples: List[int] = []
    offset = 0
    prev = 0
    while offset < len(payload) and len(samples) < header.sample_count:
        raw_value, offset = _read_varint(payload, offset)
        delta = _zigzag_decode(raw_value)
        prev += delta
        ns_value = prev * from_scale
        samples.append((ns_value + (to_scale // 2)) // to_scale)
    return header, samples
