# SM-F956B / F956BXXS4DZG3 持续验证总记录

更新时间：2026-08-17  
目标设备：Samsung SM-F956B / codename `q6q`  
目标固件：`F956BXXS4DZG3`  
目标范围：仅支持 F956B，离线 APK，真机临时 root 验证

## 1. 最终确认的设备身份

ADB 设备：

```text
serial: RFCX70YRBLX
model: SM-F956B
device: q6q
fingerprint: samsung/q6qxxx/q6q:16/BP4A.251205.006/F956BXXS4DZG3:user/release-keys
kernel: 6.1.145-android14-11-33418572-abF956BXXS4DZG3
Android: 16
security patch: 2026-07-05
```

设备身份与目标 profile 精确匹配。旧记录中出现的 `qssi_64`、`user/test-keys` 是早期离线资料，不是当前真机最终值；运行时应以以上 `q6qxxx/q6q` 指纹为准。

## 2. 静态分析与偏移量结论

已完成并交叉核对：

- `boot.img`、`vendor_boot.img`、`init_boot.img`、`abl.elf`、`uefi.elf` 等镜像提取。
- `vmlinux.elf`、稳定排序符号表和 raw BTF 恢复。
- `task_struct`、`file_operations`、`rt_mutex_waiter` 等结构布局核对。
- `nfulnl_logger`、`boot_id`、`ashmem_miscs` 等目标偏移独立推导。
- `SLIDE_TRACEFS_EVENT_ID=106`。
- `SLIDE_TRACEFS_WORKER_CALLER_OFF=0x000db1a0`。
- `SLIDE_PSELECT_WORD_SHIFT=3`。
- `P0_PHYS_OFFSET=0x80000000`。
- `P0_KERNEL_PHYS_LOAD=0x80080000`。

物理加载地址的证据来自 `fota.zip`、DTB/平台配置、`QcomBds` 的 LinuxLoader 路径和 UEFI 字面量。`0x80000000` 方案在真机上表现更差，已恢复并保留 `0x80080000` 作为当前主候选；目前没有证据支持改成 `0xa8000000`。

## 3. APK 与 KernelSU 处理

APK 已改为：

- 离线运行，不依赖网络下载。
- 仅包含 q6q / F956BXXS4DZG3 payload。
- 本地验证并加载 KernelSU 相关资源。
- 去除普通应用进程中直接 `chmod` 导致的 `EACCES` 路径。
- 通过 `/data/local/tmp` 暂存 payload/helper，再由 Shizuku/ADB 授权路径执行。

曾发现的独立问题：用户提供的 `ksud` 版本未嵌入匹配的 `.ko`，其 `supported-kmis` 为空，不能单独证明 KernelSU 模块加载成功。因此 exploit 成功后仍需单独确认 `ksud` 的 KMI 资源和模块嵌入状态。

## 4. 构建与提交时间线

| 版本/提交 | 主要变化 | 结果 |
|---|---|---|
| build `(1)` | 初始 q6q F956B profile，加入运行日志 | 能进入 mm leak/pselect，物理写失败 |
| `18f7b23` | pipe sizing、MTE、更多观测日志 | 偶尔获得 `mm_struct`，gate 未命中 |
| `edc863c` | 临时测试 `P0_KERNEL_PHYS_LOAD=0x80000000` | 表现更差，已放弃 |
| `44b38b1` / `625eef0` | pselect 路由与 guard 参数实验 | 触发不稳定，未确认成功 |
| `2025c09` | 降低 pselect 时序变化 | 出现 `ret=0`、写窗口关闭 |
| `6afd13f` | pipe gate bank/reclaim 参数实验 | `gate hits=0`，仍失败 |
| build `(5)` | bank layout 版本 | 发现 `APP_ACCEPT_SCHED_TRIGGER` 会制造假阳性 |
| `0590b59` | 删除假阳性旁路，要求真实 write window | 真实结果为 `ret=0`、`ok=0` |
| build `(6)` | 使用真实 write-window 判定的包 | 可运行，但前置泄漏命中率低；命中后仍 `pselect ret=0` |
| `e743669` | 加入 pselect syscall/wchan 同步守卫，等待从 100ms 改为 500ms | 首次 CI 编译失败，原因见下文 |
| `9dbbe15` | 修复条件编译变量作用域，清理重复宏 | 已推送，等待新的 CI artifact |

