# 在 macOS 上使用 Looki PC SDK

## 当前状态

macOS 适配已经覆盖：

- Apple IOBluetooth 上的 Classic Bluetooth RFCOMM channel 3；
- LCMP challenge、owner-binding、状态读取和拍摄控制；
- 通过 `networksetup` 加入 Looki 临时热点；
- HTTP 媒体清单与 JPG、M4A、MP4 下载；
- 传输结束后删除临时热点记录并尝试恢复原 Wi-Fi。

Windows 路径已经实机验证。macOS 已验证系统 BR/EDR 配对、基带连接和 channel 3 的
异步打开，但尚未收到设备主动发送的 tag 200 challenge，因此仍标记为实验性。当前
故障和协议证据见 [BLUETOOTH-SESSION-TIMELINE.md](research/BLUETOOTH-SESSION-TIMELINE.md)。
打通 challenge 后再按 `status` → `photo` → `media-list` → `download-one` 验证。

安装后可以先运行不接触设备的诊断：

```bash
.venv/bin/looki doctor
```

它只输出 macOS、CPU、Python、PyObjC 模块、系统网络工具和 Wi-Fi 接口是否可用，不
读取设备 MAC、owner-binding、热点口令或媒体。

## 为什么 macOS 需要单独适配

macOS 上的 Python 不提供 Windows/Linux 风格的 RFCOMM socket。SDK 因此通过 PyObjC
调用 Apple 的 IOBluetooth 框架，先请求已有基带连接完成认证，再异步打开 RFCOMM
channel 3，并等待 open-complete delegate。接收数据时运行 Objective-C run loop，
再把它转换为 SDK 通用的阻塞字节流。同步 RFCOMM API 在真实 Mac 上返回过
`0xe00002bc`，不再使用。

LCMP、protobuf、认证和媒体 HTTP 协议没有改变。平台差异只在下面三层：

```text
LookiSession / LCMP / owner-binding       两个平台共用
                 │
       RFCOMM transport abstraction
          ┌──────┴──────┐
       Windows        macOS
       Winsock      IOBluetooth
       netsh        networksetup
```

## 安装

建议使用 python.org 或 Homebrew 的原生 Python 3.11 以上版本。在 Apple Silicon Mac 上
优先使用 arm64 Python，避免 Terminal、Python 和 PyObjC 分别运行在 arm64/Rosetta
环境中。

```bash
git clone https://github.com/Shawn-TKD/looki-pc-sdk.git
cd looki-pc-sdk
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip setuptools
.venv/bin/python -m pip install -e '.[macos]'
.venv/bin/looki --help
```

`macos` 可选依赖会安装 PyObjC 的 Cocoa 和 IOBluetooth bindings。不要使用 Windows
生成的 `.venv`，虚拟环境不能跨操作系统复制。

## 蓝牙权限与配对

首次运行时，macOS 可能询问 Terminal、iTerm、Python 或所用 IDE 是否可以访问蓝牙。
应在“系统设置 → 隐私与安全性 → 蓝牙”中允许实际启动 SDK 的宿主应用。更换终端或
Python 路径后，macOS 可能把它视为新的宿主并再次请求权限。

让 Looki 进入蓝牙配对模式，并确保手机 App 已断开，然后执行：

```bash
.venv/bin/looki pair --address AA:BB:CC:DD:EE:FF
```

SDK 只接受命令中指定地址的设备，并自动确认 Looki 的数字比较请求。若设备已经在
macOS 中配对，命令会直接返回。`--renew` 无法通过 Apple 的公开 API 自动删除现有
绑定；需要先在“系统设置 → 蓝牙”中找到 Looki，选择“忽略此设备”，再重新运行配对。

macOS 显示“已连接”只代表系统的基带连接状态，不证明 RFCOMM channel 3 和 LCMP
认证已经成功。以下只读查询才是控制通路验证：

```bash
.venv/bin/looki status --address AA:BB:CC:DD:EE:FF
```

## owner-binding

owner-binding 文件可在 Windows 与 macOS 间迁移，因为它保存的是 Looki 所有者上下文，
不是 Windows DPAPI 数据。应通过加密介质复制，不要放入 Git、聊天记录或公开网盘。

```bash
mkdir -p private
# 将私下传输的文件放到 private/my-looki.looki-binding
.venv/bin/looki photo \
  --address AA:BB:CC:DD:EE:FF \
  --binding private/my-looki.looki-binding
```

新 Mac 仍需要建立自己的系统蓝牙绑定。复制 owner-binding 不能替代 macOS 配对。

## 媒体与 Wi-Fi 切换

