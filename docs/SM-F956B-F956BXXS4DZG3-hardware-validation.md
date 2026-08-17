# SM-F956B / F956BXXS4DZG3 真机验证记录（exploit 失败分析）

- 日期：2026-08-16 ~ 2026-08-17
- 设备：SM-F956B（`q6q`），serial `RFCX70YRBLX`
- 目标 payload：`q6q-F956BXXS4DZG3`（`cve-2026-43499-app.release.so` + `cve-2026-43499-root`）

## 一、编译产物与机型匹配性核查结论

用户提出质疑：**编译产物是否真的与 SM-F956B 匹配**。逐项核查结果如下，结论是**产物与机型匹配正确，问题不在产物错配**。

### 1. 设备身份精确匹配

真机只读核验（`adb shell getprop` / `uname`）：

| 项目 | 真机值 | 目标期望值 | 匹配 |
| --- | --- | --- | --- |
| fingerprint | `samsung/q6qxxx/q6q:16/BP4A.251205.006/F956BXXS4DZG3:user/release-keys` | 同左 | ✅ |
| Android / SDK | 16 / 36 | 16 | ✅ |
| 安全补丁 | 2026-07-05 | 2026-07-05 | ✅ |
| kernel release | `6.1.145-android14-11-33418572-abF956BXXS4DZG3` | 同左 | ✅ |
| device codename | `q6q` | `q6q` | ✅ |

### 2. 二进制内嵌 build label 正确

四个产物的内嵌标识符：

```
cve-2026-43499               -> q6q-F956BXXS4DZG3-root-umh
cve-2026-43499-app.so        -> q6q-F956BXXS4DZG3-app-physical-p0-oracle
cve-2026-43499-app.release.so-> q6q-F956BXXS4DZG3-app-physical-p0-oracle
cve-2026-43499-root          -> （helper/su daemon，无 target 标识，正常）
```

真机运行时 exploit 打印的 `build config label=q6q-F956BXXS4DZG3-app-physical-p0-oracle`，与二进制一致。

### 3. p0 profile 偏移量正确加载

真机日志第 1 行 exploit 上下文：

```
p0 profile pid=... phys_offset=0000000080000000 kernel_phys_load=0000000080080000
  delta=0000000000080000
  slide_logger=ffffff80017261e6 bootid_data=ffffff80023f62f0
  init_task=ffffff80022cf8c0 root_tg=ffffff80024ccd80 sysctl_bootid=ffffff80026846e8
```

逐项对照 `src/targets/q6q-F956BXXS4DZG3/target.h` 静态常量（通过 `P0_DATA_ALIAS_CONST` 转换 `image_addr - KIMAGE_TEXT_BASE + P0_KERNEL_PHYS_DELTA`，`P0_KERNEL_PHYS_DELTA = 0x80000`）：

| 运行时值 | 来源常量 | 验证 |
| --- | --- | --- |
| `slide_logger=0x...017261e6` | `SLIDE_NFULNL_LOGGER_NAME_OFF=0x016a61e6` | 0x016a61e6+0x80000=0x017261e6 ✅ |
| `bootid_data=0x...023f62f0` | `SLIDE_RANDOM_TABLE_BOOT_ID_DATA_PTR_OFF=0x023762f0` | 0x023762f0+0x80000 ✅ |
| `init_task=0x...022cf8c0` | `INIT_TASK_OFF=0x0224f8c0` | 0x0224f8c0+0x80000 ✅ |
| `root_tg=0x...024ccd80` | `ROOT_TASK_GROUP_OFF=0x0244cd80` | 0x0244cd80+0x80000 ✅ |
| `sysctl_bootid=0x...026846e8` | `SLIDE_SYSCTL_BOOTID_OFF=0x026046e8` | 0x026046e8+0x80000 ✅ |

全部一致，无偏移量错配。

### 4. release 版 ELF 未被截断破坏

`cve-2026-43499-app.release.so`（104128 bytes）是 `Makefile` 的 `release` 目标产物，该目标末尾有 `truncate -s $(APP_RELEASE_SIZE)`（`APP_RELEASE_SIZE=104128`）。经 `llvm-readelf -l` 核验，该文件 4 个 `PT_LOAD` 段的 `offset+filesz` 均在文件大小之内，段表未被截断，ELF 有效。

⚠️ 注意：`Makefile` 里 `APP_RELEASE_SIZE := 104128` 是**硬编码**值，与 q6q 目标没有绑定关系。这是构建系统的隐患，但不影响本次产物有效性。

### 5. KernelSU 产物匹配性（单独记录）

用户昨日在 `K:\KernelSU\out` 编译的产物：

- `kernelsu-android14-6.1-F956BXXS4DZG3-samsung-main-no-patch-text-kdp.ko`：vermagic=`6.1.145-android14-11-33418572-abF956BXXS4DZG3`，与真机精确匹配 ✅
- `ksud-zfold6-F956BXXS4DZG3-samsung-main-no-patch-text-kdp`：**未嵌入内核模块** ❌

在设备上运行 `ksud boot-info supported-kmis` 输出为空，而源码 `userspace/ksud/src/assets.rs` 显示模块需在编译期通过 `RustEmbed` 从 `userspace/ksud/bin/aarch64/`（`<kmi>_kernelsu.ko`）嵌入。该目录当前只有 `bootctl`/`busybox`，无 `.ko`。因此该 ksud 是**空壳**，`--late-load` 会因 `Failed to get android14-6.1_kernelsu.ko from assets` 失败。需将 `.ko` 复制为 `userspace/ksud/bin/aarch64/android14-6.1_kernelsu.ko` 后 clean build。

