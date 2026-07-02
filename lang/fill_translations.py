"""Fill English translations into en_US.ts and compile to .qm."""
import re
import subprocess
import sys
from pathlib import Path

# ═══════════════════════════════════════════════════════════════
# Complete Chinese → English translation dictionary
# ═══════════════════════════════════════════════════════════════
TRANSLATIONS: dict[str, str] = {
    # --- General UI ---
    "备份": "Backup",
    "恢复": "Restore",
    "保存": "Save",
    "保存成功": "Saved successfully",
    "删除": "Delete",
    "新建": "New",
    "添加": "Add",
    "完成": "Finish",
    "取消全选": "Deselect All",
    "全选": "Select All",
    "反选": "Invert Selection",
    "启用": "Enabled",
    "就绪": "Ready",
    "提示": "Info",
    "错误": "Error",
    "成功": "Success",
    "失败": "Failed",
    "描述": "Description",
    "名称:": "Name:",
    "描述:": "Description:",
    "备注": "Note",
    "备注:": "Note:",
    "版本": "Version",
    "时间": "Time",
    "操作": "Actions",
    "配置": "Config",
    "配置数": "Configs",
    "配置规则": "Config Rules",
    "规则管理": "Rule Management",
    "设置": "Settings",
    "关于": "About",
    "语言": "Language",
    "界面语言:": "Language:",
    "步骤": "Steps",
    "版本策略": "Version Policy",
    "恢复设置": "Restore Settings",
    "定时备份": "Scheduled Backup",
    "基本信息": "Basic Info",
    "源路径": "Source Paths",
    "解析字段": "Parser Fields",
    "备份策略": "Backup Strategy",
    "向导": "Wizard",
    "向导模式": "Wizard Mode",
    "源码": "Source",
    "字段路径": "Field Path",
    "字段路径:": "Field Path:",
    "显示标签": "Display Label",
    "显示标签:": "Display Label:",
    "平台:": "Platform:",
    "忽略模式:": "Ignore Patterns:",
    "备份类型:": "Backup Type:",
    "最大版本数:": "Max Versions:",
    "最大保留版本数:": "Max Versions:",
    "备份时间:": "Time:",
    "备份目标:": "Target:",
    "备份目录: {}": "Backup directory: {}",
    "已保存 ✔": "Saved ✔",
    "已保存到 {}": "Saved to {}",
    "已创建": "Created",
    "语法正确 ✔": "Syntax OK ✔",
    "语法错误": "Syntax Error",
    "语法错误: {}": "Syntax error: {}",
    "读取失败: {}": "Read failed: {}",
    "生成的 JSONC 格式有误": "Generated JSONC format is invalid",

    # --- Buttons ---
    "上一步": "Previous",
    "下一步": "Next",
    "浏览...": "Browse...",
    "浏览文件...": "Browse File...",
    "浏览目录...": "Browse Directory...",
    "添加路径": "Add Path",
    "删除路径": "Remove Path",
    "添加字段": "Add Field",
    "删除字段": "Remove Field",
    "添加忽略模式": "Add Ignore Pattern",
    "添加解析字段": "Add Field",
    "恢复此批次": "Restore This Batch",
    "保存": "Save",
    "应用定时设置": "Apply Schedule",
    "开启每日备份": "Enable Daily Backup",
    "注册重启时替换 (适用于被锁文件)": "Register reboot replacement (for locked files)",

    # --- Home tab ---
    "扫描本机已装软件": "Scan Installed Software",
    "备份/恢复": "Backup / Restore",
    "备份历史": "Backup History",
    "备份备注（可选）": "Backup note (optional)",
    "备份目标:": "Target:",
    "备份": "Backup",
    "恢复": "Restore",
    "备份结果": "Backup Result",
    "备份完成": "Backup Complete",
    "备份失败": "Backup Failed",
    "恢复完成": "Restore Complete",
    "恢复失败": "Restore Failed",
    "批次恢复完成": "All restores complete",
    "批次中所有配置已恢复": "All configs in this batch have been restored",
    "扫描完成": "Scan Complete",
    "扫描完成，匹配 {} 条规则": "Scan complete, matched {} rules",
    "扫描完成，匹配 {} 条规则:\n{}": "Scan complete, matched {} rules:\n{}",
    "已成功恢复 {}": "Successfully restored {}",
    "已恢复 {}": "Restored {}",
    "最新配置": "Latest Config",
    "共 {} 个配置的最新版本": "Latest versions of {} configs",
    "成功: {} 个配置 ({} 文件)": "Success: {} configs ({} files)",
    "跳过: {} 个": "Skipped: {}",
    "失败: {} 个": "Failed: {}",
    "无任何操作": "No operations",
    "备份完成: {}": "Backup complete: {}",
    "已备份:": "Backed up:",
    "已跳过:": "Skipped:",
    "失败:": "Failed:",
    "  ✓ {} ({} 文件)": "  ✓ {} ({} files)",
    "  - {}": "  - {}",
    "  ✗ {}: {}": "  ✗ {}: {}",
    "恢复前备份当前文件到临时目录": "Back up current files before restoring",
    "恢复前正在备份当前文件...": "Backing up current files before restore...",
    "发现 {} 个文件变化，正在备份...": "Found {} changed files, backing up...",
    "无文件变化，跳过备份": "No file changes, skipping backup",
    "正在写入备份...": "Writing backup...",
    "正在恢复文件...": "Restoring files...",
    "正在计算文件哈希...": "Calculating file hashes...",
    "正在读取备份文件...": "Reading backup files...",
    "正在检测文件占用...": "Checking file locks...",
    "正在执行备份操作，请等待完成": "Backup in progress, please wait",
    "正在执行恢复操作，请等待完成": "Restore in progress, please wait",
    "请先选择要备份的配置": "Please select configs to backup first",
    "请先选择或新建一个规则": "Please select or create a rule first",
    "请先在右侧勾选要恢复的配置": "Please check the configs to restore on the right",
    "请先在左侧选择一个备份记录": "Please select a backup record on the left",
    "该备份记录无可恢复的版本": "No recoverable versions in this backup record",
    "文件被占用": "File Locked",
    "{} 个文件": "{} files",
    "已备份: {}": "Backed up: {}",
    "已跳过:": "Skipped:",
    # Long string from file locker:
    "{}\n请关闭以下程序后重试：\n{}\n\n或使用设置中的「重启时替换」功能。": "{}\nPlease close these programs and retry:\n{}\n\nOr use the reboot replacement feature in Settings.",
    "此功能需要在恢复时选择「重启时替换」才会生效。\n当文件被程序占用时，系统将在下次重启前自动完成替换。": "This requires selecting 'reboot replacement' during restore.\nWhen files are locked by programs, the system will replace them before the next restart.",
    "以下配置的源文件路径不存在，将被跳过：\n{}\n\n是否继续备份其他配置？": "The following configs have missing source paths and will be skipped:\n{}\n\nContinue backing up the remaining configs?",
    "将依次恢复以下 {} 个配置：\n{}": "The following {} configs will be restored in order:\n{}",
    "未找到配置规则: {}": "Config rule not found: {}",
    "选择备份目标目录": "Select Backup Target",
    "路径不存在": "Path Not Found",
    "确认恢复": "Confirm Restore",
    "确认恢复批次": "Confirm Batch Restore",
    "确认删除": "Confirm Delete",
    "确定删除 {} 吗？": "Are you sure you want to delete {}?",
    "每日备份任务已注册，时间: {}": "Daily backup task registered at: {}",
    "注册任务失败:\n{}": "Task registration failed:\n{}",
    "已取消定时备份任务": "Scheduled backup task cancelled",
    "已保存到 {}": "Saved to {}",
    "在此编辑 JSONC 配置...": "Edit JSONC config here...",
    "必填，如: VS Code": "Required, e.g. VS Code",
    "选填，如: Visual Studio Code 编辑器配置": "Optional, e.g. Visual Studio Code editor config",
    "如: editor.fontSize": "e.g. editor.fontSize",
    "如: 字号": "e.g. Font Size",
    "字段路径不能为空": "Field path cannot be empty",
    "不支持数组索引路径": "Array index paths are not supported",
    "名称不能为空": "Name cannot be empty",
    "输入文件或目录路径：\n支持 %APPDATA% 等环境变量": "Enter file or directory path:\nSupports %APPDATA% env vars",
    "选择配置文件": "Select Config File",
    "选择配置文件目录": "Select Config Directory",
    "解析警告": "Parse Warning",
    "源码 JSONC 解析失败，向导将保持当前数据：\n{}": "Source JSONC parse failed, wizard will keep current data:\n{}",
    "添加路径": "Add Path",
    "重启时替换": "Reboot Replacement",
    "WinConfigBKP - Windows 配置文件备份工具": "WinConfigBKP - Windows Config Backup Tool",
    "Windows 配置文件备份工具": "Windows Config Backup Tool",
    "本地目录": "Local Directory",
    "ZIP 打包": "ZIP Archive",
    "全量备份": "Full Backup",
    "增量备份": "Incremental Backup",
    "备份策略:": "Strategy:",
    "新配置": "New Config",
    "请填写描述": "Add a description",
    "无法保存，JSONC 语法错误:\n{}": "Cannot save, JSONC syntax error:\n{}",
    "生成的配置有误:\n{}": "Generated config is invalid:\n{}",
    "已创建新规则:\n{}": "New rule created:\n{}",
    "恢复前备份当前文件到临时目录": "Back up current files before restoring",
    "语言切换": "Language",
    "语言已切换，重启后生效。": "Language switched, restart to take effect.",
    "每 {} 个配置的最新版本": "Latest version of {} configs",
    "[{}/{}] 正在处理 {}...": "[{}/{}] Processing {}...",
    "[{}/{}] {}: 无文件，已跳过": "[{}/{}] {}: No files, skipped",
    "[{}/{}] {}: 无变化，已跳过": "[{}/{}] {}: No changes, skipped",
    "[{}/{}] {}: 备份完成 ({} 文件)": "[{}/{}] {}: Backup complete ({} files)",
    "[{}/{}] {}: 失败 - {}": "[{}/{}] {}: Failed - {}",
    "Glob 模式：\n如 *.log 或 __pycache__/": "Glob pattern:\ne.g. *.log or __pycache__/",
    "搜索": "Search",
    "注册重启时替换 (适用于被锁文件)": "Register reboot replacement (for locked files)",
    "路径": "Path",
    "路径:": "Path:",
    "路径不能为空": "Path cannot be empty",
    "路径越界: {}": "Path traversal: {}",
    "如: %APPDATA%\\...\\config.json": "e.g. %APPDATA%\\...\\config.json",
    "如: VS Code 用户设置（选填）": "e.g. VS Code user settings (optional)",
    "名称": "Name",
    "范围": "Scope",
    "数据": "Data",
    "配置+数据": "Config + Data",
    "配置文件路径": "Config File Paths",
    "程序数据路径": "App Data Paths",
    "备份配置文件": "Backup Config Files",
    "备份程序数据": "Backup App Data",
    "选择目录": "Select Directory",
    "选择文件": "Select File",
    "请勾选要恢复的配置版本": "Please check the config versions to restore",
    "未找到备份: {}": "Backup not found: {}",
    "部分文件恢复失败: {}": "Partial restore failed: {}",
    "{} 个文件被占用": "{} files are locked",
    "写入失败，已回滚: {}": "Write failed, rolled back: {}",
    "[{}/{}] 正在收集 {} 文件...": "[{}/{}] Collecting files for {}...",
    "[{}/{}] {}: 收集失败 - {}": "[{}/{}] {}: Collection failed - {}",
    "  - {}": "  - {}",
    "  ✗ {}: {}": "  ✗ {}: {}",
}


