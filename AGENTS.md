# WinConfigBKP — Agent 指南

## 项目概要

Windows 配置文件备份工具。PySide6 GUI，QThreadPool 异步执行备份/恢复。

- **语言**: Python 3.10+
- **包管理**: `uv venv && uv pip install -r requirements.txt`
- **入口**: `main.py` — argparse 解析参数，非管理员自动 UAC 提权
- **默认分支**: `master`（另有 `feature/i18n` 分支）

## 关键命令

```powershell
# 安装依赖（必须先用 uv venv 创建虚拟环境）
uv venv && uv pip install --python .\.venv\Scripts\python.exe -r requirements.txt

# 运行（首次会弹 UAC）
.\.venv\Scripts\activate && python main.py

# 静默备份（无 GUI，需管理员）
python main.py --silent-backup

# 打包为便携 exe
.\.venv\Scripts\activate && .\build.ps1
```

> ⚠️ 项目**没有** lint / format / type-check 配置，也没有测试框架或 CI。所有改动需人工验证。

## 开发规则（反重复踩坑）

这些规则源于历史 bug 总结。违反它们几乎必然引入同类问题。

### 数据格式变更必须追查所有消费端

`src/core/config_parser.py` 中的 `resolve_path_for_platform()` 返回的 `paths` 可以是 `list[str]` 或 `list[dict]`（含 `{"path": ..., "desc": ...}` 两种格式）。

**修改前必须 grep 所有调用者并确认兼容**：
```powershell
# 确认所有消费端处理了 dict 和 str 两种格式
rg "resolve_path_for_platform"
rg "collect_files"
rg "\.get\("paths""  # 直接读 cfg["paths"] 的地方
```

典型错误链路：改 `config/builtin/*.jsonc` 的 paths 结构 → 忘了改 `collect_files` → 备份永远收集不到文件。

### 类型标注必须诚实

Python 的类型提示不强制检查，但写错会误导后续开发者：
```python
# ❌ 标注 list[str] 实际返回 list[dict]
def resolve_path_for_platform(...) -> list[str]:
    return [{"path": "...", "desc": "..."}, ...]

# ✅ 标注实际返回类型
def resolve_path_for_platform(...) -> list:
```

不自洽的类型标注是未来 bug 的种子。

### 主线程禁止文件 I/O

GUI 线程（Qt 事件循环）中做任何文件扫描、递归遍历、网络路径解析都会冻住窗口。

```python
# ❌ 在 _backup() 中直接调用 collect_files()
files = collect_files(paths)

# ✅ 放入 BatchBackupWorker.run()（QThreadPool 后台线程）
# 或使用 QThreadPool 启动专门的 PrepareWorker
```

修改 GUI 代码前先确认：这段逻辑会不会读写磁盘或网络？如果会，必须放进 QRunnable。

### 修复 bug 时检查同类的所有调用点

找到一个 bug 后，`rg` 搜索同一模式的全部调用：

- 修复 `collect_files` 后 → 检查 `cli.py`、`home_tab.py`、`restore_engine.py` 是否同步用对
- 修复 A 存储后端 → 检查 B 存储后端有无相同问题
- 修复 GUI 路径 → 检查 CLI 路径（`src/cli.py`）是否须同步

### 数据模型变更清单

修改 `config/builtin/*.jsonc` 的 schema 后，逐项检查：

- [ ] `resolve_path_for_platform()` 能正确解析新格式
- [ ] `collect_files()` 能遍历新格式路径
- [ ] `home_tab.py:_backup()` / `cli.py:run_silent_backup()` 收集文件正常
- [ ] `restore_engine.py:_resolve_target_paths()` 匹配目标路径正常
- [ ] `config_wizard.py` 序列化/反序列化正常
- [ ] 内置规则的 `paths` / `data_paths` 格式一致

## 架构要点

| 层 | 目录 | 职责 |
|---|---|---|
| 入口 | `main.py` | UAC 提权 → GUI 或 CLI |
| CLI | `src/cli.py` | `run_silent_backup()` — 无 GUI 批量备份 |
| GUI | `src/gui/` | 3-Tab 主窗口（home / config / settings）+ 5 步配置向导 |
| 核心 | `src/core/` | backup_engine / restore_engine / config_parser / manifest_manager / scanner |
| 存储 | `src/storage/` | base（抽象接口）→ local（目录版） / zip_storage（ZIP 版） |
| 工具 | `src/utils/` | 路径解析、环境变量展开、SHA256 哈希、文件锁检测 |