## 二、exploit 真机运行结果

同一套 `EXPLOIT_ATTEMPTS=24 P0_ATTEMPT_TIMEOUT_SEC=45 EXPLOIT_ATTEMPT_TIMEOUT_SEC=120`，共跑 6 轮：

| 轮次 | 结果 | 最深进度 |
| --- | --- | --- |
| 1 | 24/24 失败 | p0 slot 0，`pipe gate hits=0` |
| 2 | 24/24 失败 | p0 slot 0，`pipe gate hits=0` |
| 3 | 24/24 失败 | **p0 slot 1，`pipe gate hits=1`**，后触发内核重启 |
| 4 | 10/24 后内核崩溃重启 | p0 slot 0 |
| 5 | 24/24 失败 | p0 slot 0 |
| 6 | 24/24 失败 | p0 slot 0 |

**结论：exploit 未能在真机取得 root。**

## 三、失败根因定位

### 失败点 1（最主要）：KernelSnitch 堆泄漏命中率极低

绝大多数尝试（约 80%+）在拿到任何内核地址之前就失败，日志交替出现两种模式：

```
[!] pipe KernelSnitch sk_buff page leak failed
[!] pipe page child did not report base

[!] KernelSnitch mm_struct leak failed
[-] prepare_kernel_page did not find usable nonzero source pointers
```

对应源码：
- `src/pipe.c:244` `pipe KernelSnitch sk_buff page leak failed`
- `src/pipe.c:329` `pipe page child did not report base`

这两个是 `sk_buff` 页泄漏 / `mm_struct` 泄漏原语未命中。KernelSnitch 依赖 SLUB 分配器的精确堆布局与时序，在 F956B 真机上命中率远低于预期。

### 失败点 2：p0 oracle gate 几乎不命中

少数泄漏成功的尝试能推进到 p0 oracle，但：

```
p0 pipe gate hits=0 changed=0      ← 常态
```

`src/pipe.c:1042` 打印的 gate 命中数长期为 0。唯一一次命中（第 3 轮 attempt 7）后续又失败。

### 失败点 3（最远一次）：p0 oracle slot 1 写窗口失败

第 3 轮 attempt 7 完整日志：

```
p0 physical write status=0 ok=1           ← slot 0 写成功
p0 gate marker pipe=48 offset=0
p0 pipe gate hits=1 changed=0             ← gate 首次命中
p0 reference keeper pid=15745 pipe=48
...
slide pselect returned nfds=320 pad=0 ret=0 errno=0 ...   ← 第二次 pselect ret=0
p0 physical write status=256 ok=0         ← slot 1 写窗口失败
[!] p0 physical slot=1 write window failed after 1 attempt(s)
[!] p0 oracle state dirty or uncertain; refusing unsafe retry
```

根因链（对照 `src/slide_app.c`）：

- `write status=256` 即子进程 `_exit(1)`（waitpid status 中 exit code 1 = 256）。
- `slide_trigger_physical_state()`（`src/slide_app.c:891`）fork 子进程执行 `slide_child_trigger_write()`，其返回 `slide_waiter_ok && slide_pselect_write_window`。
- `slide_pselect_write_window` 由 `slide_app.c:430` 设成 `ret > 0 && slide_consume_sched_ok > 0`。
- 第二次 pselect 返回 `ret=0`（无 fd ready），导致 `write_window=false`，写窗口失败。
- 随后 exploit 进入 `oracle state dirty or uncertain` fail-closed，拒绝不安全重试。

即：**pselect 侧信道第二次触发时消费者线程未在预期时间窗口被调度唤醒（ret=0）**，是 pselect 路由的时序/竞态问题。

## 四、结论与下一步建议

1. **产物与机型匹配无误**，问题不在构建错配。
2. 根因是 F956B 新移植 target 的 **KernelSnitch 堆泄漏 + p0 oracle pselect 时序** 在真机上命中率过低，属于移植层调试问题（对应 progress 文档中未勾选的「真机验证」gap）。
3. 需要回源码针对性校准的候选点：
   - `target.h` 中 `SLIDE_PSELECT_WORD_SHIFT=3`（离线 ELF 推导，真机 pselect 栈形状可能有偏差）；
   - `P0_KERNEL_PHYS_LOAD=0x80080000`（BL/UEFI 证据链推导，非直接读回验证）；
   - KernelSnitch 的 sk_buff / mm_struct 泄漏时序参数；
   - pselect 路由的 `ROUTE_WAIT_SECONDS` / `PSELECT_ENTER_DELAY_USEC` 等时序常量。

## 五、附带发现（与 exploit 无关但需记录）

- KernelSU `ksud` 产物为空壳（模块未嵌入），见上文「产物匹配性核查 5」。
- `Makefile` 的 `APP_RELEASE_SIZE=104128` 硬编码，`release` 目标依赖 `truncate` 补齐文件，非 q6q 专属逻辑。

## 六、2026-08-17 后续验证更新

完整时间线、build `(1)` 至 `(6)` 的结果、CI 编译错误、已推送修复和后续分支判断见：

[SM-F956B-F956BXXS4DZG3-session-log-2026-08-17.md](SM-F956B-F956BXXS4DZG3-session-log-2026-08-17.md)

当前追加结论：`ready=1` 仅表示消费者线程已准备，不能证明目标线程已进入 `pselect/do_select`；真正的成功条件仍是 `pselect ret>0` 且 `p0 physical write status=0 ok=1`。提交 `0590b59` 已移除假阳性旁路，提交 `e743669` 增加同步守卫，提交 `9dbbe15` 修复其条件编译错误并等待新的 CI 包。
