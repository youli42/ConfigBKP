"""Extract all tr() strings from source code and generate .ts files."""
import re
import ast
import sys
from pathlib import Path

SRC_DIRS = [
    Path(__file__).resolve().parent.parent / "src",
]
EXTRA_FILES = [
    Path(__file__).resolve().parent.parent / "main.py",
]


def extract_tr_strings(filepath: Path) -> set[str]:
    """Extract all string literals passed to tr() using regex."""
    strings = set()
    text = filepath.read_text(encoding="utf-8")
    # Match tr("...") with possible .format() or other chaining
    pattern = re.compile(r'(?<!\w)tr\(\s*("(?:[^"\\]|\\.)*")\s*\)')
    for m in pattern.finditer(text):
        try:
            s = ast.literal_eval(m.group(1))
            strings.add(s)
        except (ValueError, SyntaxError):
            pass
    return strings


def main():
    all_strings: set[str] = set()
    
    for src_dir in SRC_DIRS:
        for py_file in sorted(src_dir.rglob("*.py")):
            strings = extract_tr_strings(py_file)
            if strings:
                all_strings.update(strings)
                print(f"  {py_file.relative_to(src_dir.parent)}: {len(strings)} strings")
    
    for fpath in EXTRA_FILES:
        if fpath.exists():
            strings = extract_tr_strings(fpath)
            if strings:
                all_strings.update(strings)
                print(f"  {fpath.name}: {len(strings)} strings")
    
    print(f"\nTotal unique strings: {len(all_strings)}")
    
    # Generate zh_CN.ts (source language, no translation needed)
    # QTranslator returns source text when no translation is found,
    # so we use empty <translation> tags.
    ts_path = Path(__file__).parent / "zh_CN.ts"
    generate_ts(ts_path, all_strings, "zh_CN", {})
    print(f"Generated: {ts_path}")
    
    # Read existing en_US.py DATA for any existing translations
    en_py_path = Path(__file__).parent / "en_US.py"
    existing_translations = {}
    if en_py_path.exists():
        # Simple eval of the DATA dict
        content = en_py_path.read_text(encoding="utf-8")
        # Extract the DATA dict using regex-based approach
        data_match = re.search(r'DATA\s*=\s*(\{.*\})', content, re.DOTALL)
        if data_match:
            try:
                data_dict = ast.literal_eval(data_match.group(1))
                existing_translations = data_dict
            except:
                pass
    
    print(f"Existing translations from en_US.py: {len(existing_translations)} strings")
    
    # Generate en_US.ts with existing translations (all Chinese values currently)
    ts_en_path = Path(__file__).parent / "en_US.ts"
    generate_ts(ts_en_path, all_strings, "en_US", existing_translations)
    print(f"Generated: {ts_en_path}")
    
    # Check for strings in en_US.py not found in source
    extra = set(existing_translations.keys()) - all_strings
    if extra:
        print(f"\nWARNING: {len(extra)} strings in en_US.py not found in source:")
        for s in sorted(extra):
            print(f"  - {s}")
    
    missing = all_strings - set(existing_translations.keys())
    if missing:
        print(f"\nNEW strings not in en_US.py ({len(missing)}):")
        for s in sorted(missing):
            print(f"  - {s}")


def generate_ts(path: Path, strings: set[str], language: str, translations: dict[str, str]):
    """Generate a .ts file."""
    lines = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<!DOCTYPE TS>',
        f'<TS version="2.1" language="{language}">',
        '<context>',
        '    <name>App</name>',
    ]
    
    for s in sorted(strings):
        translation = translations.get(s, "")
        # Escape XML special chars
        source_escaped = escape_xml(s)
        translation_escaped = escape_xml(translation)
        lines.append('    <message>')
        lines.append(f'        <source>{source_escaped}</source>')
        if translation:
            lines.append(f'        <translation>{translation_escaped}</translation>')
        else:
            lines.append('        <translation></translation>')
        lines.append('    </message>')
    
    lines.extend([
        '</context>',
        '</TS>',
        '',
    ])
    
    path.write_text('\n'.join(lines), encoding="utf-8")
    print(f"  {path.name}: {len(strings)} messages")


def escape_xml(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


if __name__ == "__main__":
    main()
