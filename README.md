# WinConfigBKP

Windows 配置文件备份工具。自动扫描本机已装软件，一键备份/恢复 VS Code、PowerShell、Git、Windows Terminal 等常用软件的配置文件。

## 功能

- **自动扫描** — 扫描本机已装软件，自动勾选匹配的配置规则
- **一键备份/恢复** — 勾选软件 → 选择目标 → 点击备份/恢复
- **增量备份** — 只备份变化的文件，节省空间
- **版本管理** — 自动保留最近 N 个版本，超出自动清理
- **多种存储** — 本地目录 / ZIP 打包
- **文件占用处理** — 检测被锁文件，支持重启时替换
- **JSONC 配置规则** — 自由添加新软件的备份规则
- **定时备份** — 注册 Windows 计划任务每日自动备份
- **UAC 自动提权** — 非管理员运行时自动请求提升权限

## 快速开始

### 环境要求

- Python 3.10+
- uv 或 pip

### 安装与运行

```powershell
# 1. 克隆项目
cd E:\LWS_500G\Code\ConfigBKP

# 2. 创建虚拟环境并安装依赖
uv venv
uv pip install --python .\.venv\Scripts\python.exe -r requirements.txt

# 3. 激活虚拟环境
.\.venv\Scripts\activate

# 4. 运行
python main.py
```

首次运行会弹出 UAC 权限请求窗口，点击「是」以管理员身份运行。

### 打包为 EXE

```powershell
# 确保依赖已安装
.\.venv\Scripts\activate

# 执行打包
.\build.ps1
```

打包后的 exe 位于 `dist/WinConfigBKP-1.0.0.exe`，双击即可运行。

## 配置规则

内置 5 条规则，位于 `config/builtin/`：

| 规则 | 平台 | 备份路径 |
|------|------|----------|
| VS Code | windows | `%APPDATA%\Code\User\*.json` |
| PowerShell | windows | `%USERPROFILE%\Documents\PowerShell\*.ps1` |
| Git | cross-platform | `%USERPROFILE%\.gitconfig` |
| Windows Terminal | windows | `%LOCALAPPDATA%\Packages\...\settings.json` |
| Oh My Posh | windows | `%USERPROFILE%\.oh-my-posh.omp.json` |

用户自定义规则放在 `config/user/`，程序会自动加载。

### 规则格式

```jsonc
{
  "name": "软件名称",                    // 显示名称
  "platform": "windows",                // windows | macos | linux | cross-platform
  "paths": ["%APPDATA%\\...\\file"],    // 备份路径，支持 %xxx% 环境变量
  "parser_fields": {                     // 自动生成备份摘要
    "editor.fontSize": "字号"
  },
  "strategy": {
    "type": "incremental",              // full | incremental
    "max_versions": 10                  // 最大保留版本数
  }
}
```

## 项目结构

```
WinConfigBKP/
├── main.py                 # 入口（UAC 提权）
├── requirements.txt        # 依赖清单
├── build.ps1               # PyInstaller 打包脚本
├── config/
│   ├── builtin/            # 内置配置规则 (.jsonc)
│   └── user/               # 用户自定义规则
├── src/
│   ├── gui/                # PySide6 界面
│   │   ├── main_window.py  #   3-Tab 主窗口
│   │   ├── home_tab.py     #   备份/恢复面板
│   │   ├── config_tab.py   #   规则管理面板
│   │   └── settings_tab.py #   设置（含定时任务）
│   ├── core/               # 核心逻辑
│   │   ├── backup_engine.py    # 异步备份引擎
│   │   ├── restore_engine.py   # 异步恢复引擎
│   │   ├── config_parser.py    # JSONC 解析
│   │   ├── manifest_manager.py # 增量备份清单
│   │   └── scanner.py          # 本机软件扫描
│   ├── storage/            # 存储后端
│   │   ├── local.py        #   本地目录
│   │   └── zip_storage.py  #   ZIP 打包
│   └── utils/              # 工具
│       ├── file_hasher.py
│       ├── path_expander.py
│       └── file_locker.py
└── todo/                   # 开发文档
```

## 技术栈

- Python 3.14 + PySide6
- JSONC 配置（json5 解析）
- QThreadPool + QRunnable 异步
- Windows Task Scheduler（计划任务）
- PyInstaller 打包
