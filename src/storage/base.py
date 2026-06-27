from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional


class BackupResult:
    def __init__(self, backup_id: str, config_name: str, files_count: int, total_size: int, note: str = ""):
        self.backup_id = backup_id
        self.config_name = config_name
        self.files_count = files_count
        self.total_size = total_size
        self.note = note


class RestoreResult:
    def __init__(self, config_name: str, files_restored: list[Path], files_pending: list[Path]):
        self.config_name = config_name
        self.files_restored = files_restored
        self.files_pending = files_pending


class BackupVersion:
    def __init__(self, backup_id: str, config_name: str, timestamp: str, note: str, description: str):
        self.backup_id = backup_id
        self.config_name = config_name
        self.timestamp = timestamp
        self.note = note
        self.description = description


class StorageBackend(ABC):
    @abstractmethod
    def save(self, backup_id: str, config_name: str, files: dict[str, Path], note: str, description: str) -> BackupResult:
        ...

    @abstractmethod
    def list_versions(self, config_name: str) -> list[BackupVersion]:
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
