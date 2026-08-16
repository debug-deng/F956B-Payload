#!/usr/bin/env python3
"""Generate p0_fingerprint.h from a raw kernel Image."""

from __future__ import annotations

import argparse
from pathlib import Path


PAGE_OFFSETS = (0x000, 0x200, 0x400, 0x600, 0x800, 0xA00, 0xC00, 0xE00)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate p0_fingerprint.h from a raw kernel Image."
    )
    parser.add_argument("raw_image", type=Path)
    parser.add_argument("probe_offset")
    parser.add_argument("output_header", type=Path)
    return parser.parse_args()


def parse_probe(text: str) -> int:
    try:
        return int(text, 16)
    except ValueError as exc:
        raise SystemExit(f"invalid probe offset: {text}") from exc


def read_u64_le(blob: bytes, offset: int) -> int:
    end = offset + 8
    if end > len(blob):
        raise SystemExit(f"source offset 0x{offset:x} exceeds image")
    return int.from_bytes(blob[offset:end], "little")


def main() -> None:
    args = parse_args()
    probe_offset = parse_probe(args.probe_offset)
    image = args.raw_image.read_bytes()

    rows: list[tuple[int, list[int]]] = []
    for slide in range(0, 0x200000, 0x10000):
        page_source = probe_offset - slide
        if page_source < 0:
            raise SystemExit(
                f"slide 0x{slide:x} exceeds probe offset 0x{probe_offset:x}"
            )
        words = [read_u64_le(image, page_source + page_offset) for page_offset in PAGE_OFFSETS]
        rows.append((slide, words))

    lines = [
        "// Generated from the exact raw Image.",
        f"// Each row maps actual slide to Image[0x{probe_offset:x} - slide].",
        "#ifndef P0_FINGERPRINT_H",
        "#define P0_FINGERPRINT_H",
        "",
        "#define P0_FINGERPRINT_WORDS 8",
        "",
        "static const uint16_t p0_fingerprint_offsets[P0_FINGERPRINT_WORDS] = {",
        "  0x000, 0x200, 0x400, 0x600, 0x800, 0xa00, 0xc00, 0xe00,",
        "};",
        "",
        "struct p0_fingerprint {",
        "  uintptr_t slide;",
        "  uint64_t words[P0_FINGERPRINT_WORDS];",
        "};",
        "",
        "static const struct p0_fingerprint p0_fingerprints[] = {",
    ]
    for slide, words in rows:
        formatted = []
        for index, word in enumerate(words):
            suffix = " } },"
            if index != len(words) - 1:
                suffix = "," if index % 2 == 0 else ",\n    "
            formatted.append(f"0x{word:016x}ULL{suffix}")
        lines.append(f"  {{ 0x{slide:06x}ULL, {{ " + "".join(formatted))
    lines.extend(["};", "", "#endif", ""])
    args.output_header.write_text("\n".join(lines), encoding="utf-8")

    for slide, words in rows:
        page_source = probe_offset - slide
        for index, page_offset in enumerate(PAGE_OFFSETS):
            actual = read_u64_le(image, page_source + page_offset)
            if actual != words[index]:
                raise SystemExit(
                    f"mismatch for slide 0x{slide:x} at source 0x{page_source + page_offset:x}"
                )

    print(f"verified 32 rows and 256 source qwords at probe 0x{probe_offset:x}")


if __name__ == "__main__":
    main()
