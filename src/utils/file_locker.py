from pathlib import Path
import ctypes
import os
from typing import Optional

# MoveFileEx flags
MOVEFILE_REPLACE_EXISTING = 1
MOVEFILE_DELAY_UNTIL_REBOOT = 4


def is_file_locked(filepath: Path) -> bool:
    try:
        with open(filepath, "ab") as f:
            pass
        return False
    except (PermissionError, OSError):
        return True


def schedule_reboot_replace(src: Path, dst: Path) -> bool:
    kernel32 = ctypes.windll.kernel32
    src_str = str(src.resolve())
    dst_str = str(dst.resolve())
    result = kernel32.MoveFileExW(
        src_str,
        dst_str,
        MOVEFILE_REPLACE_EXISTING | MOVEFILE_DELAY_UNTIL_REBOOT,
    )
    return result != 0


def get_locked_processes(filepath: Path) -> list[str]:
    process_names: list[str] = []
    known_locks = {
        "Code\\User\\settings.json": "Code.exe",
        "Code\\User\\keybindings.json": "Code.exe",
        "WindowsTerminal": "WindowsTerminal.exe",
        "powershell": "powershell.exe",
    }
    path_str = str(filepath)
    for key, proc in known_locks.items():
        if key in path_str:
            process_names.append(proc)
    return process_names
