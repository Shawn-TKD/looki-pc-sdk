# 研究资料索引

本仓库保存可以公开复现的研究结论和工具，不保存厂商二进制或用户数据。

| 文档 | 内容 |
|---|---|
| [research/PROTOCOL.md](research/PROTOCOL.md) | RFCOMM、LCMP、认证、控制命令和媒体数据面 |
| [research/AUTH-HANDSHAKE.md](research/AUTH-HANDSHAKE.md) | challenge 状态机、安全 trace 与脱敏握手向量 |
| [research/ANDROID-PLATFORM.md](research/ANDROID-PLATFORM.md) | Android 11、Snapdragon W5、分区、DevoMain 特权应用 |
| [research/FIRMWARE-OTA.md](research/FIRMWARE-OTA.md) | OTA 结构、版本、更新路径与公开仓库边界 |
| [research/FIRMWARE-REVERSE-ENGINEERING.md](research/FIRMWARE-REVERSE-ENGINEERING.md) | 固件取得、拆包方法、模块地图和逆向进度 |
| [research/VERIFIED-RESULTS.md](research/VERIFIED-RESULTS.md) | 电脑独立读取与主动控制的实机证据摘要 |
| [LOCAL-FIRST-AI.md](LOCAL-FIRST-AI.md) | 不经厂商云端的媒体整理和 Agent 集成设计 |
| [SECOND-PC.md](SECOND-PC.md) | 第二台 Windows 电脑迁移和验证步骤 |
| [MACOS.md](MACOS.md) | macOS 安装、蓝牙权限、配对、热点和问题排查 |
| [MACOS-VERIFICATION.md](MACOS-VERIFICATION.md) | macOS 分层实机验证与脱敏记录模板 |

`proto/lcmp_v1.proto` 与 `proto/lcmp_v2.proto` 是从本地静态分析恢复的消息 schema。
`tools/analyze_phone_actions.py` 用于离线解析用户自己采集的 HCI/RFCOMM 数据，
并要求显式传入目标设备 MAC。它会隐藏已知凭据字段的内容。

## 证据分级

- **实机验证**：RFCOMM ch3、四字节分帧、challenge、状态读取、主动拍摄、热点、
  HTTP 列表与下载。
- **固件静态确认**：Android 11、分区结构、AVB、DevoMain 权限、AON 与 USB 模块。
- **仍需实验**：不同设备/固件兼容性、通用 owner enrollment、MTP、ADB、主动 OTA。

原始研究现场约 1.96 GB，包含 OTA、分区镜像、APK、媒体和抓包。这些材料用于本地
验证，但因体积、版权和凭据风险不进入公开 Git 历史。

`firmware/1.54.80/` 保存由固件生成的小型研究工件。它们可以用于核对版本和复现
分析，但不包含可刷写镜像。
