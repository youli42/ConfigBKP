# WinConfigBKP — MVP 最小可行方案

## 裁剪项

| 模块 | 状态 | 理由 |
|------|------|------|
| FTP/SFTP/WebDAV | ❌ V2.0 | 配置仅几 MB，网盘同步即可 |
| GUI 向导式配置编辑器 | ❌ V2.0 | JSONC 源码编辑 + 语法检查足够 |
| 注册表备份 | ❌ 不支持 | 90% 配置在 `%APPDATA%` / `%USERPROFILE%` |
| 差异备份 (Diff) | ❌ 砍掉 | 增量备份对配置文件足够 |
| jsonpath-ng | ❌ 砍掉 | `functools.reduce` + 点号路径更轻量 |

## 增强项

| 模块 | 说明 |
|------|------|
| **QThreadPool + QRunnable + Signals** | 后台线程防卡死，信号更新 UI |
| **配置格式 .jsonc** | 使用 `json5` 库解析，支持注释 |
| **自动扫描本机** | 遍历 `%APPDATA%` / `Program Files`，匹配规则自动勾选 |
| **文件占用处理** | `MoveFileEx + MOVEFILE_DELAY_UNTIL_REBOOT` 重启时替换 |
| **JSON 解析器简化** | 点号路径 `extensions.theme` + `functools.reduce` |
| **管理员权限自动提权** | 启动时检测非管理员 → UAC 提权重启 |

---

## 技术规范（硬性约束）

1. **所有路径操作必须使用 `pathlib.Path`**，禁止任何形式的字符串拼接、`replace('\\', '/')` 或 `os.path.join` 混用。
2. **所有耗时操作必须在线程中执行**（QThreadPool + QRunnable），严禁在主线程中执行文件 I/O。
3. **所有需管理员权限的操作**（备份/恢复）必须优先检测权限，不足则提权。

---

## 配置规则格式 (.jsonc)

```jsonc
{
  // -------- 基本信息 --------
  "name": "VS Code",                    // 显示名称（必填）
  "description": "Visual Studio Code 编辑器配置",
  "version": 1,
  "enabled": true,

  // -------- 平台声明 --------
  "platform": "windows",                // "windows" | "macos" | "linux" | "cross-platform"
                                        // 扫描时按平台过滤

  // -------- 源文件 --------
  "paths": [
    "%APPDATA%\\Code\\User\\settings.json",
    "%APPDATA%\\Code\\User\\keybindings.json",
    "%APPDATA%\\Code\\User\\snippets\\",
    "%APPDATA%\\Code\\User\\extensions.json"
  ],

  // -------- 关键字段提取（自动生成备份摘要）--------
  "parser_fields": {
    "extensions.theme":            "主题",
    "editor.fontSize":             "字号",
    "editor.fontFamily":           "字体",
    "files.autoSave":              "自动保存",
    "workbench.colorTheme":        "颜色主题"
  },

  // -------- 备份策略 --------
  "strategy": {
    "type": "incremental",              // full | incremental
    "max_versions": 10,
    "ignore_patterns": ["*.log", "*.tmp", "__pycache__/"]
  }
}
```

### `platform` 字段取值说明

| 值 | 含义 | 扫描行为 |
|----|------|----------|
| `"windows"` | 仅 Windows 可用 | 只在 Windows 上扫描并显示 |
| `"macos"` | 仅 macOS 可用 | 只在 macOS 上扫描并显示 |
| `"linux"` | 仅 Linux 可用 | 只在 Linux 上扫描并显示 |
| `"cross-platform"` | 跨平台通用 | 所有平台均显示，扫描时跳过路径检查 |

---

## MVP 架构（3 Tab）

