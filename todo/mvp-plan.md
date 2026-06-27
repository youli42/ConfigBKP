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
| **配置格式 .jsonc** | 支持注释，方便高级用户手写 |
| **自动扫描本机** | 遍历 `%APPDATA%` / `Program Files`，匹配规则自动勾选 |
| **文件占用处理** | `MoveFileEx + MOVEFILE_DELAY_UNTIL_REBOOT` 重启时替换 |
| **JSON 解析器简化** | 点号路径 `extensions.theme` + `functools.reduce` |

---

## 配置规则格式 (.jsonc)

```jsonc
{
  // -------- 基本信息 --------
  "name": "VS Code",                    // 显示名称（必填）
  "description": "Visual Studio Code 编辑器配置",
  "version": 1,
  "enabled": true,

  // -------- 平台声明（新增）--------
  "platform": "windows",                // 配置文件适用的平台
                                        // "windows"  | "macos"  | "linux"
                                        // "cross-platform"（跨平台通用）
                                        // 扫描时按平台过滤，避免在 macOS 上加载 Windows-only 规则

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
| `"cross-platform"` | 跨平台通用 | 所有平台均显示，扫描时跳过（无特定路径） |

---

## MVP 架构

```
WinConfigBKP/
├── main.py
├── requirements.txt                 # PySide6 + watchdog + pyinstaller
├── build.ps1
│
├── config/
│   ├── builtin/                     # .jsonc 格式，带 platform 字段
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
│   │   ├── main_window.py
│   │   ├── backup_tab.py
│   │   ├── restore_tab.py
│   │   ├── config_tab.py            # JSONC 源码编辑 + 语法验证
│   │   ├── scheduler_tab.py
│   │   └── settings_tab.py
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── backup_engine.py         # QThreadPool + QRunnable + Signals
│   │   ├── restore_engine.py        # 占用检测 + MoveFileEx 延迟替换
│   │   ├── config_parser.py         # .jsonc 解析 + functools.reduce 字段读值
│   │   └── scanner.py               # 扫描本机已装软件（按 platform 过滤）
│   │
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── base.py                  # 抽象接口
│   │   ├── local.py                 # 本地目录
│   │   └── zip_storage.py           # ZIP 打包
│   │
│   ├── scheduler/
│   │   ├── __init__.py
│   │   └── scheduler.py             # Windows Task Scheduler 集成
│   │
│   └── utils/
│       ├── __init__.py
│       ├── file_hasher.py           # SHA256 哈希
│       ├── path_expander.py         # 环境变量路径展开
│       └── file_locker.py           # 占用检测 + MoveFileEx
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
  │    ├─ 展开 %xxx% 环境变量
  │    └─ 检查路径是否存在
  │         ├─ 存在 ✓ → 自动勾选该规则
  │         └─ 不存在 → 跳过
  ├─ 额外扫描 %APPDATA% 和 %ProgramFiles% 顶层目录名
  │    └─ 与规则库 name 做模糊匹配 → 自动勾选
  └─ 结果展示：共扫描 N 条规则，匹配并勾选 M 条
```

---

## MVP 开发阶段

| 阶段 | 内容 |
|------|------|
| Phase 1 | 项目骨架 + 数据结构 + config_parser + 5 条内置规则 |
| Phase 2 | 本地/ZIP 存储 + backup_engine (异步) |
| Phase 3 | restore_engine + 文件占用处理 |
| Phase 4 | GUI 主窗口 + 备份/恢复面板 |
| Phase 5 | 配置管理 JSONC 编辑器 + 扫描本机功能 |
| Phase 6 | 定时任务 + 设置面板 |
| Phase 7 | 打包 + 测试 |
