# WinConfigBKP — Windows 配置文件备份工具

## 项目概述

使用 Python + PySide6 开发的 Windows 配置文件备份 GUI 工具，支持本地目录、ZIP 压缩、远程 FTP/SFTP/WebDAV 多种存储后端，具备差异备份、版本管理、定时任务、自动描述生成等特性。

---

## 1. 架构总览

```
WinConfigBKP/
├── main.py                        # 程序入口
├── requirements.txt               # 依赖清单
├── build.ps1                      # PyInstaller 打包脚本
│
├── config/                        # 预设配置规则（JSON）
│   ├── builtin/                   #   内置常用软件规则
│   │   ├── vscode.json
│   │   ├── powershell.json
│   │   ├── git.json
│   │   ├── windows_terminal.json
│   │   └── ohmyposh.json
│   └── user/                      #   用户自定义规则
│
├── src/
│   ├── gui/                       # PySide6 界面
│   │   ├── __init__.py
│   │   ├── main_window.py         #   主窗口
│   │   ├── backup_tab.py          #   备份面板
│   │   ├── restore_tab.py         #   恢复面板
│   │   ├── config_tab.py          #   配置规则管理面板
│   │   ├── scheduler_tab.py       #   定时任务面板
│   │   └── settings_tab.py        #   设置面板
│   │
│   ├── core/                      # 核心逻辑
│   │   ├── __init__.py
│   │   ├── backup_engine.py       #   备份引擎（全量/增量/差异 + 版本管理）
│   │   ├── restore_engine.py      #   恢复引擎
│   │   ├── config_parser.py       #   JSON 配置规则解析器
│   │   └── description_gen.py     #   自动生成备份描述
│   │
│   ├── storage/                   # 存储后端（策略模式）
│   │   ├── __init__.py
│   │   ├── base.py                #   抽象存储接口
│   │   ├── local.py               #   本地目录存储
│   │   ├── zip_storage.py         #   ZIP 打包存储
│   │   ├── ftp_storage.py         #   FTP 远程存储
│   │   ├── sftp_storage.py        #   SFTP 远程存储
│   │   └── webdav_storage.py      #   WebDAV 远程存储
│   │
│   ├── scheduler/                 # 定时任务
│   │   ├── __init__.py
│   │   └── scheduler.py           #   Windows 任务计划程序集成
│   │
│   └── utils/
│       ├── __init__.py
│       ├── file_hasher.py         #   文件哈希（差异对比）
│       └── path_expander.py       #   环境变量路径展开
│
├── resources/                     # 资源文件
│   ├── icons/
│   └── styles/
│
└── dist/                          # PyInstaller 输出
```

---

## 2. JSON 配置规则设计

### 2.1 配置规则文件格式

```jsonc
{
  "name": "VS Code",                       // 显示名称
  "description": "Visual Studio Code 编辑器配置",
  "version": 1,
  "enabled": true,
  "source": {
    "paths": [                             // 要备份的文件/目录路径（支持 %xxx% 环境变量）
      "%APPDATA%\\Code\\User\\settings.json",
      "%APPDATA%\\Code\\User\\keybindings.json",
      "%APPDATA%\\Code\\User\\snippets\\",
      "%APPDATA%\\Code\\User\\extensions.json"
    ],
    "registry_keys": [],                   // 可选：注册表项
    "env_vars": []                         // 可选：环境变量名
  },
  "parser": {                              // 用于自动生成备份内容摘要
    "type": "json",                        // json | ini | text | regex
    "fields": [                            // 字段路径 + 显示标签
      {"path": "$.extensions.theme",          "label": "主题"},
      {"path": "$.editor.fontSize",           "label": "字号"},
      {"path": "$.editor.fontFamily",         "label": "字体"},
      {"path": "$.files.autoSave",            "label": "自动保存"},
      {"path": "$.workbench.colorTheme",      "label": "颜色主题"}
    ]
  },
  "backup_strategy": {
    "type": "incremental",                 // full | incremental | diff
    "max_versions": 10,                    // 最大保留版本数
    "ignore_patterns": [                   // 忽略模式（glob）
      "*.log",
      "*.tmp",
      "__pycache__/"
    ]
  }
}
```

### 2.2 支持的解析器类型

| 类型 | 说明 | 适用场景 |
|------|------|----------|
| `json` | JSONPath 提取关键字段 | VS Code、Git 等 JSON 格式配置 |
| `ini` | INI 文件节/键解析 | PowerShell 配置文件 |
| `text` | 正则表达式提取 | 自定义文本格式配置 |
| `regex` | 高级正则 + 分组命名 | 复杂的文本配置解析 |

### 2.3 内置配置文件规则计划

1. **VS Code** — settings.json, keybindings.json, snippets, extensions.json
2. **PowerShell** — $PROFILE, 控制台设置
3. **Git** — .gitconfig, .gitignore_global
4. **Windows Terminal** — settings.json
5. **Oh My Posh** — theme JSON
6. **Winget** — 已安装包列表导出

---

## 3. GUI 功能模块

### 3.1 备份面板

