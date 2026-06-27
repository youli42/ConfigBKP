# MVP-TODO

## Phase 1：项目骨架与配置规则

- [x] 1.1 创建完整目录结构（参照架构图）
- [x] 1.2 创建 `requirements.txt`（PySide6 / json5 / watchdog / pyinstaller）
- [x] 1.3 创建 `main.py` 骨架（UAC 权限检测 + 提权逻辑）
- [x] 1.4 创建 `src/__init__.py` 及各子包 `__init__.py`
- [x] 1.5 编写内置配置规则（.jsonc × 6）：
  - [x] `config/builtin/vscode.jsonc`
  - [x] `config/builtin/powershell.jsonc`
  - [x] `config/builtin/git.jsonc`
  - [x] `config/builtin/windows_terminal.jsonc`
  - [x] `config/builtin/ohmyposh.jsonc`
  - [x] `config/builtin/everything.jsonc`

## Phase 2：核心解析层

- [x] 2.1 `utils/path_expander.py` — 展开 `%xxx%` 环境变量 → `pathlib.Path`
- [x] 2.2 `core/config_parser.py` — `json5.loads` 解析 .jsonc；`functools.reduce` 点号路径取值；按 `platform` 过滤
- [x] 2.3 `utils/file_hasher.py` — 计算文件 `SHA256` 哈希
- [x] 2.4 `core/manifest_manager.py` — 读写 `manifest.json`；对比 SHA256 判断增量变化

## Phase 3：存储层与备份引擎

- [x] 3.1 `storage/base.py` — 抽象接口 `save / list_versions / restore / delete_version`
- [x] 3.2 `storage/local.py` — 本地目录存储（按版本号组织文件夹）
- [x] 3.3 `storage/zip_storage.py` — ZIP 打包存储
- [x] 3.4 `core/backup_engine.py` — QThreadPool + QRunnable + BackupSignals；全量/增量逻辑；调用 ManifestManager + storage

## Phase 4：恢复引擎与文件占用处理

- [x] 4.1 `utils/file_locker.py` — 检测文件是否被占用（NtCreateFile / try-open）；MoveFileEx + MOVEFILE_DELAY_UNTIL_REBOOT
- [x] 4.2 `core/restore_engine.py` — 异步恢复；占用检测 → 直接替换 / 提示关闭 / 重启替换；恢复前备份当前文件

## Phase 5：GUI 界面

- [x] 5.1 `gui/main_window.py` — 3-Tab QTabWidget 主窗口
- [x] 5.2 `gui/home_tab.py` — 软件勾选列表 + 备注输入 + 目标选择 + 备份/恢复按钮 + 进度条 + 历史记录 QTableWidget
- [x] 5.3 `gui/config_tab.py` — 规则下拉选择 + QPlainTextEdit JSONC 编辑 + 语法验证 + 保存 + 扫描本机按钮
- [x] 5.4 `gui/settings_tab.py` — 定时备份开关 + 时间选择 + 版本策略 + 关于信息

## Phase 6：扫描与集成

- [x] 6.1 `core/scanner.py` — 按 `platform` 过滤规则；展开路径检查是否存在；模糊匹配 `%APPDATA%` / `%ProgramFiles%` 目录名
- [x] 6.2 整合 scanner.py → config_tab "扫描本机" 按钮
- [x] 6.3 整合 backup_engine + restore_engine → home_tab 按钮回调
- [x] 6.4 整合 manifest_manager → home_tab 历史记录展示
- [x] 6.5 定时任务逻辑：点击开关 → 注册/卸载 Windows 任务计划程序

## Phase 7：打包与测试

- [x] 7.1 编写 `build.ps1`（PyInstaller 打包脚本）
- [x] 7.2 更新 `build.ps1`：`--onefile` → `--onedir` + 后处理复制 config
- [x] 7.3 编写 `README.md` 使用说明
- [x] 7.4 安装依赖并验证导入（venv + PySide6 + json5 + watchdog）
- [x] 7.5 基础功能测试：config_parser / manifest_manager / path_expander / scanner

## Phase 8：便携式架构重构

- [x] 8.1 新增 `src/utils/app_path.py` — 统一管理所有路径（打包/源码自动适配）
  - `get_app_root()` → exe 所在目录 / 源码根目录
  - `get_config_dir()` → `{app_root}/config/`
  - `get_backup_dir()` → `{app_root}/backups/`
- [x] 8.2 `main_window.py` — 改用 `app_path`，移除内置/用户双目录
- [x] 8.3 `config_tab.py` — 移除内置/用户标签、移除「禁止删除内置」、移除「复制到用户」按钮
- [x] 8.4 `home_tab.py` — 双目录 → 单目录
- [x] 8.5 `scanner.py` — 无需修改（接口已是 list[Path]）
- [x] 8.6 `build.ps1` — `--onefile` → `--onedir` + post-build 复制 `config/` 到输出目录

## Phase 9：收尾