GitHub Actions 仓库：<https://github.com/debug-deng/F956B-Payload/actions>

## 5. 真机运行结果

应用包：`dev.busung.s25uroot`  
KernelSU Manager：`me.weishu.kernelsu`

已通过 ADB 安装并执行多个构建包。应用有时会因 exploit 触发崩溃/重启后出现 package manager 的 stale 记录或 base APK 丢失；重新 `adb install -r -d` 可恢复。这不是“临时 root 重启后消失”的正常现象，而是失败路径对应用/系统状态造成的异常影响。

典型成功前置日志：

```text
mm leaked=... base=... object_index=20
slide wait_requeue_pi ret=-1 errno=110
```

但随后始终出现类似：

```text
slide pselect returned nfds=320 pad=0 ret=0 errno=0
  elapsed_usec=100163 ready=1 seen=1 entered=1 calls=1 sched_ok=1
p0 physical write status=256 ok=0
p0 physical slot=0 write window failed
```

含义：

- `ready=1` 只表示消费者线程已准备好，不表示目标线程真正处于 `pselect/do_select` 阻塞态。
- `sched_ok=1` 只表示调度事件返回成功。
- `ret=0` 表示 pselect 没有获得有效就绪事件，因而不能建立真实物理写窗口。
- `status=256` 是子进程以 exit code 1 退出，不是成功状态。
- `APP_ACCEPT_SCHED_TRIGGER` 已删除，后续日志不会再把 sched 事件伪装成物理写成功。

当前设备状态：设备可正常启动，APK 可安装运行；`su -c id` 仍不可用，KernelSU Manager 仍显示未安装，尚未取得稳定 root。

## 6. 已发现的问题与解决方法

### 6.1 `chmod failed: EACCES`

原因：普通 APK/授权执行链中直接对目标文件调用 `chmod`，权限不在当前进程上下文内。  
处理：改为离线 payload + `/data/local/tmp` 暂存，由授权执行链负责后续操作；同时移除不必要的应用侧 chmod。

### 6.2 `0x80000000` 方案失败

原因：该值虽然是 RAM/物理区域下界证据，但作为 kernel physical load 测试值时真机表现更差。  
处理：恢复 `P0_KERNEL_PHYS_LOAD=0x80080000`，保留 `P0_PHYS_OFFSET=0x80000000`。两者含义不同，不能混为一个地址。

### 6.3 假成功日志

原因：`APP_ACCEPT_SCHED_TRIGGER=1` 只检查 `sched_ok`，绕过了 `pselect ret>0` 条件。  
处理：提交 `0590b59` 删除旁路，要求 `slide_pselect_write_window` 真正为 1。

### 6.4 pselect 条件编译错误

原因：`e743669` 打开同步宏后，`ready_ok`、`guard_ok` 等变量被声明在 `APP_REQUIRE_FRESH_P0_SESSION` 分支内，而 F956B 没有定义该宏，导致 CI 出现 7 个 undeclared identifier 错误。  
处理：提交 `9dbbe15` 将诊断变量声明提升到同步宏自身的条件范围，并移除重复 `SLIDE_BANK_SLOTS` / `SLIDE_BANK_TASK_OFF` 定义。

### 6.5 KernelSnitch 前置泄漏命中率低

日志大量停在：

```text
pipe KernelSnitch sk_buff page leak failed
KernelSnitch mm_struct leak failed
prepare_kernel_page did not find usable nonzero source pointers
```

这说明 F956B 的 SLUB 堆布局和时序与现有 profile 不完全一致。它是独立于 pselect 的第一层随机失败，不能仅靠修改物理地址解决。

## 7. 当前结论

