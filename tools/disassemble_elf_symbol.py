#!/usr/bin/env python3
"""Disassemble one AArch64 ELF symbol using pyelftools and Capstone."""

from __future__ import annotations

import argparse
from pathlib import Path

from capstone import CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN, Cs
from elftools.elf.elffile import ELFFile


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("elf", type=Path)
    parser.add_argument("symbol")
    parser.add_argument("--max-bytes", type=lambda value: int(value, 0), default=0x800)
    args = parser.parse_args()

    with args.elf.open("rb") as stream:
        elf = ELFFile(stream)
        symtab = elf.get_section_by_name(".symtab")
        if symtab is None:
            raise SystemExit("input ELF has no .symtab section")

        matches = [symbol for symbol in symtab.iter_symbols() if symbol.name == args.symbol]
        if not matches:
            raise SystemExit(f"symbol not found: {args.symbol}")
        symbol = matches[0]
        section_index = symbol.entry["st_shndx"]
        if not isinstance(section_index, int):
            raise SystemExit(f"symbol has no file-backed section: {args.symbol}")

        section = elf.get_section(section_index)
        address = symbol.entry["st_value"]
        size = symbol.entry["st_size"]
        if size == 0:
            next_addresses = [
                candidate.entry["st_value"]
                for candidate in symtab.iter_symbols()
                if candidate.entry["st_shndx"] == section_index
                and candidate.entry["st_value"] > address
            ]
            if next_addresses:
                size = min(next_addresses) - address
        size = min(size or args.max_bytes, args.max_bytes)

        file_offset = section["sh_offset"] + address - section["sh_addr"]
        stream.seek(file_offset)
        code = stream.read(size)

    decoder = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)
    print(f"{args.symbol}: address=0x{address:x} size=0x{size:x}")
    for instruction in decoder.disasm(code, address):
        print(
            f"0x{instruction.address:016x}: "
            f"{instruction.mnemonic:<9} {instruction.op_str}"
        )


if __name__ == "__main__":
    main()
