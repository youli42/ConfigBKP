import ast, re, sys
from pathlib import Path

root = Path(r"E:\LWS_500G\Code\ConfigBKP")
files = [
    "src/gui/main_window.py",
    "src/gui/home_tab.py",
    "src/gui/config_tab.py",
    "src/gui/config_wizard.py",
    "src/gui/settings_tab.py",
    "src/core/backup_engine.py",
    "src/core/restore_engine.py",
]

# Search for string literals and f-strings that appear to be user-visible
# (not import paths, not logging format strings, etc.)
patterns = {
    'setPlainText': False,
    'setText': False,
    'setPlaceholderText': False,
    'setWindowTitle': False,
    'setTitle': False,
    'addItem': False,
    'setItem': True,
    'setHorizontalHeaderLabels': True,
    'addItems': True,
    'QMessageBox': True,
    'QPushButton': True,
    'QLabel': True,
    'QCheckBox': True,
    'QGroupBox': True,
    'QInputDialog': True,
    'QFileDialog': True,
    'message.emit': True,
}

all_strings = []
for fpath_str in files:
    fpath = root / fpath_str
    if not fpath.exists():
        continue
    content = fpath.read_text(encoding='utf-8')
    # Find all quoted strings and f-strings
    # Simple approach: find all string literals in contexts that look like UI
    strings = set()
    for m in re.finditer(r'(?:"([^"]{4,})"|' + "'" + r'([^"]{4,})' + "'" + r')', content):
        s = m.group(1) or m.group(2)
        if '%' not in s and '{' not in s and s.strip():
            strings.add(s.strip())
    for s in sorted(strings):
        print(f"  {fpath_str}: {s}")

print(f"\nFound strings across all files")
