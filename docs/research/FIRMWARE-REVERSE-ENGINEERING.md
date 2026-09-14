# Looki L1 固件逆向进展

本文记录固件研究的证据来源、分析步骤、已经理解的模块和仍待验证的部分。协议实机
结论以 [PROTOCOL.md](PROTOCOL.md) 为准；静态分析不能代替设备行为验证。

## 研究样本

| 项目 | 内容 |
|---|---|
| OTA 版本 | 1.54.80，完整 A/B OTA |
| 系统版本 | Android 11 / SDK 30 |
| 设备代号 | `monaco_go` |
| 核心系统 App | `ai.looki.devo` / `DevoMain.apk` |
| 实机对照版本 | 设备版本 1.53、软件版本 79 |

OTA 和实机不是同一软件版本，因此静态发现只代表 1.54.80 样本。只有在实机通信中
观察到的行为才列为“实机验证”。公开样本元数据位于
[`firmware/1.54.80/`](../../firmware/1.54.80/)。

## 取得与拆包流程

1. 从官方升级接口确认设备可用版本和官方 CDN 上的更新对象。
2. 下载标准 Android A/B OTA ZIP，读取 `META-INF/com/android/metadata` 与
   `payload_properties.txt`。
3. 解析 `payload.bin` 的 update-engine manifest，恢复 12 个分区镜像。
4. 遍历 ext4 `system`、`vendor`、`product` 和 `system_ext`，定位 Looki 特有组件。
5. 从 `system/priv-app/DevoMain/DevoMain.apk` 提取 DEX、资源和原生库。
6. 从 DEX 内嵌的 protobuf descriptor 恢复 LCMP v1/v2 schema，再用手机 HCI 抓包与
   PC 实机通信校正消息含义。

仓库中的 `tools/ota_list_partitions.py`、`tools/ext4_walk.py` 和
`tools/ext4_getfile.py` 对应第 3、4 步。它们分析用户已经合法取得的本地文件，不负责
下载或刷写固件。

## 系统与启动链

| 模块 | 当前理解 | 证据 |
|---|---|---|
| Android 系统 | Android 11，32 位 ARM，Linux 5.4 | OTA metadata、build properties、boot image |
| SoC 平台 | Qualcomm `monaco_go`，高置信度对应 Snapdragon W5 / SW5100P | build properties、xbl/abl、设备资料 |
| 启动与更新 | A/B update-engine；12 个 payload 分区 | OTA 结构与 payload manifest |
| 系统校验 | `vbmeta` 与 `vbmeta_system` 存在，AVB 启用 | 分区头与启动链 |
| SELinux | 本样本启动参数为 permissive | boot cmdline 静态分析 |
| USB | 系统含 adbd，DevoMain 拥有 `MANAGE_USB` | system 文件树与特权权限；外部入口尚未验证 |

“系统包含 adbd”不等于电脑已经能够使用 ADB。USB gadget 配置、授权界面和量产系统
属性仍可能关闭外部调试入口。

## DevoMain 模块地图

`DevoMain.apk` 是设备侧的特权系统应用，也是当前最有价值的逆向对象。

| 模块 | 作用 | 进度 |
|---|---|---|
| `base.bluetooth` / `protocol.lcmp` | Classic Bluetooth、LCMP 会话和 protobuf 消息 | schema 已恢复；核心链路已实机验证 |
| `base.camera` | 拍照、录像、媒体参数 | 拍照与录像控制已实机验证 |
| `base.audio` | 录音、播放和提示音 | 录音控制已实机验证；实时音频流待研究 |
| `base.wifi` | 扫描、连接、热点和频段 | 临时热点已实机验证；通用 Wi-Fi 控制待完善 |
| `lib.download` / `lib.upgrade` | APK 与系统 OTA 更新 | 状态机已定位；没有执行主动升级 |
| `base.sys` | 时间、存储、USB、重启与恢复 | 状态查询部分验证；MTP/ADB/重启未测试 |
| AON Utility Service | always-on、自动记录和语音相关服务 | 类与消息已定位；状态机尚未完整理解 |
| iAP2 native library | Apple accessory 通道 | 组件存在；未纳入 PC SDK |

应用拥有 Bluetooth privileged、Wi-Fi tethering、安装软件包、管理 USB、设置系统时间、
重启和恢复出厂等特权。这解释了它为何可以统一管理相机、热点、升级和外设模式，也说明
未经实机确认不应随意调用高影响命令。

## 协议恢复进展

- 已从 DEX 恢复 LCMP v1/v2 protobuf schema，并提交到 `proto/`。
- 已识别约 60 个 `onLcmp*` 处理器，覆盖电量、存储、媒体、Wi-Fi、AON、OTA、USB、
  灯光、音量和设备锁等功能域。
- 已通过 HCI/RFCOMM 字节流纠正早期分帧判断：当前实机 LCMP v1 使用四字节大端长度
  前缀，不使用早期静态分析所猜测的 HTTP-over-RFCOMM 路径。
- 已理解动态 challenge、owner-binding 和 App 状态同步对工作模式连接的作用。
- 已从电脑独立完成状态查询、拍照、录音、录像、日记记录、热点启动、媒体清单和原始
  JPG/M4A/MP4 下载。

## 固件文件公开范围

本仓库收录：

- OTA 原始 metadata 与 payload properties；
- 从系统镜像筛选出的非敏感 build properties；
- 由 payload manifest 生成的分区大小和操作数量；
- 由 system 镜像生成的文件树和由 DevoMain DEX 生成的协议符号清单；
- 自研解析工具、恢复的 protobuf schema 和研究报告。

本仓库不收录：

- 完整 OTA、`payload.bin`、分区镜像、APK 或原生库；
- 从用户设备提取的 `/data` 内容、日志或媒体；
- 手机抓包、owner-binding、热点口令、账户 token 和设备标识。

这些限制让别人能够审阅和复现分析过程，同时避免重新分发完整厂商代码或公开设备凭据。

## 下一阶段

1. 在第二台 Windows 电脑和一台 macOS 电脑验证 owner-binding 的可迁移范围。
2. 完成媒体增量同步，覆盖 JPG、M4A、MP4 的下载和恢复电脑 Wi-Fi。
3. 验证 USB File Transfer/MTP 是否能成为有线高速数据面。
4. 继续分析 AON、实时语音、Wi-Fi 保存列表与设备日志协议。
5. 对照 1.53.79 实机与 1.54.80 OTA，记录协议字段和行为差异。
6. 若有第二台 Looki，研究每设备 enrollment，避免把单设备凭据误认为通用认证。
