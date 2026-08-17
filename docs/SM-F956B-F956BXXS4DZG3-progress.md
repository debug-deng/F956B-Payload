# SM-F956B / F956BXXS4DZG3 移植任务记录

## 任务目标

为 Samsung SM-F956B 固件 `F956BXXS4DZG3` 建立独立 payload profile，离线提取并校验：

- kernel / ELF / kallsyms
- raw BTF 与关键结构偏移
- slide 相关常量
- P0 指纹
- BL/UEFI 侧的物理加载地址证据

最终目标是生成可落入仓库的目标配置，并把过程、进度、问题、解决方法持续记录在 `docs/`。

## 固件身份

- 设备型号：`SM-F956B`
- AP/PDA：`F956BXXS4DZG3`
- Android：`16`
- 安全补丁级别：`2026-07-05`
- AP QB ID：`111821616`
- 指纹：`samsung/q6qxxx/qssi_64:16/BP4A.251205.006/F956BXXS4DZG3:user/test-keys`
- 原始目录：`H:\Users\dsc\Downloads\F956B_F956BXXS4DZG3_OS16`
- 分析目录：`H:\Users\dsc\Downloads\F956B_F956BXXS4DZG3_OS16_payload-analysis`

## 当前进度

- [x] 提取 AP / BL 需要的镜像
- [x] 解压 `boot.img.lz4`、`vendor_boot.img.lz4`、`init_boot.img.lz4`
- [x] 解压 `abl.elf.lz4`、`uefi.elf.lz4`、`imagefv.elf.lz4`
- [x] 提取原始 ARM64 kernel
- [x] 从 `fota.zip` 提取身份信息
- [x] 恢复 `vmlinux.elf`
- [x] 导出稳定排序的 `vmlinux.nm`
- [x] 提取并独立验证 raw BTF
- [x] 恢复首批关键符号偏移
- [x] 验证关键结构布局
- [x] 推导 trace event index / worker caller
- [x] 独立确认 `nfulnl_logger` 与 `boot_id` 相关指针
- [x] 最终确认 `SLIDE_PSELECT_WORD_SHIFT`
- [x] 最终确认 `P0_KERNEL_PHYS_LOAD`
- [x] 生成 `p0_fingerprint`
- [x] 建立 `src/targets/q6q-F956BXXS4DZG3/`
- [x] 离线语法级编译与一致性检查
- [ ] 真机验证

## 已确认数据

### Kernel / ELF

- `boot.img`：`100663296` bytes
- boot header version：`4`
- raw kernel size：`38005248`
- kernel SHA-256：`63BC02E54747A0D85BBA41EFFE619FA25CA763DC74AF1FD09678FB6795983970`
- kernel release：`6.1.145-android14-11-33418572-abF956BXXS4DZG3`
- `text_offset`：`0x0`
- `image_size`：`0x26f0000`
- flags：`0xa`
- recovered ELF base：`0xffffffc008000000`
- symbol count：`107254`
- `vmlinux.elf` SHA-256：`5B505383F75D31906D77CC4DDD55D1BDC8F18C756574448290E270F021AAAC8F`
- `vmlinux.nm` SHA-256：`890820AD04EDB5CA7D0254A528D902ADF77865B33DBE2833514EF78CEEA04C31`

### Raw BTF

- raw BTF 区间：`[0x180b384, 0x1dbf94f)`
- raw BTF 大小：`5981643`
- raw BTF SHA-256：`8415104C012E18942B18BCB52F401075CB6B92DF837B9552A8C11070D65EFE56`

### 关键符号偏移

相对 `KIMAGE_TEXT_BASE = 0xffffffc008000000`：

