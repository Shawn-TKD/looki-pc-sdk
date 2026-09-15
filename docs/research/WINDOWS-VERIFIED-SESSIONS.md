# Windows 实机连接证据

## 2026-09-15 重新配对与状态读取

在 Looki 配对模式下，Windows 删除目标地址的旧 bond，并通过
`BluetoothAuthenticateDeviceEx` Dedicated Bonding 建立新绑定：

```text
remove_target_bond_status = 0
remembered = false
authenticated = false
auth callback: method 3, remote IO 3, accepted
authenticate_status = 0
```

紧接着连接 RFCOMM channel 3。客户端在连接后保持静默，Looki 首先发送 377 字节
RFCOMM payload，其中是 4 字节长度前缀和 373 字节 LCMP body：

```text
Looki → PC: seq 100001, tag 200, payload 365 bytes
PC → Looki: ACK 100001
PC → Looki: seq 1, tag 201, current challenge
Looki → PC: ACK 1
Looki → PC: seq 100004, tag 202, result 0
```

随后 PC 同时查询：

| 请求 | 回复 | 含义 |
|---:|---:|---|
| 19 | 20 | 电量 |
| 204 | 203 | 设备信息 |
| 49 | 50 | 媒体数量 |
| 45 | 46 | 存储 |
| 234 | 235 | 录制状态 |

五项查询全部获得回复。该会话没有发送 owner-binding，没有拍照、录音、录像或修改设置。
机器可读版本见
[`research-vectors/windows/status-success-20260915.json`](../../research-vectors/windows/status-success-20260915.json)。

## 成功与失败应如何使用

历史 Windows 记录同时包含以下情况：

- RFCOMM 无法建立；
- RFCOMM 建立后没有 challenge；
- 收到 tag 200 并成功状态查询；
- 发送 owner-binding 后启动媒体服务；
- 拍照、录音、录像和日记控制成功。

因此公开研究不应把一次成功描述为永久稳定。另一个 Agent 应运行真实 `--trace`，根据
连接停在哪一层决定唤醒、重试或重新配对。旧 challenge 和旧会话字节流只适合解析器
回归，不能作为新连接的认证输入。

## 公开抓包边界

公开仓库保留方向、长度、序号、tag、状态值和必要的 RFCOMM 控制帧。原始手机 HCI 中
还包含 link key、owner-binding、热点口令、账户与个人媒体上下文。这些字段不具备跨
设备复用价值，所以不作为 Windows 安装或操作的依赖。
