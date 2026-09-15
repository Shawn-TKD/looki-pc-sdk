# macOS Classic Bluetooth 会话准入与 ACL 生命周期

## 当前结论

macOS 剩余故障位于 LCMP challenge 之前。协议内容、protobuf 分帧和 owner-binding 不是
普通重连失败的主要原因。

| 层级 | macOS 实测 | 结论 |
|---|---|---|
| BR/EDR 配对 | 成功，link key 已由系统保存 | 系统绑定成立 |
| 认证与加密 | `bluetoothd` 记录 AES-CCM mode 2、key size 16 | 加密不是当前阻塞 |
| v1 SDP | 原始查询返回 105 字节、channel 3 | UUID 与 channel 正确 |
| L2CAP PSM 3 | 释放系统 HFP 后可以打开 | 底层通道可用 |
| RFCOMM | SABM、PN、DLCI 6、双向 MSC 与 Android 成功抓包一致 | 编码正确 |
| LCMP | 新配对会话曾完成 tag 200/201/202 和五项状态查询；普通重连时设备直接 DISC | 剩余问题是设备是否接受当前 ACL 会话 |

## Android 与 macOS 的连接生命周期差异

Android 官方 App 的成功流程是：

```text
配对 ACL
→ 认证和加密
→ 手机主动断开
→ Looki 主动建立新的普通 ACL
→ 反向 SDP
→ 手机查询 LCMP v1 SDP
→ 再认证和加密
→ RFCOMM channel 3
→ tag 200
```

macOS 的 `bluetoothd` 会把 Looki 同时识别为 Hands-Free 音频设备并自动连接 HFP。HFP
和 LCMP 都使用 L2CAP PSM 3 上的 RFCOMM multiplexer。实测中 HFP 抢占时原始探针无法
打开 PSM 3；释放 HFP 后可以完成 LCMP 所需的 SABM、PN 和 MSC。

`IOBluetoothDevice.isConnected()`、`CBClassicPeer.connectionHandle()` 与控制器真实
状态可能不同步。`bluetoothd` 已记录 Looki 发起反向 SDP 时，Python 仍可能看到未连接。
因此不能只依赖 IOBluetooth 的轮询状态判断入站 ACL 是否已经建立。

`IOBluetoothDevice.closeConnection()` 会先关闭 HFP、GATT、SerialPort 等 profile，
之后才释放 ACL。这与 Android 抓包中直接的 HCI Disconnect 时序不同，可能改变 Looki
内部对下一条 RFCOMM 会话的准入判断。

## 已排除的应用层原因

新配对会话已经在 Mac 上完成：

```text
tag 200
→ ACK + tag 201
→ tag 202 result=0
→ 电量、设备信息、媒体数量、存储、录制状态
```

完全绕过 SDK 后，原始 RFCOMM 探针仍可能得到：

```text
SABM 成功
→ PN 成功
→ DLCI 6 成功
→ 双向 MSC 成功
→ Looki 发送 DISC DLCI 0
```

因此普通重连失败不能归因于 SDK 的 LCMP 解析器，也不能通过预发 owner-binding 或重放
旧 challenge 解决。

## 已确认并修复的 PyObjC 数据问题

`IOBluetoothRFCOMMChannelDelegate` 的数据参数是无固定长度的 C 数组。PyObjC 将其表示
为 `objc.varlist`。对它直接切片再调用 `bytes()` 曾得到与真实 RFCOMM payload 等长的
全零数据。

SDK 现在使用 `data.as_buffer(length)` 取得有边界的原生内存视图，并在回调返回前复制
为 Python `bytes`。回归测试模拟了“切片返回全零、as_buffer 返回真实数据”的故障。

## 下一步探针

下一步应使用原生事件驱动方式：

1. 在配对或唤醒之前注册 baseband connect/disconnect notification；
2. 以控制器事件记录真实 ACL 边界，不以 `isConnected()` 轮询值为准；
3. 在 Looki 入站连接回调中阻止或立即释放 HFP profile；
4. 在同一条 ACL 上立即查询 v1 SDP 并打开 channel 3；
5. 记录设备 DISC 前最后一个 RFCOMM/HCI 事件和相对时间。

在原生探针完成前，反复删除绑定和重新配对只会偶尔进入一次可接受会话，不能解释普通
重连为何失败。

## 证据限制

当前仍没有 Windows 控制器级 HCI 成功抓包。Windows 应用层记录证明它能打开 channel 3
并静默等待 tag 200，但不能据此确定 Windows ACL、profile 抢占和 HCI 断开时序。后续若
取得 Windows HCI，应与 macOS 原生探针按相同相对时间格式对照。
