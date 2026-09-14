# LCMP v1 认证握手与安全诊断

## 结论

连接卡在 challenge 后面，不是因为公开仓库缺少一把通用 challenge 密钥。Looki 每次
建立 RFCOMM 会话都会生成新的 challenge；客户端必须回送本次连接的值，旧值不能重放。

原始手机 HCI 抓包没有公开，因为其中含有用户和设备绑定上下文。建立基本状态查询不
需要上传原始抓包。拍照、录制和媒体服务则需要对应设备所有者的私有
`*.looki-binding` 文件，它也不能成为公共仓库内容。

## 已验证状态机

| 顺序 | 方向 | LCMP 内容 | 处理 |
|---:|---|---|---|
| 1 | Looki → client | seq + tag 200 `DeviceAuthRequestPb` | ACK 设备 seq；读取 field 1 当前 challenge |
| 2 | client → Looki | seq + tag 201 `DeviceAuthResultPb` | field 1 原样放入当前 challenge |
| 3 | Looki → client | ACK 客户端 seq | 说明 tag 201 帧已被设备接收 |
| 4 | Looki → client | seq + tag 202 `AuthResultSyncPb` | 空 payload 等价于 protobuf 默认 result 0；已验证为 challenge 阶段通过 |
| 5 | client → Looki | tag 205 + tag 276 | 需要受保护功能时发送该设备 owner-binding |
| 6 | client → Looki | tag 99 或业务查询 | 设置页面状态或读取状态 |

手机成功重连抓包在 owner 信息之后还出现过 tag 202、`result=2`。它出现在已经成功的
会话中，因此不能直接解释成失败；具体枚举名称仍未从固件中恢复。SDK 当前只把第一个
challenge 结果的非零值视为拒绝。

客户端和设备各自维护序号。收到对方外层 field 1 序号时，用外层 field 2 返回 ACK；
不能把设备序号拿来作为自己的发送序号。PC 从 1 开始发送已经过实机验证。

## 安全 trace

所有需要设备连接的 CLI 命令支持 `--trace`：

```bash
.venv/bin/looki status --address AA:BB:CC:DD:EE:FF --trace
```

trace 只记录事件、tag、序号、wire type 和长度。它不会输出 challenge 内容、
owner-binding、热点信息或媒体名称。关键事件包括：

```text
transport.opening
transport.connected
auth.challenge.received
lcmp.send                 tag=201
lcmp.ack.send
auth.challenge.accepted   result=0
```

若最后一条是 `auth.challenge.received`，说明 Mac 已能接收 IOBluetooth delegate 数据，
问题位于 tag 201 写出或设备 ACK。若收到 tag 201 的 ACK 但没有 tag 202，问题位于设备
认证状态；若出现 `auth.challenge.accepted` 后业务仍无回复，才需要检查 owner-binding、
AppStateSync 或业务消息。

## 为什么不上传原始抓包

原始数据可能同时包含：

- owner 的 UserInfoSync 和 LoginStateSync；
- 设备 MAC、手机蓝牙标识和连接时间线；
- Looki 临时热点名称及口令；
- Wi-Fi 配置、媒体文件名或账户上下文。

公共研究应发布状态机、schema、脱敏结构和可复现工具。只有设备所有者自己的客户端才
应持有 owner-binding。机器可读的脱敏成功序列见
[`research-vectors/lcmp-v1/handshake-success.json`](../../research-vectors/lcmp-v1/handshake-success.json)。
