# 06-config — 配置文件格式说明

> 本文档面向编写配置规则的用户，非开发者。
> 解析实现细节请参阅 `02-core.md` → `config_parser.py` 章节。

## 文件位置

`config/builtin/` — 内置规则（随项目分发，可编辑/删除）
`config/user/` — 用户自定义规则

程序启动时自动扫描这两个子目录下所有 `.jsonc` 文件。

## 格式规范

使用 JSONC（带注释的 JSON），用 `json5` 库解析。每文件一个规则对象。

## 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | `string` | 是 | 规则显示名称，在 GUI 中作为勾选框标签和历史记录中的配置名 |
| `description` | `string` | 否 | 鼠标悬停时的提示文字 |
| `version` | `number` | 否 | 规则格式版本号，当前为 1 |
| `enabled` | `boolean` | 否 | 是否启用，`false` 时该规则在 GUI 中不显示 |
| `platform` | `string` | 否 | 适用平台，可选值见下方表格，默认 `cross-platform` |
| `paths` | `string[]` | 是 | 要备份的文件或目录路径列表，支持 `%xxx%` 环境变量 |
| `parser_fields` | `object` | 否 | JSON 字段提取规则，键为点号路径，值为显示标签 |
| `strategy.type` | `string` | 否 | 备份策略：`full` 或 `incremental`，默认逻辑按增量处理 |
| `strategy.max_versions` | `number` | 否 | 最大保留版本数，超出时自动删除最旧版本 |
| `strategy.ignore_patterns` | `string[]` | 否 | 忽略的文件 glob 模式（当前代码中未实现过滤逻辑） |

### platform 可选值

| 值 | 含义 |
|----|------|
| `"windows"` | 仅 Windows 系统 |
| `"macos"` | 仅 macOS 系统 |
| `"linux"` | 仅 Linux 系统 |
| `"cross-platform"` | 跨平台通用（默认值） |

### parser_fields 说明

键为点号分隔的 JSON 路径，值为字段显示名。例如 `"editor.fontSize": "字号"` 表示从 JSON 文件中取 `data.editor.fontSize` 的值，显示为`字号: 14`。

当前实现仅支持 JSON 格式的源文件。对于 INI 等非 JSON 格式，该字段在备份摘要中不会输出任何内容。

## 示例

```jsonc
{
  "name": "VS Code",
  "description": "Visual Studio Code 编辑器配置",
  "version": 1,
  "enabled": true,
  "platform": "windows",
  "paths": [
    "%APPDATA%\\Code\\User\\settings.json",
    "%APPDATA%\\Code\\User\\keybindings.json",
    "%APPDATA%\\Code\\User\\snippets\\",
    "%APPDATA%\\Code\\User\\extensions.json"
  ],
  "parser_fields": {
    "extensions.theme": "主题",
    "editor.fontSize": "字号",
    "editor.fontFamily": "字体",
    "files.autoSave": "自动保存",
    "workbench.colorTheme": "颜色主题"
  },
  "strategy": {
    "type": "incremental",
    "max_versions": 10,
    "ignore_patterns": ["*.log", "*.tmp"]
  }
}
```

## 内置规则清单

| 文件名 | name 字段 | platform |
|--------|-----------|----------|
| `vscode.jsonc` | VS Code | windows |
| `powershell.jsonc` | PowerShell | windows |
| `git.jsonc` | Git | cross-platform |
| `windows_terminal.jsonc` | Windows Terminal | windows |
| `ohmyposh.jsonc` | Oh My Posh | windows |
| `everything.jsonc` | Everything | windows |
