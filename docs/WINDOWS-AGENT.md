# Windows Agent 使用 Looki L1

这份说明面向在一台新 Windows 10/11 电脑上工作的 Codex、Claude Code 或其他本地 Agent。
目标是让 Agent 从全新克隆开始，完成安装、Classic Bluetooth 配对、状态读取，并在用户
提供自己设备的 owner-binding 后调用拍照、录音和媒体下载。

## 1. 前提

- Windows 10/11；
- Python 3.11 或更高版本；
- 支持 Bluetooth Classic RFCOMM 的蓝牙适配器；
- Wi-Fi 适配器，用于媒体下载时连接 Looki 临时热点；
- 用户明确提供目标 Looki 的 Bluetooth MAC。

手机 App 同一时间不要占用 Looki。状态查询前短按设备按键唤醒即可；重新配对时才需要
进入蓝牙配对模式。

## 2. 一键准备环境

在仓库根目录运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap-windows.ps1
```

脚本会建立 `.venv`、安装项目并运行只读主机诊断。它不会扫描设备、配对、读取媒体或
修改 Windows 蓝牙绑定。

如果用户已经让 Looki 进入配对模式，可显式要求脚本配对并读取状态：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap-windows.ps1 `
  -Address AA:BB:CC:DD:EE:FF -Pair -Renew -Status
```

`-Renew` 先删除这台 Windows 电脑上该地址的旧 Classic Bluetooth bond，然后立即重新
建立 Dedicated Bonding。它不会清除 Looki 内的媒体或手机账户。

## 3. Agent 应采用的验证顺序

```powershell
# 主机环境，不接触设备
.\.venv\Scripts\looki.exe doctor

# 首次或旧绑定损坏时；要求 Looki 正处于配对模式
.\.venv\Scripts\looki.exe pair --address AA:BB:CC:DD:EE:FF --renew

# 配对后退出配对模式，唤醒设备；只读状态
.\.venv\Scripts\looki.exe status --address AA:BB:CC:DD:EE:FF --trace
```

成功 trace 的关键顺序：

```text
transport.connected
auth.challenge.received
lcmp.send tag=201
auth.challenge.accepted result=0
lcmp.send tag=19/204/49/45/234
```

状态结果应包含电量、设备版本、媒体数量、存储和录制状态中的大部分。录制状态为空消息
通常表示当前没有录制，不代表查询失败。

## 4. 受保护功能

这些功能需要用户自己设备的 `*.looki-binding`：

```powershell
.\.venv\Scripts\looki.exe photo `
  --address AA:BB:CC:DD:EE:FF --binding private\my-looki.looki-binding

.\.venv\Scripts\looki.exe audio-start `
  --address AA:BB:CC:DD:EE:FF --binding private\my-looki.looki-binding
.\.venv\Scripts\looki.exe audio-stop `
  --address AA:BB:CC:DD:EE:FF --binding private\my-looki.looki-binding

.\.venv\Scripts\looki.exe media-list `
  --address AA:BB:CC:DD:EE:FF --binding private\my-looki.looki-binding
```

`media-list` 和 `download-one` 会让电脑临时离开原 Wi-Fi，连接 Looki 自身热点并通过 HTTP
读取媒体。Agent 依赖云端时，应先完成下载并恢复原 Wi-Fi，再调用云端模型。

公开仓库没有通用 owner-binding。它与所有者及设备有关，不能从示例 challenge 生成。

## 5. 常见连接表现

| 表现 | 处理 |
|---|---|
| `BluetoothAuthenticateDeviceEx` 不存在 | 更新到 SDK 0.2.4 或更高；Windows 配对 API 应从 `bthprops.cpl` 加载 |
| RFCOMM 连接超时 | 断开手机 App、唤醒 Looki，再试一次状态读取 |
| 连续失败且 Windows 只保留 BLE 项目 | 让 Looki 进入配对模式，运行 `pair --renew` |
| 已连接但没有 tag 200 | 关闭会话并重试；记录 trace，不要发送旧 challenge |
| tag 202 result 0 后状态有回复 | 控制链路已成功，问题不在配对或 challenge |
| 媒体命令被拒绝 | 检查 owner-binding 是否属于当前设备与所有者 |

Windows 也不是每次都必然收到 challenge。研究记录包含成功与失败会话，因此 Agent 应按
实际 trace 判断，不要仅根据 Windows 设置页的“已配对/已连接”文字下结论。

## 6. 可直接交给另一个 Agent 的提示词

```text
请先阅读仓库根目录 AGENTS.md 和 docs/WINDOWS-AGENT.md。使用仓库虚拟环境完成只读
doctor 和 status 验证。目标设备 MAC 由我提供；不要从研究向量猜地址。只有在我让 Looki
进入配对模式后才运行 pair --renew。先证明 tag 200/201/202 和状态读取成功，再使用我
私下提供的 owner-binding 测试拍照、录音或媒体下载。保留 --trace，但不要输出 challenge、
owner-binding 或热点密码。
```
