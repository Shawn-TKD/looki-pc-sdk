# 实机验证记录摘要

## 电脑独立读取

手机 App 未连接时，Windows 电脑完成：Classic RFCOMM 建链、动态 challenge、
owner-binding、`DeviceFileSync`、Looki 热点、HTTP 媒体目录和原始 JPEG 下载。
样本 JPEG 返回 HTTP 200，可正常解码为 4000 × 3000。

## 电脑主动控制

同一轮基线媒体总数为 27。电脑依次执行并检查目录增量：

| 操作 | 目录变化 |
|---|---|
| 拍照 | JPG +1 |
| 录音开始/停止 | M4A +1 |
| 普通录像开始/停止 | MP4 +1 |
| 日记记录开始/停止 | MP4 +1；停止后约十秒完成写盘 |

所有控制都在手机 App 未占用会话的条件下完成。隐私灯打开与恢复关闭命令已发送，
但设备协议没有提供独立设置回执，因此没有仅凭日志断言肉眼灯态。

## 配对经验

Windows 设置页可能只建立 BLE 记录。RFCOMM 需要 Classic Bluetooth Dedicated
Bonding；项目通过 Windows `BluetoothAuthenticateDeviceEx` 和目标设备专属的
Just Works 回调建立。电脑蓝牙关闭会出现 `WinError 10050`，Looki 未唤醒、低电、
被手机占用或 Classic 绑定失效时通常表现为连接超时。