媒体文件不会通过蓝牙传输。SDK 先通过蓝牙请求 Looki 开启临时热点，再让 macOS 加入
该热点，通过局域网 HTTP 读取媒体。Mac 只有一个 Wi-Fi 接口时，这段时间会暂时离开
原网络，因此云端 Agent 可能短暂离线。

```bash
.venv/bin/looki media-list \
  --address AA:BB:CC:DD:EE:FF \
  --binding private/my-looki.looki-binding

.venv/bin/looki download-one \
  --address AA:BB:CC:DD:EE:FF \
  --binding private/my-looki.looki-binding \
  --kind jpg \
  --output downloads
```

SDK 会从 `networksetup -listallhardwareports` 自动识别 Wi-Fi 设备。需要覆盖时可传
`--interface en0` 或实际接口名。热点密码会作为 `networksetup` 的进程参数短暂传给
macOS，但 SDK 不把它写入输出或日志。

退出媒体命令时，SDK 会删除 Looki 临时首选网络并尝试重新加入原 SSID。如果原网络
未保存在钥匙串、企业网络需要额外认证，或程序被强制终止，自动恢复可能失败；这时在
macOS 菜单栏手动选择原网络即可。

部分较新的 macOS 配置会限制命令行读取当前 SSID。此时下载仍可能成功，但 SDK 无法
记住切换前的网络，也就不能自动恢复。表现是命令结束后仍连接 Looki 热点；从菜单栏
重新选择原网络即可。

## 常见问题

| 现象 | 常见原因 | 处理方法 |
|---|---|---|
| 安装时找不到 `IOBluetooth` | 没安装 macOS 可选依赖 | 运行 `pip install -e '.[macos]'` |
| 配对后 `status` 仍无法连接 | 手机占用、Looki 未唤醒或只有低功耗蓝牙记录 | 断开手机，唤醒 Looki；忽略设备后重新配对 |
| channel 3 打开后约两秒被设备关闭 | 基带链路未认证/加密，或异步 open-complete 未正确完成 | 更新到使用异步 RFCOMM 的版本，运行 `--trace`，并检查系统链路加密状态 |
| 出现蓝牙权限错误 | Terminal/Python 没有 Bluetooth 权限 | 在“隐私与安全性 → 蓝牙”授权后重开终端 |
| PyObjC 安装或加载失败 | Python 架构与 Terminal/Rosetta 不一致 | 在 Apple Silicon 上统一使用原生 arm64 Python |
| `media-list` 后网络中断 | Mac 已切到 Looki 的无互联网热点 | 等命令结束自动恢复，或手动选回原 Wi-Fi |
| 下载成功但没有自动恢复 Wi-Fi | macOS 未向命令行返回原 SSID，或钥匙串没有该网络 | 从菜单栏手动选择原网络 |
| 找不到 Wi-Fi 接口 | 接口被禁用，或接口名不是 `en0` | 开启 Wi-Fi；用 `networksetup -listallhardwareports` 查看并传 `--interface` |
| HTTP 服务超时 | 热点尚未取得 IPv4，或 LCMP 文件同步会话已结束 | 唤醒设备后重试，保持蓝牙会话和热点切换连续 |
| `--renew` 提示不能执行 | macOS 公开 API 没有可靠的自动忘记设备流程 | 在系统设置中手动“忽略此设备” |

## 第一次实机验证需要记录什么

在 Mac 上验证时，请保存命令、macOS 版本、Intel/Apple Silicon、Python 版本、错误中的
IOReturn 数值，以及成功时的媒体数量。不要保存或公开 owner-binding、热点密码、设备
真实 MAC 和下载的个人媒体。验证结果会用于调整 PyObjC 方法签名、run loop 和 Wi-Fi
恢复行为，然后把 macOS 状态从“实验性”提升为“实机验证”。

## Apple 接口资料

- [IOBluetooth 框架](https://developer.apple.com/documentation/iobluetooth)
- [IOBluetoothDevice.openRFCOMMChannelAsync](https://developer.apple.com/documentation/iobluetooth/iobluetoothdevice/openrfcommchannelasync%28_%3Awithchannelid%3Adelegate%3A%29)
- [IOBluetoothDevice.requestAuthentication](https://developer.apple.com/documentation/iobluetooth/iobluetoothdevice/requestauthentication%28%29)
- [IOBluetoothRFCOMMChannelDelegate](https://developer.apple.com/documentation/iobluetooth/iobluetoothrfcommchanneldelegate)
- [IOBluetoothDevicePair](https://developer.apple.com/documentation/iobluetooth/iobluetoothdevicepair)
- [使用 networksetup 确认接口](https://developer.apple.com/documentation/network/recording-a-packet-trace)

这些链接描述的是 macOS 主机接口。Looki 的 channel 3、LCMP framing 和消息映射来自
本项目的固件分析与实机抓包，不是 Apple 定义的协议。
