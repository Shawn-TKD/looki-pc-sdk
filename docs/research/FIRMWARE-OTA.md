# 固件与 OTA 研究

## 已获得版本

官方更新接口返回的研究版本为 `1.54.80`：系统 OTA 约 348 MB，设备端
`DevoMain.apk` 约 14.7 MB。实际测试设备在协议查询时报告设备版本 `1.53`、
软件版本 `79`，因此不能假设 OTA 静态分析与实机运行版本完全一致。

公开仓库只记录版本、校验信息和分析结论，不重新分发厂商 APK、OTA 或分区镜像。

## OTA 分区

完整 OTA payload 中恢复出 12 类镜像：

| 分区 | 大致大小 | 作用 |
|---|---:|---|
| system | 377 MB | Android 根系统 |
| vendor | 236 MB | Qualcomm/设备厂商实现 |
| boot | 101 MB | 内核和 ramdisk |
| modem | 83 MB | Qualcomm 固件 |
| product | 67 MB | 产品层组件 |
| system_ext | 64 MB | 系统扩展 |
| recovery | 50 MB | 恢复环境 |
| dtbo | 8 MB | 设备树覆盖 |
| xbl / abl | 约 3.3 MB | Qualcomm 启动链 |
| vbmeta / vbmeta_system | 数 KB | Android Verified Boot 元数据 |

## 更新架构

静态字符串和更新状态机显示，官方 App 从云端查询版本并下载系统 OTA 或
`DevoMain.apk`，校验后请求 Looki 开启热点，再把更新文件传给设备安装。媒体读取
已实机确认使用热点上的 HTTP；更新上传路径的 SFTP 判断来自 App 静态分析，尚未在
本项目中执行主动 OTA。

## 为什么当前项目不刷机

现有官方设备服务已经提供拍摄、录音、录像、日记和原始媒体访问。直接复用这些服务
风险更低，也不需要处理 AVB、厂商签名、bootloader 和失败恢复。Android 平台研究
仍有价值，因为它解释了设备为什么能提供热点、媒体服务、AON、USB 模式和独立 OTA。

当前项目没有 root 设备、修改系统镜像、绕过 AVB、触发恢复出厂或刷入非官方固件。
