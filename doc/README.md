# WinConfigBKP 文档

Windows 配置文件备份工具。使用 PySide6 搭建 GUI，QThreadPool 异步执行备份/恢复。

## 代码文档（开发者）

| 文档 | 内容 |
|------|------|
| `代码文档/01-程序入口与权限.md` | main.py：UAC 提权 + 启动逻辑 + logging 配置 |
| `代码文档/02-核心逻辑层.md` | config_parser / backup_engine / restore_engine / manifest_manager / scanner |
| `代码文档/03-存储后端.md` | base / local / zip_storage |
| `代码文档/04-界面层.md` | main_window / home_tab / config_tab / config_wizard / settings_tab |
| `代码文档/05-工具层.md` | app_path / path_expander / file_hasher / time_util / file_locker |
| `代码文档/07-数据模型.md` | BackupResult / RestoreResult / BackupVersion / BackupSummary / 信号类 |

## 使用文档（用户）

| 文档 | 内容 |
|------|------|
| `使用文档/06-配置文件格式与书写指南.md` | JSONC 格式说明 + 手把手教你写配置规则 |
| `使用文档/08-调试模式使用指南.md` | 环境变量设置 / 日志场景 / 排查方法 |

## 模块概览

| 文件 | 核心职责 | 外部依赖（非标准库） |
|------|----------|----------------------|
| `main.py` | UAC 权限检测与提权；启动 QApplication 主循环 | PySide6 |
| `src/core/config_parser.py` | 解析 `.jsonc` 配置文件；按点号路径提取字段值；按平台过滤规则 | json5 |
| `src/core/backup_engine.py` | 通过 QRunnable 在后台线程执行增量备份，通过 Signals 更新 UI | PySide6 |
| `src/core/restore_engine.py` | 通过 QRunnable 在后台线程执行恢复，含文件占用检测与反馈 | PySide6 |
| `src/core/manifest_manager.py` | 读写 `manifest.json` 记录 SHA256 哈希，对比判定增量变化 | — |
| `src/core/scanner.py` | 展开环境变量路径检测文件是否存在，模糊匹配目录名识别已装软件 | — |
| `src/storage/base.py` | 定义 StorageBackend 抽象基类；数据模型 BackupResult / RestoreResult / BackupVersion | — |
| `src/storage/local.py` | 本地目录版存储，按 config 名称 + 版本 ID 分层组织 | — |
| `src/storage/zip_storage.py` | ZIP 压缩包版存储，每次备份输出一个 .zip 文件 | — |
| `src/gui/main_window.py` | 3-Tab QTabWidget 主窗口，组装各 Tab 并切换时刷新数据 | PySide6 |
| `src/gui/home_tab.py` | 软件勾选列表 + 备份/恢复按钮 + 进度条 + 历史记录表 | PySide6 |
| `src/gui/config_tab.py` | JSONC 源码编辑器 + 向导式配置，双模式 Tab 切换 | PySide6, json5 |
| `src/gui/config_wizard.py` | 4 步向导表单（基本信息/源路径/解析字段/备份策略） | PySide6 |
| `src/gui/settings_tab.py` | 定时备份注册/卸载 + 版本策略配置 + 关于信息 | PySide6 |
| `src/utils/app_path.py` | 根据打包/源码状态返回 exe 同目录或项目根目录 | — |
| `src/utils/path_expander.py` | 替换字符串中的 `%xxx%` 为环境变量值，返回 Path | — |
| `src/utils/file_hasher.py` | 计算文件 SHA256 哈希与文件元信息 | — |
| `src/utils/time_util.py` | 将 UTC 时间戳转换为本地时间，用于 UI 展示 | — |
| `src/utils/file_locker.py` | 检测文件写入锁；调用 MoveFileExW 注册重启时替换 | — |
| `config/builtin/*.jsonc` | 6 条内置备份规则，定义备份路径与策略 | json5 |
| `build.ps1` | PowerShell 打包脚本，PyInstaller `--onedir` 输出便携版 | PyInstaller |

## 非代码文件

| 文件 | 说明 |
|------|------|
| `src/*/__init__.py` | 包标记文件，无业务逻辑 |
| `requirements.txt` | 依赖清单：PySide6, json5, watchdog, pyinstaller |
| `pyproject.toml` | uv/pip 项目元数据与依赖声明 |
| `todo/` | 开发计划与过程文档，非运行必需 |
