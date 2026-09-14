# 在第二台 Windows 电脑验证

这套流程适用于同一台 Looki。第二台电脑需要新的 Windows Classic Bluetooth 绑定，
但可以使用该设备已有的应用层 owner-binding。不要通过 GitHub 传递 owner-binding。

## 1. 第一台电脑导出私有绑定

在研究目录已有“手机发往 Looki 的重组 LCMP 流”时执行：

```powershell
looki enroll --capture C:\private\phone-to-looki.bin --output private\my-looki.looki-binding
```

输出文件是未加密的设备凭据。用加密 U 盘或加密压缩包将它复制到第二台电脑的
`private\`，不要提交到 Git。

## 2. 安装 SDK

```powershell
git clone https://github.com/Shawn-TKD/looki-pc-sdk.git
cd looki-pc-sdk
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip setuptools
.\.venv\Scripts\python.exe -m pip install -e .
```

## 3. 建立 Classic Bluetooth 绑定

关闭手机 App 的 Looki 连接，让 Looki 进入蓝牙配对模式。以管理员身份打开
PowerShell，立即运行：

```powershell
.\.venv\Scripts\looki.exe pair --address AA:BB:CC:DD:EE:FF --renew
```

成功后退出配对模式，短按实体键唤醒设备。Looki 控制使用的是 Classic Bluetooth
RFCOMM，不是 Windows 设置页看到的 BLE GATT 项目；只出现 BLE 项目时仍无法控制。

## 4. 由浅到深验证

```powershell
# 只读：电量、版本、存储、媒体数量、录制状态
.\.venv\Scripts\looki.exe status --address AA:BB:CC:DD:EE:FF

# 电脑主动拍照
.\.venv\Scripts\looki.exe photo --address AA:BB:CC:DD:EE:FF --binding private\my-looki.looki-binding

# 验证媒体目录；电脑会临时切到 Looki 热点，再恢复此前的 Wi-Fi
.\.venv\Scripts\looki.exe media-list --address AA:BB:CC:DD:EE:FF --binding private\my-looki.looki-binding

# 下载一个原始文件
.\.venv\Scripts\looki.exe download-one --address AA:BB:CC:DD:EE:FF --binding private\my-looki.looki-binding --kind jpg --output downloads
```

录音、录像和日记记录必须成对执行开始与停止：

```powershell
.\.venv\Scripts\looki.exe video-start --address AA:BB:CC:DD:EE:FF --binding private\my-looki.looki-binding
.\.venv\Scripts\looki.exe video-stop  --address AA:BB:CC:DD:EE:FF --binding private\my-looki.looki-binding
```

## 常见故障

| 现象 | 原因与处理 |
|---|---|
| `WinError 10050` | 电脑蓝牙无线电未开启 |
| `WinError 10060` / 连接超时 | Looki 未唤醒、低电、手机占用会话，或 Classic 绑定未成功 |
| Windows 只显示 BLE 服务 | 在 Looki 配对模式下重新运行 `looki pair --renew` |
| 日记停止后立即无法连接 | 设备仍在生成日记视频；等待约十秒 |
| 媒体热点连接后没有网络 | 这是正常的本地热点；文件传完会恢复原 Wi-Fi |