```
WinConfigBKP/
├── main.py                             # 入口：UAC 权限检测 → 提权 / 正常启动
├── requirements.txt                    # PySide6 + json5 + watchdog + pyinstaller
├── build.ps1
│
├── config/
│   ├── builtin/                        # .jsonc 格式，带 platform 字段
│   │   ├── vscode.jsonc
│   │   ├── powershell.jsonc
│   │   ├── git.jsonc
│   │   ├── windows_terminal.jsonc
│   │   └── ohmyposh.jsonc
│   └── user/
│
├── src/
│   ├── gui/
│   │   ├── __init__.py
│   │   ├── main_window.py              # 3-Tab 主窗口
│   │   ├── home_tab.py                 # Tab 1: 备份/恢复合一（核心操作区）
│   │   ├── config_tab.py               # Tab 2: JSONC 源码编辑 + 语法验证 + 扫描本机
│   │   └── settings_tab.py             # Tab 3: 设置 + 定时任务（含每日备份开关）
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── backup_engine.py            # QThreadPool + QRunnable + Signals
│   │   ├── restore_engine.py           # 占用检测 + MoveFileEx 延迟替换
│   │   ├── config_parser.py            # json5 解析 + functools.reduce 字段读值
│   │   ├── manifest_manager.py         # 独立类：管理 manifest.json（文件列表 + SHA256）
│   │   └── scanner.py                  # 扫描本机已装软件（按 platform 过滤）
│   │
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── base.py                     # 抽象接口
│   │   ├── local.py                    # 本地目录
│   │   └── zip_storage.py              # ZIP 打包
│   │
│   └── utils/
│       ├── __init__.py
│       ├── file_hasher.py              # SHA256 哈希
│       ├── path_expander.py            # 环境变量展开 → pathlib.Path 统一输出
│       └── file_locker.py              # 占用检测 + MoveFileEx
│
└── resources/
    ├── icons/
    └── styles/
```

---

## 异步架构（防卡死核心）

```python
class BackupSignals(QObject):
    progress = Signal(int)
    message  = Signal(str)
    done     = Signal(object)
    error    = Signal(str)

class BackupWorker(QRunnable):
    def __init__(self, config, storage, signals):
        super().__init__()
        self.config = config
        self.storage = storage
        self.signals = signals

    def run(self):
        try:
            self.signals.message.emit("正在收集文件...")
            self.signals.progress.emit(10)
            files = collect_files(self.config)

            self.signals.message.emit("正在计算差异...")
            self.signals.progress.emit(40)
            hashes = compute_hashes(files)

            self.signals.message.emit("正在写入备份...")
            self.signals.progress.emit(70)
            result = self.storage.save(files, hashes)

            self.signals.progress.emit(100)
            self.signals.done.emit(result)
        except Exception as e:
            self.signals.error.emit(str(e))
```

---

## ManifestManager（增量备份状态记录）

```
存储目录/
├── manifest.json          ← ManifestManager 维护
│   {
│     "last_backup": "2026-06-27T21:00:00",
│     "files": {
│       "Code/User/settings.json": {
│         "sha256": "a1b2c3...",
│         "size": 1234,
│         "mtime": "2026-06-27T20:30:00"
│       },
│       "Code/User/keybindings.json": { ... }
│     }
│   }
├── backup-20260627-2100.zip    # 每次备份的压缩包
├── backup-20260628-0900.zip
└── ...
```

增量备份流程：

```
ManifestManager.load() → 读取上次 manifest
  ├─ 计算当前文件 SHA256
  ├─ 与 manifest 对比
  │    ├─ 新文件 → 加入备份
  │    ├─ SHA256 变化 → 加入备份
  │    ├─ 未变化 → 跳过
  │    └─ 已删除 → 从 manifest 移除
  └─ 打包有变化的文件 → ManifestManager.save() 更新 manifest
```

---

## 恢复安全机制

```
恢复请求
  ├─ 检测目标文件是否被占用 (NtCreateFile)
  │    ├─ 无占用 → 直接覆盖还原 ✓
  │    └─ 有占用 → 弹窗：请关闭以下程序后再试
  │                [VS Code]  [Windows Terminal]
  │                ├─ 用户手动关闭后重试 ✓
  │                └─ 用户选择「重启时替换」
  │                    → MoveFileEx(src, dst, MOVEFILE_DELAY_UNTIL_REBOOT)
  │                    → 提示「重启后生效」
```

---

## UAC 权限检测（main.py 入口）

```python
import ctypes
import sys

def is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except AttributeError:
        return False  # 非 Windows 平台

def main():
    if not is_admin():
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1
        )
        sys.exit()
    # ... 正常启动 GUI
```

---

## GUI 布局（3 Tab）

### Tab 1: 主面板（home_tab.py）— 备份/恢复合一