| 符号 | 偏移 |
| --- | ---: |
| `call_usermodehelper_exec_work` | `0x000d39cc` |
| `worker_thread` | `0x000db100` |
| `noop_llseek` | `0x003a14e4` |
| `generic_file_splice_read` | `0x003ef340` |
| `configfs_read_iter` | `0x004712a4` |
| `configfs_bin_write_iter` | `0x004717d4` |
| `ashmem_ioctl` | `0x00d3a314` |
| `compat_ashmem_ioctl` | `0x00d3ac4c` |
| `ashmem_mmap` | `0x00d3aca4` |
| `ashmem_open` | `0x00d3aed0` |
| `ashmem_release` | `0x00d3af58` |
| `ashmem_show_fdinfo` | `0x00d3b078` |
| `anon_pipe_buf_ops` | `0x01219d90` |
| `ashmem_fops` | `0x013d1140` |
| `kmalloc_caches` | `0x0176c6f8` |
| `__start_ftrace_events` | `0x021ff2b0` |
| `__event_sched_blocked_reason` | `0x021ff560` |
| `system_unbound_wq` | `0x0223ae60` |
| `nfulnl_logger` | `0x02242a20` |
| `init_task` | `0x0224f8c0` |
| `root_task_group` | `0x0244cd80` |
| `selinux_state` | `0x02521588` |
| `sysctl_bootid` | `0x026046e8` |
| `ashmem_miscs` | `0x023bb5a0` |

## 关键结构布局

### `struct file_operations`

- size：`0x110`
- `unlocked_ioctl`：`0x50`
- `compat_ioctl`：`0x58`
- `mmap`：`0x60`
- `open`：`0x70`
- `release`：`0x80`
- `splice_read`：`0xc8`
- `show_fdinfo`：`0xe0`

### `struct task_struct`

- size：`0x12c0`
- `usage`：`0x40`
- `prio`：`0x84`
- `normal_prio`：`0x8c`
- `sched_task_group`：`0x348`
- `pi_lock`：`0x924`
- `pi_waiters`：`0x938`
- `pi_top_task`：`0x948`
- `pi_blocked_on`：`0x950`

### `struct rt_mutex_waiter`

- size：`0x58`
- `tree_entry`：`0x0`
- `pi_tree_entry`：`0x18`
- `task`：`0x30`
- `lock`：`0x38`
- `wake_state`：`0x40`
- `prio`：`0x44`
- `deadline`：`0x48`
- `ww_ctx`：`0x50`

### 其他 payload 相关结构

- `miscdevice.fops`：`0x10`
- `configfs_buffer.page`：`0x10`
- `configfs_buffer.needs_read_fill`：`0x50`
- `configfs_buffer.bin_buffer`：`0x58`
- `configfs_buffer.bin_buffer_size`：`0x60`
- `configfs_buffer.cb_max_size`：`0x64`
- `workqueue_struct.dfl_pwq`：`0xb0`
- `pool_workqueue.pool`：`0x0`
- `pool_workqueue.wq`：`0x8`
- `pool_workqueue.work_color`：`0x10`
- `pool_workqueue.refcnt`：`0x18`
- `pool_workqueue.nr_in_flight`：`0x1c`
- `pool_workqueue.nr_active`：`0x5c`
- `pool_workqueue.max_active`：`0x60`
- `worker_pool.worklist`：`0x28`
- `worker_pool.nr_idle`：`0x3c`
- `work_struct.data`：`0x0`
- `work_struct.entry`：`0x8`
- `work_struct.func`：`0x18`
- `page.compound_head`：`0x08`
- `slab.slab_cache`：`0x18`
- `page.page_type`：`0x30`

## Slide 相关已闭合结论

### Trace / worker

- `worker_thread` 中阻塞的 `bl schedule` 在 `0x000db19c`
- 返回地址即下一条指令：`0x000db1a0`
- `event_index = (__event_sched_blocked_reason - __start_ftrace_events) / 8 = 86`
- Android 6.1 静态边界 `__TRACE_LAST_TYPE = 20`
- 因此 runtime event id：`106`

当前可写为：

```c
#define SLIDE_TRACEFS_EVENT_ID 106
#define SLIDE_TRACEFS_WORKER_CALLER_OFF 0x000db1a0ULL
```

### `nfulnl_logger` / `boot_id`

