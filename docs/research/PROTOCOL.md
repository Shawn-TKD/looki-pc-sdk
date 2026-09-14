# 已验证的 Looki L1 协议

## 传输结构

```text
Windows Agent
  └─ Bluetooth Classic RFCOMM channel 3
       └─ 4-byte big-endian message length
            └─ LCMP v1 protobuf envelope
                 └─ device query / control / file-service messages
```

实机 HCI 重组确认控制面使用四字节大端长度分帧。早期“HTTP/1.1 直接运行在
RFCOMM 上”的假设与当前实机字节流冲突，SDK 不使用该旧假设。

设备会为每个连接发送新的 `DeviceAuthRequest`。客户端回送当前连接 challenge，
随后根据操作需要发送该设备的 owner-binding。历史 challenge 不能代替当前 challenge。

## 关键消息

| 外层 tag | 方向 | 含义 |
|---:|---|---|
| 19 → 20 | PC → Looki → PC | 电量查询与回复 |
| 45 → 46 | PC → Looki → PC | 存储状态 |
| 49 → 50 | PC → Looki → PC | 媒体数量 |
| 99 | PC → Looki | App/page 状态 |
| 103 | Looki → PC | 临时热点信息 |
| 200 → 201 → 202 | 双向 | challenge、认证响应、结果 |
| 203 / 204 | 双向 | 设备型号与版本 |
| 234 → 235 | 双向 | 录制状态 |
| 245 | PC → Looki | 隐私灯设置 |
| 253 | PC → Looki | 启动/停止文件同步 |
| 256 | Looki → PC | HTTP 文件服务地址 |
| 257 | PC → Looki | 拍摄与录制控制 |

`DeviceFunctionCmd` 的已验证映射：

| action | state=2 | state=1 |
|---:|---|---|
| 1 | 开始日记记录 | 停止日记记录 |
| 2 | 开始录像 | 停止录像 |
| 3 | 开始录音 | 停止录音 |
| 4 | 拍照触发 | 不使用 |

隐私灯使用 tag 245 的 field 1：`1` 为打开，`0` 为关闭。设备未观察到独立设置回执。

## 媒体数据面

媒体传输不经过 RFCOMM 搬运大文件：

```text
RFCOMM：认证、启动 DeviceFileSync、取得临时热点和 HTTP 服务参数
Wi-Fi：电脑关联 Looki 临时热点
HTTP：/files/list 与 /files/download?file=...
```

媒体目录和原文件访问需要 owner-binding。热点口令是当前会话数据，不应写入日志。