```
┌───────────────────────────────────────────┐
│  [扫描本机]  [全选/取消]                    │
│  ┌─ 软件列表 ───────────────────────────┐  │
│  │ ☑ VS Code                            │  │
│  │ ☐ PowerShell                         │  │
│  │ ☑ Git                                │  │
│  │ ☑ Windows Terminal                   │  │
│  │ ☐ Oh My Posh                         │  │
│  └──────────────────────────────────────┘  │
│  备份备注: [___________________________]   │
│  目标: [本地目录 ▼] [...浏览...]           │
│                                           │
│  [ 🔵 备份 ]  [ 🔴 恢复 ]  [ 进度: ██░░░ ]│
│  ┌─ 历史记录 ─────────────────────────────┐│
│  │ 2026/06/27 21:00  VS Code 主题:xxx ... ││
│  │ 2026/06/27 09:00  Git 配置备份         ││
│  └────────────────────────────────────────┘│
└───────────────────────────────────────────┘
```

### Tab 2: 规则管理（config_tab.py）

```
┌───────────────────────────────────────────┐
│  规则列表:  [VS Code] [Git] [Terminal]    │
│  ┌─ JSONC 源码编辑 ──────────────────────┐ │
│  │ {                                      │ │
│  │   "name": "VS Code",                   │ │
│  │   "platform": "windows",               │ │
│  │   ...                                  │ │
│  │ }                                      │ │
│  └────────────────────────────────────────┘ │
│  [✔ 语法正确]  [保存]  [恢复默认]           │
└───────────────────────────────────────────┘
```

### Tab 3: 设置（settings_tab.py）— 含定时任务

```
┌───────────────────────────────────────────┐
│  ── 定时备份 ──                            │
│  [☑ 开启每日备份]  时间: [22:00 ▸]         │
│  备份目标: [C:\Backup\Configs ▸ ▸浏览]    │
│                                           │
│  ── 版本策略 ──                            │
│  最大保留版本数: [10 ▸]                    │
│  备份策略: [增量 ▼]                       │
│                                           │
│  ── 恢复设置 ──                            │
│  [☑ 恢复前备份当前文件到临时目录]           │
│                                           │
│  ── 关于 ──                                │
│  WinConfigBKP v1.0.0                      │
└───────────────────────────────────────────┘
```

---

## 内置配置规则计划

| 规则 | 平台 | 路径 |
|------|------|------|
| VS Code | windows | `%APPDATA%\Code\User\*.json` |
| PowerShell | windows | `%USERPROFILE%\Documents\PowerShell\*\*.ps*1` |
| Git | cross-platform | `%USERPROFILE%\.gitconfig` |
| Windows Terminal | windows | `%LOCALAPPDATA%\Packages\*\LocalState\settings.json` |
| Oh My Posh | windows | `%USERPROFILE%\AppData\Local\Programs\oh-my-posh\themes\*` |

---

## 扫描本机逻辑 (`scanner.py`)

```
点击「扫描本机已装软件」
  ├─ 获取当前平台 (platform.system())
  ├─ 过滤 config/builtin/*.jsonc，只加载 platform 匹配的规则
  ├─ 遍历每个规则的 paths：
  │    ├─ 展开 %xxx% 环境变量 → pathlib.Path
  │    └─ 检查路径是否存在
  │         ├─ 存在 ✓ → 自动勾选该规则
  │         └─ 不存在 → 跳过
  ├─ 额外扫描 %APPDATA% 和 %ProgramFiles% 顶层目录名
  │    └─ 与规则库 name 做模糊匹配 → 自动勾选
  └─ 结果展示：共扫描 N 条规则，匹配并勾选 M 条
```

---

## 依赖清单 (`requirements.txt`)

```
PySide6>=6.8
json5>=0.10
watchdog>=6.0
pyinstaller>=6.12
```

---

## MVP 开发阶段

| 阶段 | 内容 |
|------|------|
| Phase 1 | 项目骨架 + 目录结构 + 5 条内置 .jsonc 规则 |
| Phase 2 | config_parser (json5) + path_expander + ManifestManager |
| Phase 3 | storage (local + zip) + file_hasher + backup_engine (异步) |
| Phase 4 | restore_engine + file_locker (占用检测 + MoveFileEx) |
| Phase 5 | GUI 3 Tab: main_window + home_tab + config_tab + settings_tab |
| Phase 6 | scanner.py + UAC main.py + 打包测试 |