- 加载所有配置规则（内置 + 用户自定义）
- 勾选要备份的项，显示每项的配置描述
- 选择备份目标：本地目录 / ZIP / FTP / SFTP / WebDAV
- 添加本次备份备注
- 点击「执行备份」→ 进度条显示 → 完成后展示摘要
- 备份记录以时间线形式展示，包含：时间、内容摘要、备注、大小

### 3.2 恢复面板

- 按时间线或版本号浏览备份历史
- 查看每个备份版本的详细内容（解析后的关键字段对比）
- 选择恢复范围：全部 / 单项
- 恢复选项：覆盖原路径 / 恢复到指定路径
- 恢复前自动创建还原点（备份当前文件到临时目录）

### 3.3 配置规则管理面板

- 列表展示所有配置规则，支持搜索和分类筛选
- 使用 Table 控件显示：名称、路径数、策略类型、启用状态
- 点击编辑进入向导式配置界面：
  - Step 1: 基本信息（名称、描述）
  - Step 2: 添加/删除源路径（支持浏览文件夹选择）
  - Step 3: 配置解析规则（选择类型 + 可视化添加字段）
  - Step 4: 备份策略（类型、版本数、忽略规则）
- 支持 JSON 源码编辑（对高级用户）

### 3.4 定时任务面板

- 创建定时备份任务（一次 / 每日 / 每周 / 自定义 Cron）
- 选择要执行的备份配置集合
- 选择目标存储位置
- 一键注册到 Windows 任务计划程序（`schtasks.exe`）
- 查看已注册的任务列表，支持暂停 / 删除

### 3.5 设置面板

- 默认备份存储路径
- 网络连接配置（FTP/SFTP/WebDAV 连接参数，测试连接按钮）
- 默认版本保留策略
- 日志级别设置
- 开机自启选项

---

## 4. 存储后端

| 后端 | 实现方式 | 依赖 |
|------|----------|------|
| 本地目录 | `shutil.copytree` / `shutil.copy2` | 内置 |
| ZIP 压缩 | `zipfile` 模块 | 内置 |
| FTP | `ftplib` | 内置 |
| SFTP | `paramiko.SFTPClient` | paramiko |
| WebDAV | `webdav4` 库 | webdav4 |

所有存储后端实现统一接口（策略模式）：

```python
class StorageBackend(ABC):
    @abstractmethod
    def save(self, backup_id: str, files: dict[str, Path], note: str) -> BackupResult: ...
    @abstractmethod
    def list_versions(self, config_name: str) -> list[BackupVersion]: ...
    @abstractmethod
    def restore(self, version_id: str, target_dir: Path | None = None) -> RestoreResult: ...
    @abstractmethod
    def delete_version(self, version_id: str) -> bool: ...
```

---

## 5. 差异备份与版本管理

- **全量备份 (full)**: 每次备份所有文件
- **增量备份 (incremental)**: 基于最近一次备份，只备份变化的文件
- **差异备份 (diff)**: 基于第一个全量备份，只备份变化的文件
- **版本管理**: 每个配置项保留 `max_versions` 个版本，超出时自动删除最旧版本
- **文件对比**: 使用 SHA256 哈希 + 文件修改时间双重校验

---

## 6. 自动描述生成

用户创建备份时，系统会自动生成结构化的内容描述：

```
VS Code 配置备份 — 2026-06-27 21:00
├─ 主题: One Dark Pro
├─ 字号: 14
├─ 字体: Cascadia Code
├─ 自动保存: afterDelay
├─ 颜色主题: One Dark Pro
└─ 备注: (用户输入)
```

---

## 7. 技术栈

| 类别 | 技术 |
|------|------|
| 语言 | Python 3.14+ |
| GUI | PySide6 (Qt 6.x) |
| SFTP | paramiko |
| WebDAV | webdav4 |
| JSONPath 解析 | jsonpath-ng |
| 文件监控 | watchdog |
| 打包 | PyInstaller (Nuitka 备选) |
| 定时任务 | Windows Task Scheduler (`schtasks.exe`) |

---

## 8. 依赖清单 (`requirements.txt`)

```
PySide6>=6.8
paramiko>=3.5
webdav4>=0.12
jsonpath-ng>=1.7
watchdog>=6.0
pyinstaller>=6.12
```

---

## 9. 交付物

1. 完整项目源码
2. `requirements.txt` 依赖清单
3. `build.ps1` PyInstaller 打包脚本
4. 5-7 个内置软件配置规则 JSON 文件
5. 中文使用说明文档

---

## 10. 开发阶段规划

| 阶段 | 内容 | 预计工时 |
|------|------|----------|
| Phase 1 | 项目骨架搭建 + 核心数据结构 + JSON 配置解析器 | 1d |
| Phase 2 | 本地/ZIP 存储后端 + 差异备份/版本管理 | 1d |
| Phase 3 | 远程存储后端 (FTP/SFTP/WebDAV) | 1d |
| Phase 4 | GUI 备份/恢复面板 | 1.5d |
| Phase 5 | GUI 配置管理面板 + 定时任务面板 | 1d |
| Phase 6 | 自动描述生成 + 设置面板 | 0.5d |
| Phase 7 | 内置规则编写 + 测试 | 0.5d |
| Phase 8 | 打包脚本 + 使用文档 | 0.5d |
