# 03-storage — 存储后端

## base.py

文件职责：定义存储后端抽象基类 `StorageBackend` 和三个数据模型 `BackupResult` / `RestoreResult` / `BackupVersion`。

### StorageBackend（抽象基类）

| 方法 | 参数 | 返回值 | 核心作用 |
|------|------|--------|----------|
| `save` | `backup_id: str`, `config_name: str`, `files: dict[str, Path]`, `note: str`, `description: str` | `BackupResult` | 写入备份文件与元数据 |
| `list_versions` | `config_name: str` | `list[BackupVersion]` | 列出某配置所有历史备份版本 |
| `restore` | `config_name: str`, `backup_id: str`, `target_dir: Optional[Path] = None` | `RestoreResult` | 将指定版本的文件恢复到目标路径 |
| `get_files` | `config_name: str`, `backup_id: str` | `dict[str, Path]` | 获取指定备份版本的文件字典（相对路径 → 临时文件路径） |
| `delete_version` | `config_name: str`, `backup_id: str` | `bool` | 删除指定版本，返回是否成功 |

### 数据模型

| 类 | 构造参数 | 字段 |
|----|----------|------|
| `BackupResult` | `backup_id`, `config_name`, `files_count`, `total_size`, `note` | 同上 |
| `RestoreResult` | `config_name`, `files_restored: list[Path]`, `files_pending: list[Path]` | 同上 |
| `BackupVersion` | `backup_id`, `config_name`, `timestamp`, `note`, `description` | 同上 |

### 特别说明

- ⚠️ **数据模型类已在 07-models.md 中单独展开**，本文只列出基类接口签名。
- `LocalStorage` 和 `ZipStorage` 都继承自 `StorageBackend(ABC)`。

---

## local.py

文件职责：`StorageBackend` 的本地目录实现。备份文件按 `{base_dir}/{config_name}/{backup_id}/` 目录组织，元数据存放于 `{version_dir}/.metadata.json`。

### 公开接口

| 方法 | 参数 | 返回值 | 核心作用 | 关键副作用 |
|------|------|--------|----------|------------|
| `__init__` | `base_dir: Path` | — | 设置存储根目录 | — |
| `save` | 同 base.py | `BackupResult` | 拷贝文件到版本目录，写入 `.metadata.json` | 自动创建目录 |
| `list_versions` | 同 base.py | `list[BackupVersion]` | 遍历 `{base_dir}/{name}/` 下子目录，解析 `.metadata.json` 返回版本列表 | 无子目录或元数据缺失时跳过 |
| `restore` | 同 base.py | `RestoreResult` | 将版本目录中除 `.metadata.json` 外的文件复制到目标路径 | `FileNotFoundError` 版本不存在 |
| `get_files` | 同 base.py | `dict[str, Path]` | 递归遍历版本目录，返回所有非 `.metadata.json` 文件的相对路径 → 绝对路径映射 | — |
| `delete_version` | 同 base.py | `bool` | `shutil.rmtree` 删除版本目录 | — |

---

## zip_storage.py

文件职责：`StorageBackend` 的 ZIP 压缩包实现。每次备份输出一个 `{archive_dir}/{config_name}/{backup_id}.zip`，元数据内嵌于 zip 中的 `.metadata.json`。

### 公开接口

| 方法 | 参数 | 返回值 | 核心作用 | 关键副作用 |
|------|------|--------|----------|------------|
| `__init__` | `archive_dir: Path` | — | 设置存档根目录，`_temp_dir` 初始为 None | — |
| `save` | 同 base.py | `BackupResult` | 将文件写入 zip（`ZIP_DEFLATED`），内嵌 `.metadata.json` | 自动创建父目录 |
| `list_versions` | 同 base.py | `list[BackupVersion]` | 扫描 `{name}/` 下的 `.zip` 文件，读取内部 `.metadata.json` | — |
| `restore` | 同 base.py | `RestoreResult` | 解压到临时目录，复制到目标路径，然后清理临时目录 | 临时文件在 `%TEMP%/winbkp_*` |
| `get_files` | 同 base.py | `dict[str, Path]` | 解压到临时目录，返回文件字典 | — |
| `delete_version` | 同 base.py | `bool` | 删除对应的 .zip 文件 | — |
| `cleanup` | 无 | `None` | 删除 `_temp_dir` 临时目录 | — |

### 特别说明

- `_ensure_temp()` 使用 `tempfile.mkdtemp(prefix="winbkp_")` 创建临时目录，生命周期长于单次操作，需手动调用 `cleanup()` 释放。
- `restore` 方法在复制完成后自动 `shutil.rmtree(extract_dir, ignore_errors=True)`。
