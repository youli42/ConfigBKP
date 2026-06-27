from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Iterable


class BackupResult:
    def __init__(self, backup_id: str, config_name: str, files_count: int, total_size: int, note: str = "",
                 session_id: str = ""):
        self.backup_id = backup_id
        self.config_name = config_name
        self.files_count = files_count
        self.total_size = total_size
        self.note = note
        self.session_id = session_id


class RestoreResult:
    def __init__(self, config_name: str, files_restored: list[Path], files_pending: list[Path]):
        self.config_name = config_name
        self.files_restored = files_restored
        self.files_pending = files_pending


class BackupVersion:
    def __init__(self, backup_id: str, config_name: str, timestamp: str, note: str, description: str,
                 session_id: str = ""):
        self.backup_id = backup_id
        self.config_name = config_name
        self.timestamp = timestamp
        self.note = note
        self.description = description
        self.session_id = session_id


class BackupSession:
    def __init__(self, session_id: str, timestamp: str, note: str, config_names: list[str]):
        self.session_id = session_id
        self.timestamp = timestamp
        self.note = note
        self.config_names = config_names

    @property
    def total_count(self) -> int:
        return len(self.config_names)


def build_sessions_from_meta(metas: Iterable[dict]) -> list[BackupSession]:
    session_map: dict[str, dict] = {}
    for meta in metas:
        sid = meta.get("session_id", meta["backup_id"])
        if sid not in session_map:
            session_map[sid] = {
                "session_id": sid,
                "timestamp": meta["timestamp"],
                "note": meta.get("note", ""),
                "config_names": [],
            }
        cfg_name = meta.get("config_name", "")
        if cfg_name not in session_map[sid]["config_names"]:
            session_map[sid]["config_names"].append(cfg_name)
    sessions = []
    for s in sorted(session_map.values(), key=lambda x: x["timestamp"], reverse=True):
        sessions.append(BackupSession(
            session_id=s["session_id"],
            timestamp=s["timestamp"],
            note=s["note"],
            config_names=s["config_names"],
        ))
    return sessions


class StorageBackend(ABC):
    @abstractmethod
    def save(self, backup_id: str, config_name: str, files: dict[str, Path], note: str, description: str,
             session_id: str = "") -> BackupResult:
        ...

    @abstractmethod
    def list_versions(self, config_name: str) -> list[BackupVersion]:
        ...

    @abstractmethod
    def list_sessions(self) -> list[BackupSession]:
        ...

    @abstractmethod
    def restore(self, config_name: str, backup_id: str, target_dir: Optional[Path] = None) -> RestoreResult:
        ...

    @abstractmethod
    def get_files(self, config_name: str, backup_id: str) -> dict[str, Path]:
        ...

    @abstractmethod
    def delete_version(self, config_name: str, backup_id: str) -> bool:
        ...
