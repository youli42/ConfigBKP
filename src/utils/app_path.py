import sys
from pathlib import Path


def get_app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent.parent


def get_config_dir() -> Path:
    return get_app_root() / "config"


def get_default_backup_dir() -> Path:
    return get_app_root() / "backups"
