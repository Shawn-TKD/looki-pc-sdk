# Looki PC SDK

一个面向用户自有 Looki L1 的非官方 Windows SDK。它让电脑在手机 App 未连接时，
直接通过蓝牙控制设备，并通过 Looki 自身热点读取原始媒体。

> 当前为实验性 `0.1.0`，已在一台 Looki L1（设备版本 1.53、软件版本 79）和
> Windows 11 上实机验证。项目与 Looki 官方无隶属或授权关系。

## 已验证能力

| 能力 | 实机状态 |
|---|---|
| Windows Classic Bluetooth Dedicated Bonding | 已验证 |
| RFCOMM channel 3、LCMP 分帧、ACK、动态 challenge | 已验证 |
| 电量、型号、版本、存储、媒体数量、录制状态 | 已验证 |
| 拍照、录音、录像、日记记录 | 已验证并生成媒体 |
| 隐私灯开关 | 命令已验证；设备没有独立设置回执 |
| Looki 热点、HTTP 媒体清单、JPG/M4A/MP4 下载 | 已验证 |

## 安装

需要 Windows 10/11、Python 3.11 或更高版本，以及同时支持 Classic Bluetooth
和 Wi-Fi 的电脑。

```powershell
git clone https://github.com/Shawn-TKD/looki-pc-sdk.git
cd looki-pc-sdk
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip setuptools
.\.venv\Scripts\python.exe -m pip install -e .
```

## 快速验证

首次在一台电脑配对时，让 Looki 进入蓝牙配对模式，然后运行：

```powershell
.\.venv\Scripts\looki.exe pair --address AA:BB:CC:DD:EE:FF --renew
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
src/looki/       SDK、CLI、Windows 配对与热点支持
proto/           逆向恢复的 LCMP v1/v2 schema
tools/           HCI/RFCOMM 分析工具，不含任何抓包
docs/research/   协议、固件和 Android 平台研究结论
private/         本地设备凭据，已被 .gitignore 排除
```

本仓库不包含厂商 APK、OTA、分区镜像、媒体、原始抓包、设备 MAC、热点口令、
用户 token 或 owner-binding。请只操作自己拥有或明确获准研究的设备。
