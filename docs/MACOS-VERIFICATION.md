# macOS 实机验证清单

这份清单用于把 macOS 后端从“代码适配”推进到“实机验证”。每一步只在前一步成功后
继续，以便错误能定位到单一层级。诊断输出不读取 Looki 凭据、媒体、MAC 或热点口令，
可以直接提供给维护者或本地 Agent。

## 1. 主机环境

```bash
git pull
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip setuptools
.venv/bin/python -m pip install -e '.[macos]'
.venv/bin/looki doctor
```

预期结果：

- `sdk_platform` 是 `darwin`；
- Apple Silicon 原生环境的 `machine` 是 `arm64`；
- `objc`、`Foundation`、`IOBluetooth` 均为 `true`；
- `networksetup` 和 `ipconfig` 为 `true`；
- `wifi_interface` 通常是 `en0` 或 `en1`；
- `static_ready` 为 `true`。

`static_ready` 只表示依赖和系统工具存在。蓝牙权限、设备是否唤醒、RFCOMM 服务和 LCMP
认证必须在后续步骤验证。

## 2. Classic Bluetooth 配对

1. 断开手机 App 与 Looki 的连接。
2. 唤醒 Looki 并进入设备的蓝牙配对模式。
3. 确认启动命令的 Terminal、iTerm 或 IDE 已获得 macOS 蓝牙权限。
4. 执行：

```bash
.venv/bin/looki pair --address AA:BB:CC:DD:EE:FF
```

若旧绑定损坏，在系统设置的蓝牙页面手动“忽略此设备”，再重新配对。macOS 版本不使用
`--renew` 自动移除绑定。

## 3. RFCOMM 与 LCMP

退出配对模式并再次唤醒 Looki，然后执行：

```bash
.venv/bin/looki status --address AA:BB:CC:DD:EE:FF
```

成功标准是返回电量、型号或存储等 LCMP 状态。系统蓝牙页面显示“已连接”不是这一层的
成功标准。若失败，请保存完整错误文字和其中的 `IOReturn` 数值。

## 4. owner-binding 与控制

通过加密方式复制当前设备的私有 owner-binding：

```bash
mkdir -p private
.venv/bin/looki photo \
  --address AA:BB:CC:DD:EE:FF \
  --binding private/my-looki.looki-binding
```

观察设备是否拍照，再读取媒体数量。不要把 binding 文件、真实 MAC 或媒体提交到 Git。

## 5. 热点和媒体

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

验证四件事：Mac 加入 Looki 热点、取得局域网 IPv4、HTTP 返回媒体清单、命令结束后恢复
原 Wi-Fi。只有一个 Wi-Fi 接口的 Mac 在下载期间没有互联网，这是预期行为。需要云端
Codex 或 Claude Code 处理时，先完成下载和网络恢复，再调用模型。

## 6. 建议记录格式

```text
macOS：<版本>
Mac：<Apple Silicon / Intel>
Python：<版本>
SDK commit：<git rev-parse --short HEAD 的结果>
looki doctor：<完整 JSON，可公开>
pair：成功 / 错误文字
status：成功 / 错误文字
photo：成功 / 失败
media-list：成功 / 失败
download-one：成功 / 失败
Wi-Fi 自动恢复：成功 / 需手动
```

上传前删除真实设备 MAC、owner-binding、热点名称和口令、用户媒体及系统日志中的其他
设备名称。`looki doctor` 已按可分享场景设计，本身不输出这些字段。

## 7. 错误应该如何解释

| 失败位置 | 说明 |
|---|---|
| `doctor` | Python、PyObjC 或系统工具尚未准备好 |
| `pair` | macOS 权限、旧绑定或 Looki 配对模式问题 |
| `status` 打不开 channel 3 | Classic Bluetooth/RFCOMM 问题 |
| `status` 打开后等不到 challenge | Looki 工作状态或 delegate/run loop 问题 |
| `photo` 被拒绝 | owner-binding 或 App 状态同步问题 |
| `media-list` 切网失败 | macOS Wi-Fi 接口或热点关联问题 |
| 已切热点但 HTTP 超时 | DHCP、文件服务地址或会话持续时间问题 |
| 下载后未恢复网络 | 原 SSID 不可读、钥匙串缺少网络或进程被中断 |
