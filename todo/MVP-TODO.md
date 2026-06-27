# MVP-TODO

## Phase 1：项目骨架与配置规则

- [ ] 1.1 创建完整目录结构（参照架构图）
- [ ] 1.2 创建 `requirements.txt`（PySide6 / json5 / watchdog / pyinstaller）
- [ ] 1.3 创建 `main.py` 骨架（UAC 权限检测 + 提权逻辑）
- [ ] 1.4 创建 `src/__init__.py` 及各子包 `__init__.py`
- [ ] 1.5 编写内置配置规则（.jsonc × 5）：
  - [ ] `config/builtin/vscode.jsonc`
  - [ ] `config/builtin/powershell.jsonc`
  - [ ] `config/builtin/git.jsonc`
  - [ ] `config/builtin/windows_terminal.jsonc`
  - [ ] `config/builtin/ohmyposh.jsonc`

## Phase 2：核心解析层

- [ ] 2.1 `utils/path_expander.py` — 展开 `%xxx%` 环境变量 → `pathlib.Path`
- [ ] 2.2 `core/config_parser.py` — `json5.loads` 解析 .jsonc；`functools.reduce` 点号路径取值；按 `platform` 过滤
- [ ] 2.3 `utils/file_hasher.py` — 计算文件 `SHA256` 哈希
- [ ] 2.4 `core/manifest_manager.py` — 读写 `manifest.json`；对比 SHA256 判断增量变化

## Phase 3：存储层与备份引擎

- [ ] 3.1 `storage/base.py` — 抽象接口 `save / list_versions / restore / delete_version`
- [ ] 3.2 `storage/local.py` — 本地目录存储（按版本号组织文件夹）
- [ ] 3.3 `storage/zip_storage.py` — ZIP 打包存储
- [ ] 3.4 `core/backup_engine.py` — QThreadPool + QRunnable + BackupSignals；全量/增量逻辑；调用 ManifestManager + storage

## Phase 4：恢复引擎与文件占用处理

- [ ] 4.1 `utils/file_locker.py` — 检测文件是否被占用（NtCreateFile / try-open）；MoveFileEx + MOVEFILE_DELAY_UNTIL_REBOOT
- [ ] 4.2 `core/restore_engine.py` — 异步恢复；占用检测 → 直接替换 / 提示关闭 / 重启替换；恢复前备份当前文件

## Phase 5：GUI 界面

- [ ] 5.1 `gui/main_window.py` — 3-Tab QTabWidget 主窗口
- [ ] 5.2 `gui/home_tab.py` — 软件勾选列表 + 备注输入 + 目标选择 + 备份/恢复按钮 + 进度条 + 历史记录 QTableWidget
- [ ] 5.3 `gui/config_tab.py` — 规则下拉选择 + QPlainTextEdit JSONC 编辑 + 语法验证 + 保存 + 扫描本机按钮
- [ ] 5.4 `gui/settings_tab.py` — 定时备份开关 + 时间选择 + 版本策略 + 关于信息

## Phase 6：扫描与集成

- [ ] 6.1 `core/scanner.py` — 按 `platform` 过滤规则；展开路径检查是否存在；模糊匹配 `%APPDATA%` / `%ProgramFiles%` 目录名
- [ ] 6.2 整合 scanner.py → config_tab "扫描本机" 按钮
- [ ] 6.3 整合 backup_engine + restore_engine → home_tab 按钮回调
- [ ] 6.4 整合 manifest_manager → home_tab 历史记录展示
- [ ] 6.5 定时任务逻辑：点击开关 → 注册/卸载 Windows 任务计划程序

## Phase 7：打包与测试

- [ ] 7.1 编写 `build.ps1`（PyInstaller 打包脚本）
- [ ] 7.2 基础功能测试：全量备份 → 增量备份 → 恢复 → 文件占用恢复
- [ ] 7.3 边缘情况测试：空目录、权限不足、非法 .jsonc、跨版本恢复
- [ ] 7.4 编写 `README.md` 使用说明

---

## 完成进度

- [ ] Phase 1 完成
- [ ] Phase 2 完成
- [ ] Phase 3 完成
- [ ] Phase 4 完成
- [ ] Phase 5 完成
- [ ] Phase 6 完成
- [ ] Phase 7 完成
