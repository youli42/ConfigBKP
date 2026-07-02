# WinConfigBKP — Agent 指南

## 项目概要

Windows 配置文件备份工具。PySide6 GUI，QThreadPool 异步执行备份/恢复。

- **语言**: Python 3.10+
- **包管理**: `uv venv && uv pip install -r requirements.txt`
- **入口**: `main.py` — argparse 解析参数，非管理员自动 UAC 提权
- **默认分支**: `master`

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

### 数据格式变更必须追查所有消费端

`resolve_path_for_platform()` 返回的 `paths` 可以是 `list[str]` 或 `list[dict]`（含 `{"path": ..., "desc": ...}` 两种格式）。

**修改前必须 grep 所有调用者**：
```powershell
rg "resolve_path_for_platform"
rg "collect_files"
rg "\.get\("paths""
```

典型错误链路：改 `config/builtin/*.jsonc` 的 paths 结构 → 忘了改 `collect_files` → 备份永远收集不到文件。

### 主线程禁止文件 I/O

GUI 线程（Qt 事件循环）中做任何文件扫描、递归遍历、网络路径解析都会冻住窗口。**所有磁盘操作必须放入 QRunnable 后台线程。**

```python
# ❌ 在 _backup() 中直接调用 collect_files()
# ✅ 放入 BatchBackupWorker._collect_files_for_config()（QThreadPool 后台线程）
```

### 修复 bug 时检查同类的所有调用点

```powershell
# 修复 A 存储后端 → 检查 B 存储后端有无相同问题
# 修复 GUI 路径 → 检查 CLI 路径（src/cli.py）是否须同步
```

### 数据模型变更清单

修改 `config/builtin/*.jsonc` 的 schema 后，逐项检查：

- [ ] `resolve_path_for_platform()` 能正确解析新格式
- [ ] `_collect_files_for_config()`（在 `BatchBackupWorker` 内）能遍历新格式路径
- [ ] `restore_engine.py:_resolve_target_paths()` 匹配目标路径正常
- [ ] `config_wizard.py` 序列化/反序列化正常
- [ ] 内置规则的 `paths` / `data_paths` 格式一致

## 国际化（i18n）规则

所有**用户可见**的字符串必须用 `tr()` 包裹。`logger.debug()` 日志不翻译。

```python
from src.utils.i18n import tr, on_locale_changed, off_locale_changed

# ✅ 正确
self.label.setText(tr("发现 {} 个文件").format(count))
QMessageBox.warning(self, tr("提示"), tr("请先选择要备份的配置"))
self.signals.message.emit(tr("正在读取备份文件..."))

# ❌ 错误 - f-string 在 tr() 外
self.label.setText(f"发现 {count} 个文件")
```

### 热切换生命周期

每个需要即时刷新的 GUI 组件必须实现：

```python
class MyWidget(QWidget):
    def __init__(self):
        self._setup_ui()
        self.retranslate_ui()
        self._retranslate_cb = self.retranslate_ui
        on_locale_changed(self._retranslate_cb)
        self.destroyed.connect(self._on_destroy)

    def retranslate_ui(self):
        """在构造和语言切换时调用。"""
        self.scan_btn.setText(tr("扫描本机已装软件"))
        idx = self.combo.currentIndex()
        self.combo.clear()
        self.combo.addItems([tr("本地目录"), tr("ZIP 打包")])
        if 0 <= idx < self.combo.count():
            self.combo.setCurrentIndex(idx)

    def _on_destroy(self):
        off_locale_changed(self._retranslate_cb)
```

### 翻译文件

- `lang/zh_CN.ts` — 源语言（中文），`<translation>` 留空即可
- `lang/en_US.ts` — 英文翻译，通过 `fill_translations.py` 维护
- `lang/extract_strings.py` — 从源代码 `tr()` 调用提取字符串，重新生成 `.ts`
- `lang/fill_translations.py` — 中文→英文翻译字典，填充 `en_US.ts` 并编译 `.qm`
- 运行时通过 `src/utils/i18n.py` 加载 `lang/<locale>.qm`
- 语言选择通过 `QSettings("language")` 持久化

添加新语言：创建 `.ts` 文件 → 设置页 ComboBox 添加选项 → 编译 `.qm`。

## 架构要点

