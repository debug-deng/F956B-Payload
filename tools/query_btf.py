#!/usr/bin/env python3
"""Query structure layouts from a standalone raw BTF blob."""

from __future__ import annotations

import argparse
import struct
from dataclasses import dataclass
from pathlib import Path


@dataclass
class BtfType:
    type_id: int
    name: str
    kind: int
    kind_flag: bool
    vlen: int
    size_or_type: int
    members: list[tuple[str, int, int, int]]


KIND_NAMES = {
    0: "UNKNOWN",
    1: "INT",
    2: "PTR",
    3: "ARRAY",
    4: "STRUCT",
    5: "UNION",
    6: "ENUM",
    7: "FWD",
    8: "TYPEDEF",
    9: "VOLATILE",
    10: "CONST",
    11: "RESTRICT",
    12: "FUNC",
    13: "FUNC_PROTO",
    14: "VAR",
    15: "DATASEC",
    16: "FLOAT",
    17: "DECL_TAG",
    18: "TYPE_TAG",
    19: "ENUM64",
}


def string_at(strings: bytes, offset: int) -> str:
    if offset >= len(strings):
        raise ValueError(f"string offset out of range: {offset}")
    end = strings.find(b"\0", offset)
    if end < 0:
        raise ValueError(f"unterminated string at offset: {offset}")
    return strings[offset:end].decode("utf-8", errors="replace")


def parse_btf(path: Path) -> list[BtfType]:
    data = path.read_bytes()
    if len(data) < 24:
        raise ValueError("BTF blob is shorter than its fixed header")

    magic, version, flags, header_len, type_off, type_len, str_off, str_len = (
        struct.unpack_from("<HBBIIIII", data)
    )
    if magic != 0xEB9F or version != 1 or flags != 0 or header_len < 24:
        raise ValueError("unsupported or invalid BTF header")

    type_start = header_len + type_off
    type_end = type_start + type_len
    str_start = header_len + str_off
    str_end = str_start + str_len
    if type_end > len(data) or str_end > len(data):
        raise ValueError("BTF section exceeds file bounds")
    strings = data[str_start:str_end]

    extra_sizes = {
        0: lambda vlen: 0,
        1: lambda vlen: 4,
        2: lambda vlen: 0,
        3: lambda vlen: 12,
        4: lambda vlen: 12 * vlen,
        5: lambda vlen: 12 * vlen,
        6: lambda vlen: 8 * vlen,
        7: lambda vlen: 0,
        8: lambda vlen: 0,
        9: lambda vlen: 0,
        10: lambda vlen: 0,
        11: lambda vlen: 0,
        12: lambda vlen: 0,
        13: lambda vlen: 8 * vlen,
        14: lambda vlen: 4,
        15: lambda vlen: 12 * vlen,
        16: lambda vlen: 0,
        17: lambda vlen: 4,
        18: lambda vlen: 0,
        19: lambda vlen: 12 * vlen,
    }

    types = []
    cursor = type_start
    type_id = 1
    while cursor < type_end:
        if cursor + 12 > type_end:
            raise ValueError("truncated BTF type header")
        name_off, info, size_or_type = struct.unpack_from("<III", data, cursor)
        cursor += 12
        kind = (info >> 24) & 0x1F
        kind_flag = bool(info >> 31)
        vlen = info & 0xFFFF
        if kind not in extra_sizes:
            raise ValueError(f"unsupported BTF kind {kind} for type {type_id}")
        extra_size = extra_sizes[kind](vlen)
        if cursor + extra_size > type_end:
            raise ValueError(f"truncated payload for BTF type {type_id}")

        members = []
        if kind in (4, 5):
            for index in range(vlen):
                member_name_off, member_type, raw_offset = struct.unpack_from(
                    "<III", data, cursor + index * 12
                )
                bitfield_size = raw_offset >> 24 if kind_flag else 0
                bit_offset = raw_offset & 0xFFFFFF if kind_flag else raw_offset
                members.append(
                    (
                        string_at(strings, member_name_off),
                        member_type,
                        bit_offset,
                        bitfield_size,
                    )
                )

        types.append(
            BtfType(
                type_id=type_id,
                name=string_at(strings, name_off),
                kind=kind,
                kind_flag=kind_flag,
                vlen=vlen,
                size_or_type=size_or_type,
                members=members,
            )
        )
        cursor += extra_size
        type_id += 1

    if cursor != type_end:
        raise ValueError("BTF type section did not end on a record boundary")
    return types


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("btf", type=Path)
    parser.add_argument("names", nargs="+")
    args = parser.parse_args()

    types = parse_btf(args.btf)
    wanted = set(args.names)
    matches = [item for item in types if item.name in wanted]
    by_id = {item.type_id: item for item in types}
    for name in args.names:
        if name.startswith("#"):
            try:
                type_id = int(name[1:], 0)
            except ValueError:
                raise SystemExit(f"invalid BTF type id: {name}") from None
            named = [by_id[type_id]] if type_id in by_id else []
        else:
            named = [item for item in matches if item.name == name]
        if not named:
            print(f"{name}: NOT FOUND")
            continue
        for item in named:
            kind = KIND_NAMES.get(item.kind, str(item.kind))
            if item.kind not in (4, 5):
                print(
                    f"{name}: id={item.type_id} kind={kind} "
                    f"size_or_type={item.size_or_type}"
                )
                continue
            print(
                f"{name}: id={item.type_id} kind={kind} "
                f"size=0x{item.size_or_type:x}"
            )
            for member_name, member_type, bit_offset, bitfield_size in item.members:
                suffix = f" bitfield={bitfield_size}" if bitfield_size else ""
                byte_offset = (
                    f"0x{bit_offset // 8:x}"
                    if bit_offset % 8 == 0
                    else "not-byte-aligned"
                )
                print(
                    f"  {member_name}: type={member_type} "
                    f"bits_offset={bit_offset} byte_offset={byte_offset}{suffix}"
                )


if __name__ == "__main__":
    main()
