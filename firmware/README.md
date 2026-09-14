# 固件研究工件

此目录保存能够公开审阅的小型固件研究工件。它们来自官方 1.54.80 Android A/B OTA，
用于证明版本、平台和分区结论。

这里没有可刷写固件。完整 OTA、`payload.bin`、分区镜像、`DevoMain.apk` 和原生库不在
Git 历史中。`.gitignore` 也会阻止常见厂商二进制格式被意外提交。

| 路径 | 内容 |
|---|---|
| `1.54.80/ota-metadata.txt` | OTA 包内原始 Android metadata |
| `1.54.80/payload-properties.txt` | update-engine payload 属性 |
| `1.54.80/selected-build-properties.txt` | 从 system build properties 筛选的非敏感字段 |
| `1.54.80/partition-map.json` | 从 payload manifest 和镜像分析生成的分区清单 |
| `1.54.80/system-filetree.txt` | 从 `system.img` 生成的 2,397 项路径清单 |
| `1.54.80/devomain-protocol-inventory.txt` | 从 DevoMain DEX 生成的消息、字段、处理器与命令名 |

分析方法和进度见
[`docs/research/FIRMWARE-REVERSE-ENGINEERING.md`](../docs/research/FIRMWARE-REVERSE-ENGINEERING.md)。

## 本地复现

`tools/ota_list_partitions.py` 需要一个提供 `payload_dumper.update_metadata_pb2` 的
payload-dumper Python 包。`tools/ext4_walk.py` 和 `tools/ext4_getfile.py` 需要 `ext4`
Python 包。这些是研究辅助工具，因此没有加入 SDK 的运行时依赖。

```powershell
.\.venv\Scripts\python.exe tools\ota_list_partitions.py C:\path\to\payload.bin
.\.venv\Scripts\python.exe tools\ext4_walk.py C:\path\to\system.img system-filetree.txt
.\.venv\Scripts\python.exe tools\ext4_getfile.py C:\path\to\system.img /system/build.prop build.prop
```
