from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional


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


class StorageBackend(ABC):
    @property
    @abstractmethod
    def base_dir(self) -> Path:
        ...

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