def main():
    ts_path = Path(__file__).parent / "en_US.ts"
    ts_content = ts_path.read_text(encoding="utf-8")

    # Find all <source> blocks
    pattern = re.compile(r'(<source>(.*?)</source>\s*<translation>).*?(</translation>)', re.DOTALL)

    def replace_match(m: re.Match) -> str:
        source = m.group(2)
        translation = TRANSLATIONS.get(source)
        if translation:
            # Escape XML special chars in translation
            translation_esc = (translation
                               .replace("&", "&amp;")
                               .replace("<", "&lt;")
                               .replace(">", "&gt;")
                               .replace('"', "&quot;"))
            return f'{m.group(1)}{translation_esc}{m.group(3)}'
        # Keep existing translation if not in our dict
        return m.group(0)

    updated = pattern.sub(replace_match, ts_content)
    ts_path.write_text(updated, encoding="utf-8")

    # Count what's been translated vs what's still Chinese/empty
    untranslated = []
    for m in re.finditer(r'<source>(.*?)</source>\s*<translation>(.*?)</translation>', updated, re.DOTALL):
        src = m.group(1)
        tln = m.group(2)
        if not tln.strip() or tln.strip() == src.strip():
            untranslated.append(src)

    print(f"Total strings: {len(TRANSLATIONS)}")
    print(f"Translated: {len(TRANSLATIONS) - len(untranslated)}")
    if untranslated:
        print(f"\nUntranslated ({len(untranslated)}):")
        for s in untranslated:
            print(f"  - {repr(s[:60])}")
    else:
        print("All strings translated!")

    # Compile .ts → .qm
    print("\nCompiling .qm files...")
    qm_path = ts_path.with_suffix(".qm")
    try:
        subprocess.run(
            ["pyside6-lrelease", str(ts_path), "-qm", str(qm_path)],
            check=True, capture_output=True, text=True,
        )
        print(f"  {qm_path.name} — OK")
    except FileNotFoundError:
        print("  pyside6-lrelease not found, trying pyside2-lrelease...")
        try:
            subprocess.run(
                ["pyside2-lrelease", str(ts_path), "-qm", str(qm_path)],
                check=True, capture_output=True, text=True,
            )
            print(f"  {qm_path.name} — OK")
        except FileNotFoundError:
            # Check pip show PySide6 to find scripts dir
            result = subprocess.run(
                [sys.executable, "-m", "PiSide6", "lrelease", str(ts_path)],
                capture_output=True, text=True,
            )
            print("  Could not find lrelease. Install PySide6 tools.")
    except subprocess.CalledProcessError as e:
        print(f"  lrelease failed: {e.stderr}")


if __name__ == "__main__":
    main()