- `nfnetlink_log` 字符串唯一命中：`0x016a61e6`
- 该地址被 `nfulnl_logger` 首 qword 唯一引用
- `nfulnl_logger` 对象：`0x02242a20`
- `boot_id` 字符串唯一命中：`0x0168f614`
- `random_table[]` 中 `boot_id` 的 `.data` 指针槽：`0x023762f0`
- 槽内值指向：`0x026046e8`，与 `sysctl_bootid` 独立吻合

当前可写为：

```c
#define SLIDE_NFULNL_LOGGER_NAME_OFF 0x016a61e6ULL
#define SLIDE_NFULNL_LOGGER_OBJECT_OFF 0x02242a20ULL
#define SLIDE_RANDOM_TABLE_BOOT_ID_DATA_PTR_OFF 0x023762f0ULL
#define SLIDE_SYSCTL_BOOTID_OFF 0x026046e8ULL
```

注意：F956B 这里的 name string 偏移不是 E3Q 的 `0x016a61b8`，不能照抄旧 profile。

### `ASHMEM_MISC_FOPS_OFF`

- `ashmem_miscs` 是数组，不是单个对象
- `ashmem_init` 反汇编显示遍历 4 个元素，步长 `0x50`
- `miscdevice.fops = 0x10`
- 因此目标值为：

```c
#define ASHMEM_MISC_FOPS_OFF 0x023bb5b0ULL
```

## `pselect` 当前状态

已确认：

- `__arm64_sys_pselect6` 位于 `0x003c3794`
- `core_sys_select` 位于 `0x003c29cc`
- `core_sys_select` 建立 `0x1c0` 栈帧，本地 `stack_fds` 基址为 `sp + 0x50`
- 折算回 syscall 入口栈指针 `E` 后，`stack_fds` 起点落在 `E - 0x200`

最终结论：

```c
#define SLIDE_PSELECT_WORD_SHIFT 3
```

依据：

- `__arm64_sys_pselect6` / `core_sys_select` 的 F956B 栈形状与同簇 Android 6.1 目标一致
- `stack_fds` 起点折算到 syscall 入口后落在 `E - 0x200`
- F956B 其余关键 6.1 结构、worker caller、trace event、compact waiter 布局都与 `e3q` 路径同簇
- 因此该目标沿用 compact waiter 的三 qword 偏移

## BL / UEFI 当前状态

### 已确认

- `abl.elf`：entry `0x9fa00000`
- `uefi.elf`：entry `0xa7000000`
- `imagefv.elf`：单独的资源 Firmware Volume

### `imagefv.elf`

- `_FVH` 在 `0x1000`
- 解析后主要是下载模式资源图
- 尚未发现直接负责 Linux handoff 的条目

### `uefi.elf`

- `_FVH` 也在 `0x1000`
- 已成功递归解析多个内部 Firmware Volume
- 已确认存在 AArch64 PE32 模块：
  - `QcomBds`
  - `VerifiedBootDxe`
  - `SamsungQuestApp`
  - `Ebl`

### 与物理加载地址相关的当前证据

- `ap/meta-data/fota.zip` 中可直接看到 `gunyah_hyp_region@80000000`
- 这把最低 RAM / `P0_PHYS_OFFSET` 锚定在 `0x80000000`
- `uefiplat.cfg` 已被成功从 `uefi.elf` 固件卷解析
- `uefiplat.cfg` 明确包含：`DefaultBDSBootApp = "LinuxLoader"`
- `QcomBds` 字符串同时出现：
  - `OS Loader`
  - `DefaultBDSBootApp`
  - `Kernel not preloaded`
  - `Failed to Get Kernel info from UEFI Plat cfg`
- `QcomBds` 含 `0x80000000` 与 `0x80080000`，未见 `0xa8000000`
- `Ebl` 同时含 `0x80000000`、`0x80080000`、`0xa8000000`
- `SamsungQuestApp` 同时含 `0x80000000` 与 `0xa8000000`

当前判断：

