#!/usr/bin/env python3
"""Export an ELF symbol table in a stable, nm-like text format."""

from __future__ import annotations

import argparse
from pathlib import Path

from elftools.elf.constants import SH_FLAGS
from elftools.elf.elffile import ELFFile


def symbol_type(symbol, elf: ELFFile) -> str:
    bind = symbol.entry["st_info"]["bind"]
    section_index = symbol.entry["st_shndx"]

    if bind == "STB_WEAK":
        letter = "W"
    elif section_index == "SHN_UNDEF":
        letter = "U"
    elif section_index == "SHN_ABS":
        letter = "A"
    elif isinstance(section_index, int):
        section = elf.get_section(section_index)
        flags = section["sh_flags"]
        if flags & SH_FLAGS.SHF_EXECINSTR:
            letter = "T"
        elif section["sh_type"] == "SHT_NOBITS":
            letter = "B"
        elif flags & SH_FLAGS.SHF_WRITE:
            letter = "D"
        else:
            letter = "R"
    else:
        letter = "N"

    return letter.lower() if bind == "STB_LOCAL" else letter


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    with args.input.open("rb") as stream:
        elf = ELFFile(stream)
        symtab = elf.get_section_by_name(".symtab")
        if symtab is None:
            raise SystemExit("input ELF has no .symtab section")

        rows = []
        for symbol in symtab.iter_symbols():
            if symbol.name:
                rows.append(
                    (symbol.entry["st_value"], symbol_type(symbol, elf), symbol.name)
                )

    rows.sort(key=lambda row: (row[0], row[2]))
    with args.output.open("w", encoding="utf-8", newline="\n") as stream:
        for address, kind, name in rows:
            stream.write(f"{address:016x} {kind} {name}\n")

    print(f"wrote {len(rows)} symbols to {args.output}")


if __name__ == "__main__":
    main()
