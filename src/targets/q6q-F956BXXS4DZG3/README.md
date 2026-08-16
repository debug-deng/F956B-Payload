# q6q-F956BXXS4DZG3 compatibility status

This directory contains the statically verified SM-F956B DZG3 target.

```text
model: SM-F956B
device: q6q
firmware: F956BXXS4DZG3
display build: BP4A.251205.006/F956BXXS4DZG3
fingerprint: samsung/q6qxxx/qssi_64:16/BP4A.251205.006/F956BXXS4DZG3:user/test-keys
kernel: 6.1.145-android14-11-33418572-abF956BXXS4DZG3
page size: 4096
```

`target.h` uses offsets recovered from the exact F956BXXS4DZG3 raw kernel,
recovered `vmlinux.elf`, exported symbol table, raw BTF, and BL/UEFI evidence.
`p0_fingerprint.h` was generated from the exact raw kernel Image and verified
against all 256 source qwords at probe `0x1f0000`.

Closed target-specific decisions include:

- `SLIDE_PSELECT_WORD_SHIFT = 3`
- `SLIDE_TRACEFS_EVENT_ID = 106`
- `SLIDE_TRACEFS_WORKER_CALLER_OFF = 0x000db1a0`
- `P0_PHYS_OFFSET = 0x80000000`
- `P0_KERNEL_PHYS_LOAD = 0x80080000`

The F956B profile does not reuse the older E3Q logger string offset; it uses
the F956B-specific `SLIDE_NFULNL_LOGGER_NAME_OFF = 0x016a61e6`.

The sources pass Android NDK r30 front-end syntax checks on Windows when the
target header is injected explicitly. Full artifact linking is still pending
because the repository `Makefile` currently assumes a Linux-style NDK path and
Unix host utilities.

Analysis provenance and the ongoing porting record are in
[`docs/SM-F956B-F956BXXS4DZG3-progress.md`](../../../docs/SM-F956B-F956BXXS4DZG3-progress.md).
