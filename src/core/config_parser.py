from pathlib import Path
import json5
import platform
from functools import reduce
from typing import Any


_OVERRIDE_KEY = "$schema"


def load_config(filepath: Path) -> dict[str, Any]:
    with open(filepath, encoding="utf-8") as f:
        return json5.load(f)


def get_field(data: dict[str, Any], dotted_path: str) -> Any | None:
    try:
        return reduce(lambda d, k: d[k], dotted_path.split("."), data)
    except (KeyError, TypeError, IndexError):
        return None


def generate_description(name: str, config: dict[str, Any], source_files: dict[str, Path]) -> str:
    lines = [f"{name} 配置备份"]
    for filepath_str, filepath in source_files.items():
        parser_fields = config.get("parser_fields", {})
        if not parser_fields:
            continue
        try:
            content_text = filepath.read_text(encoding="utf-8")
            import json5 as _json5
            data = _json5.loads(content_text)
        except Exception:
            continue
        for dotted_path, label in parser_fields.items():
            value = get_field(data, dotted_path)
            if value is not None:
                lines.append(f"├─ {label}: {value}")
    return "\n".join(lines) if len(lines) > 1 else lines[0]


def filter_by_platform(rules: list[dict]) -> list[dict]:
    system = platform.system().lower()
    result = []
    for rule in rules:
        plat = rule.get("platform", "cross-platform")
        if plat == "cross-platform":
            result.append(rule)
        elif plat == system:
            result.append(rule)
        elif plat == "windows" and system == "windows":
            result.append(rule)
        elif plat == "linux" and system == "linux":
            result.append(rule)
        elif plat == "macos" and system == "darwin":
            result.append(rule)
    return result