1. F956B profile、设备指纹、主要静态偏移和 build label 已匹配。
2. 当前失败不是 APK 离线化、设备错配或单纯 `0x80000000/0x80080000` 地址错误。
3. 真机最远进度是获得 mm leak 并进入 pselect/physical-p0 oracle，但真实写窗口未建立。
4. 当前主要技术问题按优先级为：
   - KernelSnitch `sk_buff/mm_struct` 泄漏命中率；
   - pselect 目标线程进入 `do_select` 的同步和触发时序；
   - p0 pipe gate 在真实物理写之后的命中率。
5. 在 `9dbbe15` 的 CI 包验证前，不应继续解释 gate 偏移或宣称 root 成功。

## 8. 后续工作

### 立即步骤

- 等待 `9dbbe15` 的 GitHub Actions 构建完成。
- 下载新 artifact，确认 APK payload 已包含同步守卫版本。
- 在设备上重新安装并记录：
  - 是否出现 `slide pselect blocked ready=1`；
  - `ready_wchan` / `guard_wchan` 是否为 `do_select`；
  - 是否出现 `ret>0`；
  - 是否出现真实 `p0 physical write status=0 ok=1`。

### 若仍失败

- 若 `ready=0`：继续校准 waiter tid、wchan 判断或触发延时，不改物理地址。
- 若 `ready=1` 但 `ret=0`：继续检查 pselect fdset/高 fd 映射和事件就绪路径。
- 若 `ret>0` 但 gate 为 0：再单独校准 pipe gate 的物理页、对象 index 和页内偏移。
- 若 gate 命中但 KernelSU 未加载：单独修复 `ksud` 的 KMI `.ko` 嵌入，不把 exploit 和 KernelSU 资源问题混为一谈。

## 9. 当前文件与仓库状态

## 9.1 build `(7)` 真机结果

本地包：`H:\Users\dsc\Downloads\q6q-F956BXXS4DZG3-build (7).zip`  
设备：`RFCX70YRBLX`  
结果：24 次重试全部结束，APK 显示“安装失败”，设备未取得 root。

第 12 次出现了本轮最重要的进展：

```text
mm leaked=ffffff804d3df800 base=ffffff804d3d8000 object_index=24
slide pselect returned nfds=320 pad=0 ret=2 errno=0 elapsed_usec=500599
  ready=1 seen=1 entered=1 calls=1 sched_ok=1
p0 physical write status=0 ok=1
p0 pipe gate hits=0 changed=0
```

这证明：

- `pselect ret=0` 不再是唯一阻塞点；同步/等待窗口调整后，确实出现了 `ret=2`。
- 物理写窗口实际建立，`status=0 ok=1` 为真实成功，不是假阳性旁路。
- 当前失败已进一步收敛到 pipe gate：物理写成功后 gate 仍为 `hits=0`。

同一轮第 16 次仍出现 `ret=0`、`status=256`，说明时序命中仍有随机性，但不再是主线唯一问题。第 12 次的 `ret=2 + physical write ok=1` 是目前最远的可重复验证证据。

因此下一轮不应再优先改 `P0_PHYS_OFFSET` 或 `P0_KERNEL_PHYS_LOAD`，而应在保留 pselect 同步参数的前提下，校准：

1. gate marker 写入的页内偏移；
2. gate object index / slot 与真实 pipe page 的对应关系；
3. `verify_p0_pipe_oracle_gate()` 复制、读取和 marker 搜索路径；
4. 物理写后 gate 检查的时序和 restore 行为。

- target：`src/targets/q6q-F956BXXS4DZG3/target.h`
- p0 指纹：`src/targets/q6q-F956BXXS4DZG3/p0_fingerprint.h`
- 真机验证原记录：`docs/SM-F956B-F956BXXS4DZG3-hardware-validation.md`
- 静态分析进度：`docs/SM-F956B-F956BXXS4DZG3-progress.md`
- 最新修复提交：`9dbbe15`
- 目标分支：`main`
- CI remote：`debug-deng/F956B-Payload`