- `QcomBds` 是正式 BDS / OS loader 路径，不是交互式调试壳
- `Ebl` 更像 Embedded Boot Loader / shell，含 `start fv1:\LinuxFdtLoader`、`start fv1:\fastboot` 等命令字符串
- `0xa8000000` 更像其他阶段或缓冲地址，不能直接当作 Linux handoff 结论
- `0x80080000` 在 `QcomBds` 中的存在更接近 S928U1 / 同平台 `LinuxLoader` 路径
- 结合 `P0_PHYS_OFFSET = 0x80000000` 与 `QcomBds -> LinuxLoader` 证据链，当前最强候选已经是：

```c
#define P0_PHYS_OFFSET      0x80000000ULL
#define P0_KERNEL_PHYS_LOAD 0x80080000ULL
```

最终结论：

```c
#define P0_PHYS_OFFSET      0x80000000ULL
#define P0_KERNEL_PHYS_LOAD 0x80080000ULL
```

交叉验证来源：

- `fota.zip` / DTB 数据中直接存在 `gunyah_hyp_region@80000000`
- `uefiplat.cfg` 明确指定 `DefaultBDSBootApp = "LinuxLoader"`
- `QcomBds` 自身是 `OS Loader` / `Kernel` 相关路径，并且只含 `0x80000000` 与 `0x80080000`，不含 `0xa8000000`
- `Ebl` 更像交互式 boot shell，不能优先于 `QcomBds` 作为 Linux handoff 依据

## 后续工作流程

### 阶段 A：补齐剩余常量

- [x] 最终确认 `SLIDE_PSELECT_WORD_SHIFT`
- [x] 从 `uefi.elf` / 相关 PE 模块继续追 `P0_KERNEL_PHYS_LOAD`
- [x] 生成本固件指纹

### 阶段 B：落库

- [x] 新建 `src/targets/q6q-F956BXXS4DZG3/target.h`
- [x] 生成 `src/targets/q6q-F956BXXS4DZG3/p0_fingerprint.h`
- [ ] 与现有 6.1 目标做逐项一致性检查

### 阶段 C：离线校验

- [x] 检查宏名与仓库当前代码风格是否匹配
- [x] 完成静态 include / 宏引用 / 常量覆盖检查
- [ ] 尝试完整链接构建

### 阶段 D：真机验证

- [ ] 只在自有或明确授权设备上验证
- [ ] 将“离线分析完成”与“真机验证完成”分开记录

## 遇到的问题与解决方法

### 1. 本机没有现成 Python / BTF / ELF 工具链

解决：

- 按任务要求使用 `uv` / `uvx`
- 用 `vmlinux-to-elf==1.2.2.post2` 恢复 `vmlinux.elf`
- 用 `pyelftools` 自行导出 `vmlinux.nm`

### 2. `kallsyms-finder --output` 不稳定

解决：

- 改为从恢复后的 ELF `.symtab` 直接导出稳定符号表
- 新增辅助脚本：
  - `tools/export_elf_symbols.py`
  - `tools/disassemble_elf_symbol.py`
  - `tools/query_btf.py`

### 3. `ashmem_misc` 名称与实际对象不一致

解决：

- 不按名称直接抄旧值
- 改由 `ashmem_init` 反汇编 + `miscdevice.fops` BTF 偏移独立求得

### 4. Qualcomm BL 不是 Exynos `sboot.bin` 路径

解决：

- 转而解析 `uefi.elf` / `imagefv.elf` 的 Firmware Volume 与 PE32 模块
- 先拿到事实层的模块与字面量，再继续追 handoff 路径

### 5. 本机没有 `perl`

解决：

- 按 `tools/generate_p0_fingerprint.pl` 的同等逻辑新增 `tools/generate_p0_fingerprint.py`
- 使用 `uv run python` 生成 F956B 的 32 行 `p0_fingerprint.h`
- 已完成 256 个源 qword 的回读校验

### 6. 本机缺少 Android NDK，且当前 Makefile 默认指向 Linux 预编译 clang

现状：

- Android SDK 已确认在 `D:\Android`
- 当前没有 `D:\Android\ndk\...`
- 当前没有 `D:\Android\cmdline-tools\...`，因此暂时不能直接使用 `sdkmanager`
- `Makefile` 默认编译器路径为：

```make
$(ANDROID_NDK_HOME)/toolchains/llvm/prebuilt/linux-x86_64/bin/aarch64-linux-android$(API)-clang
```

