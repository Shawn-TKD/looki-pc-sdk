# Looki PC SDK

一个面向用户自有 Looki L1 的非官方 Windows/macOS SDK。它让电脑在手机 App 未连接时，
直接通过蓝牙控制设备，并通过 Looki 自身热点读取原始媒体。

> 当前为实验性 `0.3.0`。Windows 11 已在一台 Looki L1（设备版本 1.53、软件版本
> 79）上实机验证；macOS 新配对会话已完成 challenge 与状态读取，普通重连、热点与
> 媒体闭环仍在验证。项目与 Looki 官方无隶属或授权关系。

## 为什么做这个项目

Looki 原本以手机 App 和云端服务为中心。这个项目把用户自己设备里的照片、录音和
视频接回个人电脑，让本地工具可以在用户控制的目录中完成下载、整理、转写、检索和
总结。媒体不必为了进入 AI 工作流而先上传到厂商云端。

一个典型链路是：

```text
Looki
  ├─ Bluetooth：认证、状态与拍摄控制
  └─ Wi-Fi hotspot：原始媒体下载
          ↓
     本地媒体目录
          ↓
  Codex / Claude Code / 本地 ASR / VLM
          ↓
  日记、相册索引、会议记录或个人记忆库
```

SDK 只负责可靠地连接设备并取得原始数据。选择什么模型、是否联网、保存多久，都由
用户自己的 Agent 和存储策略决定。完整设计见
[本地优先 AI 工作流](docs/LOCAL-FIRST-AI.md)。

## 已验证能力

| 能力 | Windows 11 | macOS |
|---|---|---|
| Classic Bluetooth 系统配对 | 已验证 | 已验证 |
| RFCOMM channel 3、LCMP、动态 challenge | 稳定复现 | 新配对会话成功过，普通重连不稳定 |
| 电量、版本、存储、媒体数量、录制状态 | 已验证 | 新配对会话已读取五项状态 |
| 电脑主动拍照、录音、录像、日记记录 | 已验证并生成媒体 | 未完成稳定实机验证 |
| 隐私灯开关 | 命令已验证 | 未验证 |
| Looki 热点、HTTP 媒体清单、JPG/M4A/MP4 原文件下载 | 已验证 | 未完成闭环验证 |

Windows 上的完整已验证链路是：电脑通过蓝牙完成认证和控制，Looki
再开启自身 Wi-Fi 热点，电脑通过 HTTP 读取媒体目录并下载原始文件。照片、
录音和视频文件不经过蓝牙传输。

## 平台状态

| 平台 | 状态 | 主机接口 |
|---|---|---|
| Windows 10/11 | 已实机验证 | Winsock RFCOMM、Bluetooth APIs、`netsh` |
| macOS | 实验性适配，部分实机验证 | PyObjC IOBluetooth、`networksetup` |

协议、认证、控制和 HTTP 下载代码在两个平台共用。只有 RFCOMM、系统配对和 Wi-Fi
切换属于平台后端。macOS 的安装、权限和已知问题见 [docs/MACOS.md](docs/MACOS.md)。
在提交 Mac 实机结果前，可按
[macOS 验证清单](docs/MACOS-VERIFICATION.md)逐层测试并生成脱敏诊断信息。
连接停在 challenge 时，使用 `--trace` 并参考
[认证握手说明](docs/research/AUTH-HANDSHAKE.md)和
[蓝牙会话建立时序](docs/research/BLUETOOTH-SESSION-TIMELINE.md)包含足以排查连接的
脱敏证据。macOS 普通重连问题见
[ACL 生命周期研究](docs/research/MACOS-ACL-LIFECYCLE.md)，无需公开原始手机抓包。

## 安装

需要 Python 3.11 或更高版本，以及同时支持 Classic Bluetooth 和 Wi-Fi 的电脑。

Windows：

```powershell
git clone https://github.com/Shawn-TKD/looki-pc-sdk.git
cd looki-pc-sdk
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip setuptools
.\.venv\Scripts\python.exe -m pip install -e .
```

也可以使用一键准备脚本：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap-windows.ps1
```

供另一台 Windows 电脑上的 Agent 使用的完整流程见
[Windows Agent 指南](docs/WINDOWS-AGENT.md)。仓库根目录的 [AGENTS.md](AGENTS.md)
会向支持仓库指令的编码 Agent 提供相同的操作边界和协议顺序。

macOS：

```bash
git clone https://github.com/Shawn-TKD/looki-pc-sdk.git
cd looki-pc-sdk
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip setuptools
.venv/bin/python -m pip install -e '.[macos]'
.venv/bin/looki doctor
```

## 快速验证

首次在一台电脑配对时，让 Looki 进入蓝牙配对模式，然后运行。Windows 使用
`.venv\Scripts\looki.exe`，macOS 使用 `.venv/bin/looki`：

```powershell
.\.venv\Scripts\looki.exe pair --address AA:BB:CC:DD:EE:FF --renew
```

macOS 首次配对不要使用 `--renew`；需要重新绑定时先在系统蓝牙设置中忽略设备：

```bash
.venv/bin/looki pair --address AA:BB:CC:DD:EE:FF
.venv/bin/looki status --address AA:BB:CC:DD:EE:FF
```

配对完成后退出配对模式并唤醒设备。只读状态不一定需要所有者绑定：

```powershell
.\.venv\Scripts\looki.exe status --address AA:BB:CC:DD:EE:FF
```

拍摄、录制和原始媒体访问需要设备自己的私有 owner-binding 文件：

```powershell
.\.venv\Scripts\looki.exe photo --address AA:BB:CC:DD:EE:FF --binding private\my-looki.looki-binding
.\.venv\Scripts\looki.exe media-list --address AA:BB:CC:DD:EE:FF --binding private\my-looki.looki-binding
.\.venv\Scripts\looki.exe download-one --address AA:BB:CC:DD:EE:FF --binding private\my-looki.looki-binding --kind jpg --output downloads
```

录音、录像与日记记录采用显式开始/停止命令：

```powershell
.\.venv\Scripts\looki.exe audio-start --address AA:BB:CC:DD:EE:FF --binding private\my-looki.looki-binding
.\.venv\Scripts\looki.exe audio-stop  --address AA:BB:CC:DD:EE:FF --binding private\my-looki.looki-binding
```

完整的第二台电脑迁移流程见 [docs/SECOND-PC.md](docs/SECOND-PC.md)。

## Python API

```python
from pathlib import Path
from looki import LookiControls, LookiSession, OwnerBinding

binding = OwnerBinding.load_portable(Path("private/my-looki.looki-binding"))

with LookiSession("AA:BB:CC:DD:EE:FF") as session:
    session.authenticate(owner_binding=binding)
    LookiControls(session).capture_photo()
```

## 项目结构

```text
src/looki/       跨平台 SDK、CLI、协议和设备功能
src/looki/macos/ macOS IOBluetooth、配对与 Wi-Fi 热点支持
src/looki/transport/ 跨平台 RFCOMM 字节流接口
proto/           逆向恢复的 LCMP v1/v2 schema
tools/           HCI/RFCOMM 分析工具，不含任何抓包
scripts/         Windows 环境准备和主机辅助脚本
docs/research/   协议、固件和 Android 平台研究结论
research-vectors/ 可公开的脱敏真实会话结构与时序
firmware/        可公开的 OTA 元数据、分区清单和系统属性摘录
private/         本地设备凭据，已被 .gitignore 排除
```

本仓库不包含厂商 APK、OTA、分区镜像、媒体、原始抓包、设备 MAC、热点口令、
用户 token 或 owner-binding。请只操作自己拥有或明确获准研究的设备。
