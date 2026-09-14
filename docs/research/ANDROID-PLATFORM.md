# Looki L1 的 Android 平台

对厂商签名的 1.54.80 OTA 做离线分析后，确认 Looki L1 不是简单 MCU 相机，而是
一台定制 Android 设备。

| 项目 | 研究结论 |
|---|---|
| 系统 | Android 11 / SDK 30，`user` build |
| 平台 | Qualcomm `monaco_go`；结合启动链和拆机资料，高置信度为 Snapdragon W5 / SW5100P |
| CPU ABI | 32-bit ARM (`armeabi-v7a`) |
| 内核 | Linux 5.4.210-perf |
| 安全启动 | 存在 `vbmeta` / `vbmeta_system`，AVB 已启用 |
| SELinux | OTA 启动参数显示 permissive |
| 存储 | 实机协议报告约 32 GB；媒体由 Android 文件系统管理 |

## 设备核心应用

`ai.looki.devo` / `DevoMain.apk` 是预装特权系统应用，负责蓝牙、Wi-Fi 热点、
录音录像、按键、OTA、USB 模式和媒体服务。系统授予的特权包含：

- Bluetooth privileged control；
- Wi-Fi tethering；
- secure settings、系统时间和时区；
- package install、reboot、master clear；
- USB gadget management 和 input monitoring。

固件中还存在 AON Utility Service、Looki 日志服务、Qualcomm 启动分区，以及
iAP2、图像增强、畸变校正和 JPEG 原生库。设备会在 `/data/log` 下维护电池、
Looki 和系统日志。

## 这意味着什么

Android 平台让 Looki 具备比常见裸机运动相机更高的软件上限：可以由特权 App
组合蓝牙控制、热点传输、媒体处理、OTA 和 always-on 服务。但它仍受 AVB、厂商
签名、未确认的 USB 调试入口和硬件资源限制。当前项目优先复用官方设备服务，
没有修改 boot/system、绕过 AVB、root 或刷入非官方固件。

## 已确认与待确认

已确认：Android 11 系统镜像、分区结构、特权 App、热点与媒体服务、Classic
Bluetooth 控制面、录音录像和日记记录。

待确认：ADB 是否能通过官方设置开启、MTP 控制是否能稳定用于文件传输、第二台
Looki 的 owner-binding 登记差异、不同固件版本的协议兼容性。