### 异步模型

`QRunnable` + `QThreadPool`:
- `BackupWorker` / `BatchBackupWorker` — 增量备份
- `RestoreWorker` — 三步：读备份 → 检测文件占用 → 恢复（恢复前先备份当前文件到 tempdir 以便回滚）
- 通过 `BackupSignals` / `RestoreSignals`（QObject + Signal）与 UI 通信

### 存储后端

- **LocalStorage** (`src/storage/local.py`): `backups/<config名称>/<backup_id>/` 目录结构，每个版本内含 `.metadata.json`
- **ZipStorage** (`src/storage/zip_storage.py`): `archive_dir/<config名称>/<backup_id>.zip`，含 `_safe_extract()` 防路径遍历

### 增量备份机制

`manifest_manager.py` 在每个配置的 manifest 目录下维护 `manifest.json`，记录每个文件的 SHA256 哈希 + 最后备份 ID。`compute_changes()` 对比当前文件哈希，只备份变化的文件。

## 配置规则

JSONC 格式（`json5` 库解析），存放路径：

- 内置规则: `config/builtin/*.jsonc`（6 条: VS Code, PowerShell, Git, Windows Terminal, Oh My Posh, Everything）
- 用户规则: `config/user/*.jsonc`（已 gitignore）

关键字段：
- `paths` / `data_paths` — 支持 `list[str]` 或按平台的 `dict` 格式（`{"windows": [...], "linux": [...], "default": [...]}`）
- `backup_scope` — `{"config": true, "data": false}`，控制 CLI 模式下是否收集 data 路径
- `strategy.type` — `"incremental"` | `"full"`
- `strategy.max_versions` — 版本上限，超限自动裁剪旧版本
- `strategy.ignore_patterns` — glob 模式过滤文件
- `parser_fields` — `{"editor.fontSize": "字号"}` 点号路径提取 JSON 字段，生成备份摘要

> 需要添加新软件的备份规则 → 在 `config/user/` 创建 `.jsonc` 文件即可，无需改代码。

## 配置文件路径

- `%xxx%` 环境变量展开 → `src/utils/path_expander.py`
- 便携式打包后 `config/` 和 `backups/` 目录跟随 exe 位置 → `src/utils/app_path.py`

## 调试

```powershell
$env:WINCONFIGBKP_DEBUG=1
python main.py
```

日志输出到 stderr，格式 `[LEVEL] message`，DEBUG 级别包含详细文件哈希、版本裁剪、异常堆栈。

## 命名与 ID 约定

- `backup_id`: `YYYYMMDD-HHMMSS-nanoseconds`（纳秒防冲突，如 `20260630-120000-123456789`）
- `session_id`: `session_YYYYMMDD-HHMMSS-微秒`，同一次批量备份共享一个 session，用于按会话聚合展示历史

## 恢复的安全机制

1. **路径遍历保护**: `restore_engine.py` 检查 `dst.resolve()` 是否在 `restore_dir` 下
2. **文件占用检测**: `file_locker.py` 先尝试以 `ab` 模式打开目标文件，若被占用则拒绝恢复
3. **MoveFileExW 重启替换**: 被锁文件支持注册系统重启时替换（`MOVEFILE_DELAY_UNTIL_REBOOT`）
4. **恢复前备份**: 将当前文件先 cp 到 tempdir，恢复失败可人工回滚

## 打包

`build.ps1` → PyInstaller `--onedir --windowed`，自动复制 `config/` 到 exe 目录实现便携。spec 文件 `WinConfigBKP-1.0.0.spec` 可手动调参。

## 补充文档

- `doc/README.md` — 文档索引（代码文档 + 使用文档）
- `doc/代码文档/` — 各模块详细说明
- `doc/使用文档/` — JSONC 配置书写指南、调试模式用法
- `todo/` — 开发计划与历史记录
