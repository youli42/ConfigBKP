# 07-models — 数据模型

## 存储数据类（src/storage/base.py）

### BackupResult

| 字段 | 类型 | 说明 |
|------|------|------|
| `backup_id` | `str` | 备份版本标识，格式 `YYYYmmDD-HHMMSS`（基于 UTC） |
| `config_name` | `str` | 对应配置规则的 `name` 字段 |
| `files_count` | `int` | 本次备份的文件数量 |
| `total_size` | `int` | 本次备份文件的总字节数 |
| `note` | `str` | 用户填写或传入的备注文本，默认空字符串 |

### RestoreResult

| 字段 | 类型 | 说明 |
|------|------|------|
| `config_name` | `str` | 对应配置规则的 `name` 字段 |
| `files_restored` | `list[Path]` | 成功恢复的目标文件路径列表 |
| `files_pending` | `list[Path]` | 待恢复的文件路径列表（当前代码始终返回空列表） |

### BackupVersion

| 字段 | 类型 | 说明 |
|------|------|------|
| `backup_id` | `str` | 备份版本标识 |
| `config_name` | `str` | 对应配置规则的 `name` 字段 |
| `timestamp` | `str` | ISO 8601 格式的时间戳（UTC） |
| `note` | `str` | 该版本的备注 |
| `description` | `str` | 自动生成的备份内容描述 |

---

## 信号类

### BackupSignals（src/core/backup_engine.py）

继承自 `QObject`，在 QThread 线程中发射。

| 信号 | 参数 | 发射时机 |
|------|------|----------|
| `progress` | `int` | 备份进度百分比 |
| `message` | `str` | 当前步骤文字 |
| `done` | `object` (BackupResult) | 备份完成 |
| `error` | `str` | 备份出错 |

### RestoreSignals（src/core/restore_engine.py）

继承自 `QObject`，在 QThread 线程中发射。

| 信号 | 参数 | 发射时机 |
|------|------|----------|
| `progress` | `int` | 恢复进度百分比 |
| `message` | `str` | 当前步骤文字 |
| `done` | `object` (RestoreResult) | 恢复完成 |
| `error` | `str` | 恢复出错 |
| `file_blocked` | `str, list` | 文件被锁时，消息文本 + 推测的进程名列表 |

---

## StorageBackend 接口（src/storage/base.py）

抽象基类，定义了 5 个抽象方法。`LocalStorage` 和 `ZipStorage` 分别实现。

| 方法 | 参数 | 返回值 |
|------|------|--------|
| `save` | `backup_id: str, config_name: str, files: dict[str, Path], note: str, description: str` | `BackupResult` |
| `list_versions` | `config_name: str` | `list[BackupVersion]` |
| `restore` | `config_name: str, backup_id: str, target_dir: Optional[Path] = None` | `RestoreResult` |
| `get_files` | `config_name: str, backup_id: str` | `dict[str, Path]` |
| `delete_version` | `config_name: str, backup_id: str` | `bool` |