- [x] 9.1 所有模块语法检查 + 导入测试（9 项全部通过）
- [x] 9.2 功能验证：app_path / config_parser / filter_by_platform / scanner / storage / manifest_manager / backup_engine / utils / GUI imports

---

## Phase 10：备份历史双栏 + 规则管理双栏

### 概述

两个 UI 重设计：
1. **备份历史**：单表 → 左（session 记录）+ 右（session 内 config 详情 + 恢复按钮）
2. **规则管理**：下拉框 + 编辑器 → 左（文件列表）+ 右（编辑器）

通过 `session_id` 字段实现批次分组。该字段独立于 `backup_id`，在 `BatchBackupWorker.run()` 开始处生成，所有同批 config 共享。

### 涉及的数据类变更

```
新增 BackupSession:
  session_id: str, timestamp: str, note: str,
  config_names: list[str], total_count: int

BackupResult 新增字段: session_id: str
StorageBackend.save() 新增参数: session_id: str
StorageBackend 新增抽象方法: list_sessions() → list[BackupSession]
```

### Step 1：`storage/base.py`

- [ ] 1.1 新增 `BackupSession` 数据类（session_id, timestamp, note, config_names, total_count）
- [ ] 1.2 `BackupResult.__init__` 新增 `session_id: str = ""` 参数
- [ ] 1.3 `StorageBackend.save()` 新增 `session_id: str` 参数
- [ ] 1.4 `StorageBackend` 新增抽象方法 `list_sessions() → list[BackupSession]`

### Step 2：`storage/local.py`

- [ ] 2.1 `save()` 将 `session_id` 写入 `.metadata.json`
- [ ] 2.2 `list_sessions()` 遍历所有 config 的版本，聚合相同 session_id（含兼容旧备份：无 session_id 时回退为 backup_id）

### Step 3：`storage/zip_storage.py`

- [ ] 3.1 `save()` 将 `session_id` 写入 zip 内 `.metadata.json`
- [ ] 3.2 `list_sessions()` 同 local.py 逻辑对齐

### Step 4：`core/backup_engine.py`

- [ ] 4.1 `BackupSummary.__init__` 新增 `session_id: str = ""`
- [ ] 4.2 `BatchBackupWorker.run()` 开始在循环外生成 `session_id = "session_" + datetime.now().strftime("%Y%m%d-%H%M%S")`
- [ ] 4.3 `storage.save()` 调用传参 `session_id=self.session_id`

### Step 5：`gui/home_tab.py` — 备份历史双栏

- [ ] 5.1 底部 QGroupBox 内替换为 QSplitter（水平）
  - 左栏: QTableWidget（列: 时间, 备注, 配置数）
  - 右栏: QTableWidget（列: 配置名, 状态, 文件数）+ "恢复此批次" 按钮
- [ ] 5.2 新增 `_refresh_sessions()` 调用 `storage.list_sessions()` 填充左栏
- [ ] 5.3 新增 `_on_session_selected(row)` 按 session_id 过滤版本填充右栏
- [ ] 5.4 "恢复此批次" 按钮回调：遍历右栏 configs 逐个执行 RestoreWorker
- [ ] 5.5 `_batch_backup_done()` 改为调用 `_refresh_sessions()`
- [ ] 5.6 `refresh_configs()` 改为调用 `_refresh_sessions()`
- [ ] 5.7 移除旧的 `_refresh_history()` 和 QTableWidget 单表
- [ ] 5.8 移除 restore 方法中的历史行依赖（改从右栏 session 获取）

### Step 6：`gui/config_tab.py` — 规则管理双栏

- [ ] 6.1 `_setup_ui()` 替换为 QSplitter（水平）
  - 左栏: QListWidget（显示规则名，itemData 存文件路径）
  - 右栏: QPlainTextEdit + 底部按钮行
- [ ] 6.2 `refresh_rules()` 改为填充 QListWidget（保留 builtin/user 顺序）
- [ ] 6.3 替换 `_on_rule_selected` 为列表选中事件 `_on_list_selected`
- [ ] 6.4 移除 QComboBox 及相关代码
- [ ] 6.5 新建/删除后调用 `refresh_rules()` 并高亮对应项

### Step 7：验证 + doc

- [ ] 7.1 语法检查 + import 验证
- [ ] 7.2 全量/增量备份测试 → session 分组正常
- [ ] 7.3 恢复批次测试 → 逐个配置恢复
- [ ] 7.4 旧备份兼容测试（无 session_id → 回退 backup_id）
- [ ] 7.5 双栏 UI 交互测试（列表选中/右键/恢复按钮）
- [ ] 7.6 更新 `doc/04-界面层.md`、`doc/07-数据模型.md`、`doc/03-存储后端.md`

---

## 完成进度

- [x] Phase 1 完成
- [x] Phase 2 完成
- [x] Phase 3 完成
- [x] Phase 4 完成
- [x] Phase 5 完成
- [x] Phase 6 完成
- [x] Phase 7 完成
- [x] Phase 8 完成
- [x] Phase 9 完成
- [ ] Phase 10 进行中