| 层 | 目录 | 职责 |
|---|---|---|
| 入口 | `main.py` | UAC 提权 → 加载 QSettings locale → `install_locale()` → GUI 或 CLI |
| CLI | `src/cli.py` | `run_silent_backup()` — 无 GUI 批量备份 |
| GUI | `src/gui/` | 3-Tab 主窗口（home / config / settings）+ 4 步配置向导 |
| 核心 | `src/core/` | backup_engine / restore_engine / config_parser / manifest_manager / scanner |
| 存储 | `src/storage/` | base（抽象接口）→ local（目录版） / zip_storage（ZIP 版） |
| 工具 | `src/utils/` | 路径解析、环境变量展开、SHA256 哈希、i18n、文件锁检测 |

### 异步模型

`QRunnable` + `QThreadPool`:
- **`BatchBackupWorker`** — 接收 `configs: list[dict]`，内部调用 `_collect_files_for_config()` 收集文件，增量备份并写入存储
- **`RestoreWorker`** — 四阶段：读备份 → `_resolve_target_paths()` 解析目标 → 检测文件占用 → 恢复（恢复前备份当前文件到 tempdir）
- 通过 `BackupSignals` / `RestoreSignals`（QObject + Signal）与 UI 通信
- 信号对象必须存储在 `self` 实例属性上，防止 GC 回收导致信号丢失

### 存储后端

- **LocalStorage** (`src/storage/local.py`): `backups/<config名称>/<backup_id>/` 目录结构，每版本含 `.metadata.json`
- **ZipStorage** (`src/storage/zip_storage.py`): `archive_dir/<config名称>/<backup_id>.zip`，含 `_safe_extract()` 防路径遍历

### 增量备份

`manifest_manager.py` 在每个配置的 manifest 目录下维护 `manifest.json`，记录每个文件的 SHA256 哈希 + 最后备份 ID。`compute_changes()` 对比当前文件哈希，只备份变化的文件。

## 配置规则

JSONC 格式（`json5` 库解析）：

- 内置规则: `config/builtin/*.jsonc`（6 条: VS Code, PowerShell, Git, Windows Terminal, Oh My Posh, Everything）
- 用户规则: `config/user/*.jsonc`（已 gitignore）

关键字段：
- `paths` / `data_paths` — 支持 `list[str]` 或按平台的 `dict` 格式
- `backup_scope` — `{"config": true, "data": false}`，控制是否收集 data 路径
- `strategy.type` — `"incremental"` | `"full"`
- `strategy.max_versions` — 版本上限，超限自动裁剪旧版本
- `strategy.ignore_patterns` — glob 模式过滤文件
- `parser_fields` — `{"editor.fontSize": "字号"}` 点号路径提取 JSON 字段，生成备份摘要

## 命名与 ID 约定

- `backup_id`: `YYYYMMDD-HHMMSS-nanoseconds`（纳秒防冲突，如 `20260630-120000-123456789`）
- `session_id`: `session_YYYYMMDD-HHMMSS-微秒`，同一次批量备份共享一个 session

## 恢复的安全机制

1. **路径遍历保护**: `_resolve_target_paths()` 检查 `dst.resolve()` 是否在 `restore_dir` 下
2. **文件占用检测**: `file_locker.py` 先尝试以 `ab` 模式打开目标文件，若被占用则拒绝恢复
3. **MoveFileExW 重启替换**: 被锁文件支持注册系统重启时替换
4. **恢复前备份**: 将当前文件 cp 到 tempdir，恢复失败可人工回滚

## 调试

```powershell
$env:WINCONFIGBKP_DEBUG=1
python main.py
```

日志输出到 stderr，格式 `[LEVEL] message`，DEBUG 级别包含详细文件哈希、版本裁剪、异常堆栈。

## 打包

`build.ps1` → PyInstaller `--onedir --windowed`，自动复制 `config/` 和 `lang/` 到 exe 目录实现便携。spec 文件 `WinConfigBKP-1.5.0.spec` 可手动调参。

## 补充文档

- `doc/README.md` — 文档索引
- `doc/代码文档/` — 各模块详细说明
- `doc/i18n/多语言贡献方法.md` — i18n 翻译贡献指南
- `todo/` — 开发计划与历史记录