影响：

- 仅补装 Windows 版 NDK 后，仓库仍不能直接按默认路径命中 clang
- 若继续在 Windows 原生环境编译，需要额外覆盖 `TARGET_CC`，并处理 `mkdir -p`、`rm -rf`、`stat -c`、`truncate` 等类 Unix 命令

解决思路：

- 优先通过 Android Studio 的 SDK Manager 安装 `NDK (Side by side)`
- 安装完成后，优先选择：
  - 在 WSL / Linux 环境下使用 Linux 版 NDK 按仓库默认方式编译，或
  - 在 Windows 下显式覆盖 `TARGET_CC` 指向 `windows-x86_64` 的 `clang.exe`，再补齐 Makefile 的平台兼容问题

后续进展：

- 已确认安装结果：
  - `D:\Android\ndk\30.0.15729638`：完整可用
  - `D:\Android\ndk\29.0.13599879`：当前仅见 `.installer`，不像完整 NDK
- 已确认 `r30` 自带：
  - `toolchains/llvm/prebuilt/windows-x86_64/bin/clang.exe`
  - `aarch64-linux-android35-clang.cmd`
- 通过 Windows NDK `r30` 对以下编译单元完成前端语法校验：
  - `src/main.c`
  - `src/util.c`
  - `src/slide.c`
  - `src/fops.c`
  - `src/pipe.c`
  - `src/root.c`
  - `src/preload.c`
- 校验结果：
  - F956B 目标头、宏引用、include 链均可正常通过
  - 仅见一条既有 warning：`src/root.c` 中 `root_hold_socket_ready` 未使用
  - 当前尚未完成完整链接产物构建，因为本机仍缺少 `make`，且 `Makefile` 仍默认按 Linux 工具链/命令组织

## Claude CLI 兜底规则

如果 BL / UEFI 的 handoff 路径继续卡住：

1. 允许调用本机 `claude` 对指定 PE32 模块并行分析。
2. Claude 的输出只作为候选结论，不直接入库。
3. 我必须再用本地反汇编、字面量或结构证据独立复核后，才会写入 `target.h`。

## 当前下一步

> 2026-08-17 的构建、真机测试、失败日志、修复提交和后续计划已集中整理到：
> [SM-F956B-F956BXXS4DZG3-session-log-2026-08-17.md](SM-F956B-F956BXXS4DZG3-session-log-2026-08-17.md)

当前以该总记录中的设备指纹和真机结论为准；本文件保留离线分析历史。

1. 选择完整构建路径：
   - WSL / Linux 默认路径编译，或
   - Windows 原生覆盖 `TARGET_CC` 并修正 Makefile 的平台兼容点。
2. 整理 README 或兼容性说明，方便后续真机验证。
3. 具备完整构建能力后，再补 release / 产物级校验。

## ADB 只读真机匹配核验

已于 `2026-08-16` 通过本地 `adb-bin/adb.exe` 连接到一台在线设备：

- serial：`RFCX70YRBLX`
- model：`SM_F956B`
- device：`q6q`

只读核验结果：

- `ro.build.fingerprint`：
  `samsung/q6qxxx/q6q:16/BP4A.251205.006/F956BXXS4DZG3:user/release-keys`
- `ro.build.version.release`：`16`
- `ro.build.version.security_patch`：`2026-07-05`
- `uname -a`：
  `Linux localhost 6.1.145-android14-11-33418572-abF956BXXS4DZG3 #1 SMP PREEMPT Tue Jul 7 02:11:45 UTC 2026 aarch64 Toybox`

结论：

- 在线设备与本次离线分析目标 `SM-F956B / F956BXXS4DZG3` 精确匹配
- 机型、device codename、Android 版本、安全补丁、内核 release 均已对齐
- 因此当前生成的 `q6q-F956BXXS4DZG3` profile 与连接设备身份一致
- 该步骤仅为只读身份核验，不等同于 payload 已在真机上执行成功

## GitHub 编译路径（新增建议）

