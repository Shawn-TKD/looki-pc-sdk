# Looki 蓝牙会话建立时序

本文专门记录 LCMP challenge 之前的链路与 RFCOMM 行为。所有地址、链路密钥、
challenge、owner-binding、热点口令和个人数据均已删除。

## 证据边界

- 目前没有 Windows 控制器级 HCI 抓包。因此，Windows 代码设置
  `SO_BTH_AUTHENTICATE`、`SO_BTH_ENCRYPT` 并成功通信，只能证明它请求了这些属性，
  不能反推某次连接一定出现了 HCI `Authentication Complete` 和
  `Encryption Change` 事件。
- 下面的完整 HCI/RFCOMM 时序来自官方 Android App 的一次成功连接。
- Windows 已多次取得成功的 RFCOMM 应用层收发记录：打开 channel 3 后客户端保持
  静默，Looki 主动发送 tag 200。Windows 记录不包含 PN、MSC、RPN 等控制器层数据。

## 一次成功连接的脱敏时序

相对时间从 BR/EDR `Connection Complete` 开始：

| 时间 | 方向 | 事件或帧 | 脱敏内容 |
|---:|---|---|---|
| +0.000 s | controller → host | Connection Complete | status=0 |
| +1.540 s | controller → host | Authentication Complete | status=0 |
| +1.576 s | controller → host | Encryption Change | status=0, enabled=2 |
| +1.638 s | client → Looki | RFCOMM SABM | DLCI 0 |
| +1.646 s | Looki → client | RFCOMM UA | DLCI 0 |
| +1.647 s | client → Looki | RFCOMM PN command | `83 11 06 f0 00 00 de 03 00 07` |
| +1.728 s | Looki → client | RFCOMM PN response | `81 11 06 e0 00 00 de 03 00 07` |
| +1.729 s | client → Looki | RFCOMM SABM | DLCI 6 / server channel 3 |
| +1.739 s | Looki → client | RFCOMM UA | DLCI 6 |
| +1.740 s | client → Looki | RFCOMM MSC command | `e3 05 1b 8d` |
| +1.747 s | Looki → client | RFCOMM MSC response | `e1 05 1b 8d` |
| +1.748 s | Looki → client | RFCOMM MSC command | `e3 05 1b 8d` |
| +1.749 s | client → Looki | RFCOMM MSC response | `e1 05 1b 8d` |
| +1.889 s | Looki → client | 第一条应用数据 | LCMP tag 200，认证内容已删除 |
| +1.894 s | client → Looki | ACK + tag 201 | 本次 challenge 回显，值已删除 |

PN 中请求 DLCI 6、最大帧长 `0x03de`（990 字节）和 7 个初始 credits。此次成功会话
没有观察到 RPN，因此没有需要复制的波特率、数据位、停止位或校验位参数。RFCOMM 是
蓝牙虚拟串口；这里的成功协商依赖 PN 和 MSC，不依赖 RPN。

第一条 LCMP 数据的安全结构表示为：

```text
Looki → client
00 00 01 75 | 08 <device-seq> | c2 0c ed 02 | [tag 200 payload withheld]
```

这条记录回答了 challenge 前的先后关系：本次成功会话中，客户端没有先发送 Location、
AppStateSync 或其他 LCMP 初始化帧。Windows 成功脚本也采用相同行为。另一次手机重连
曾先发送 Location 再收到 challenge，说明 App 可以提前同步状态，但它不是所有成功
连接的必需前导帧。

## 服务 UUID 与 channel

设备 SDP 对 LCMP v1 accessory UUID
`00000000-1000-1234-abcd-1234567890ff` 返回：L2CAP、RFCOMM、server channel 3。
LCMP v2 使用末尾为 `fe` 的 UUID。手机端对应的反向 UUID
`00000000-2000-1234-abcd-1234567890ff` 在成功连接中返回空 SDP 结果，因此电脑无需
提供反向 RFCOMM 服务。

若 macOS 把 “Companion Message Protocol” 显示为 channel 1，应把它视为另一个 SDP
记录或系统层名称映射，不能用它覆盖上述实际 SDP 查询结果。当前 LCMP v1 数据通道仍
是 channel 3（RFCOMM DLCI 6）。

## owner-binding 的位置

基础状态读取已经在 Windows 上两次验证为：tag 200 → tag 201 → 状态查询，全程不发送
tag 205 或 tag 276。因此 owner-binding 不是让设备发送 challenge、保持基础状态会话的
前置条件。

拍照、录音、录像、文件同步和媒体下载属于受保护操作，SDK 会在 challenge 成功后发送
这台设备对应的 owner-binding。它不应在 challenge 前发送，也不能解决未收到 tag 200
的问题。

## 对 macOS 故障的直接判断

macOS 已能打开 channel 3，却在约两秒后被设备关闭，而且系统记录链路加密为 0。结合
成功手机会话在 RFCOMM 之前已经完成认证和加密，当前首要问题是 macOS 基带链路的认证/
加密与异步 RFCOMM 打开流程，而不是 LCMP 状态字段、owner-binding 或 AppStateSync。

SDK 的 macOS transport 因此改为：先确认系统配对，建立基带连接并调用
`requestAuthentication()`，再通过异步 RFCOMM API 打开 channel 3，并等待
`rfcommChannelOpenComplete:status:` 回调。下一次真机测试仍应同时观察 macOS 的链路
加密状态；`--trace` 的 `transport.connected` 会输出 `authentication_status` 和
`encryption_mode`，不包含设备身份或凭据。只有收到 tag 200 后，才进入 LCMP 层排查。
