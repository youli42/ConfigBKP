from pathlib import Path
import platform
from typing import Optional

from src.core.config_parser import load_config, filter_by_platform
from src.utils.path_expander import expand


_SCAN_DIRS = [
    "%APPDATA%",
    "%LOCALAPPDATA%",
    "%ProgramFiles%",
    "%ProgramW6432%",
    "%USERPROFILE%\\.config",
]


def scan_installed(config_dirs: list[Path]) -> list[str]:
    matched_names: list[str] = []
    all_rules = _load_rules(config_dirs)
    system_rules = filter_by_platform(all_rules)

    for rule in system_rules:
        name = rule.get("name", "")
        paths = rule.get("paths", [])
        for p in paths:
            expanded = expand(p)
            if expanded.exists():
                matched_names.append(name)
                break

    for scan_dir_str in _SCAN_DIRS:
        scan_dir = expand(scan_dir_str)
        if not scan_dir.exists():
            continue
        try:
            entries = {d.name.lower() for d in scan_dir.iterdir() if d.is_dir()}
        except PermissionError:
            continue
        for rule in system_rules:
            name = rule.get("name", "")
            if name in matched_names:
                continue
            rule_keywords = name.lower().split()
            if any(kw in entries for kw in rule_keywords):
                matched_names.append(name)

    return matched_names


def _load_rules(config_dirs: list[Path]) -> list[dict]:
    rules = []
    for cfg_dir in config_dirs:
        if not cfg_dir.exists():
            continue
        for fpath in sorted(cfg_dir.glob("*.jsonc")):
            try:
                cfg = load_config(fpath)
                if cfg.get("enabled", True):
                    rules.append(cfg)
            except Exception:
                continue
    return rules