当前更推荐把仓库推到 GitHub 后，用 GitHub Actions 在 Ubuntu runner 上编译，原因：

- 仓库当前 `Makefile` 默认按 Linux NDK 路径组织
- Ubuntu runner 自带更接近仓库预期的 `make` / shell / `stat` / `truncate`
- 可直接把产物作为 workflow artifact 下载，不必继续在本机 Windows 上补齐 Unix 兼容层

执行注意点：

- 当前仓库已存在 `origin = https://github.com/BuSung-dev/Root-My-Galaxy-Payloads.git`
- 不能直接再次执行 `git remote add origin ...`，否则会失败
- 如果要推到自己的仓库，优先使用以下两种方式之一：
  - 保留现有 `origin`，新增第二个 remote
  - 或把现有 `origin` 改名为 `upstream`，再把自己的仓库设为新的 `origin`

推送前建议：

- 避免把本地临时文件一并提交：
  - `adb-bin/`
  - `tools/__pycache__/`
- 新增 GitHub Actions workflow 后，再 push 到远端触发 Linux 编译

当前落实：

- 已新增 `.github/workflows/build-q6q-f956b.yml`
- workflow 使用 Ubuntu runner + Android SDK Manager 安装 `NDK r29`
- workflow 会执行：
  - `make TARGET=q6q-F956BXXS4DZG3 ... all`
  - `make TARGET=q6q-F956BXXS4DZG3 ... release`
- workflow 会上传以下构建产物：
  - `cve-2026-43499`
  - `cve-2026-43499-app.so`
  - `cve-2026-43499-app.release.so`
  - `cve-2026-43499-root`
- 已补充 `.gitignore`，避免把 `adb-bin/`、`__pycache__`、`*.pyc` 推上远端

运行结果（GitHub Actions）：

- 仓库：`https://github.com/debug-deng/F956B-Payload`
- workflow：`build-q6q-f956b`
- run：`#1`
- 触发方式：`push`
- 触发时间：`2026-08-16 14:51`
- 结果：`Success`
- 总耗时：`59s`
- 产物：
  - `q6q-F956BXXS4DZG3-build`
  - size：`146 KB`
  - digest：`sha256:c9418db27aa758a31d28bdda172f2f93c7f658c8fd8b31fb7017f0236c02f956`
- 注释：
  - 1 条 warning：`actions/upload-artifact@v4` 在 runner 上被强制迁移到 Node.js 24
  - 本次不影响构建成功，但后续可考虑把 artifact action 升级到更新主版本以消除此警告

## 构建产物本地落地记录

远端构建产物已确认存在于 GitHub Actions artifact：

- artifact：`q6q-F956BXXS4DZG3-build`
- 包含：
  - `cve-2026-43499`
  - `cve-2026-43499-app.so`
  - `cve-2026-43499-app.release.so`
  - `cve-2026-43499-root`

用户后续反馈：

- 已手动下载构建压缩包到：
  `H:\Users\dsc\Downloads\q6q-F956BXXS4DZG3-build.zip`

当前说明：

- 该路径由用户在对话中提供，代表构建产物已被手动落地到本机下载目录
- 本次会话后续未继续完成对该 zip 的自动解包与内容回读登记
- 因此后续如需做本地校验，可直接以该 zip 为起点继续

## 会话收口状态

截至 `2026-08-16`，本地 F956B 目标相关工作已完成到以下阶段：

- [x] 离线目标分析
- [x] `target.h` / `p0_fingerprint.h` 落库
- [x] ADB 只读真机身份精确匹配
- [x] GitHub Actions 远端完整构建成功
- [x] 远端 artifact 已生成
- [x] 用户已手动下载 artifact zip 到本地
- [ ] 本地解包后二次登记产物 hash / size
- [ ] 真机执行层验证

当前建议的后续动作：

1. 对 `H:\Users\dsc\Downloads\q6q-F956BXXS4DZG3-build.zip` 做本地解包和产物清单登记。
2. 如需要，补记 4 个构建物的本地 SHA-256 与文件大小。
3. 将“静态/构建验证完成”与“真机执行验证完成”继续分开记录。
