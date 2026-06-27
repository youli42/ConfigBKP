import shutil
import json
from pathlib import Path
from typing import Optional
from datetime import datetime, timezone
from src.storage.base import StorageBackend, BackupResult, RestoreResult, BackupVersion, BackupSession
from src.storage._utils import build_sessions_from_meta


def _read_meta(meta_path: Path) -> dict:
    with open(meta_path, encoding="utf-8") as f:
        return json.load(f)


class LocalStorage(StorageBackend):
    def __init__(self, base_dir: Path):
        self._storage_base_dir = base_dir

    @property
    def base_dir(self) -> Path:
        return self._storage_base_dir

    def _config_dir(self, config_name: str) -> Path:
        return self.base_dir / config_name

    def _version_dir(self, config_name: str, backup_id: str) -> Path:
        return self._config_dir(config_name) / backup_id

    def _meta_path(self, config_name: str, backup_id: str) -> Path:
        return self._version_dir(config_name, backup_id) / ".metadata.json"

    def save(self, backup_id: str, config_name: str, files: dict[str, Path], note: str, description: str,
             session_id: str = "") -> BackupResult:
        ver_dir = self._version_dir(config_name, backup_id)
        ver_dir.mkdir(parents=True, exist_ok=True)
        total_size = 0
        for rel_path, src_path in files.items():
            dst = ver_dir / rel_path
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_path, dst)
            total_size += dst.stat().st_size
        metadata = {
            "backup_id": backup_id,
            "config_name": config_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "note": note,
            "description": description,
            "session_id": session_id,
        }
        with open(self._meta_path(config_name, backup_id), "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        return BackupResult(backup_id, config_name, len(files), total_size, note, session_id)

    def list_versions(self, config_name: str) -> list[BackupVersion]:
        cfg_dir = self._config_dir(config_name)
        if not cfg_dir.exists():
            return []
        versions = []
        for entry in sorted(cfg_dir.iterdir(), reverse=True):
            meta_path = entry / ".metadata.json"
            if not meta_path.exists():
                continue
            meta = _read_meta(meta_path)
            versions.append(BackupVersion(
                backup_id=meta["backup_id"],
                config_name=meta["config_name"],
                timestamp=meta["timestamp"],
                note=meta.get("note", ""),
                description=meta.get("description", ""),
                session_id=meta.get("session_id", meta["backup_id"]),
            ))
        return versions

    def list_sessions(self) -> list[BackupSession]:
        if not self.base_dir.exists():
            return []
        metas = []
        for cfg_entry in sorted(self.base_dir.iterdir()):
            if not cfg_entry.is_dir():
                continue
            config_name = cfg_entry.name
            for ver_entry in sorted(cfg_entry.iterdir(), reverse=True):
                meta_path = ver_entry / ".metadata.json"
                if not meta_path.exists():
                    continue
                meta = _read_meta(meta_path)
                meta.setdefault("config_name", config_name)
                metas.append(meta)
        return build_sessions_from_meta(metas)

    def restore(self, config_name: str, backup_id: str, target_dir: Optional[Path] = None) -> RestoreResult:
        ver_dir = self._version_dir(config_name, backup_id)
        if not ver_dir.exists():
            raise FileNotFoundError(f"Backup {backup_id} not found")
        restored = []
        for item in ver_dir.iterdir():
            if item.name == ".metadata.json":
                continue
            if target_dir:
                dst = target_dir / item.relative_to(ver_dir)
            else:
                dst = item
            dst.parent.mkdir(parents=True, exist_ok=True)
            if item.is_file():
                shutil.copy2(item, dst)
                restored.append(dst)
            elif item.is_dir():
                shutil.copytree(item, dst, dirs_exist_ok=True)
                restored.append(dst)
        return RestoreResult(config_name, restored, [])

    def get_files(self, config_name: str, backup_id: str) -> dict[str, Path]:
        ver_dir = self._version_dir(config_name, backup_id)
        if not ver_dir.exists():
            return {}
        files = {}
        for item in ver_dir.rglob("*"):
            if item.is_file() and item.name != ".metadata.json":
                rel = item.relative_to(ver_dir)
                files[str(rel)] = item
        return files

    def delete_version(self, config_name: str, backup_id: str) -> bool:
        ver_dir = self._version_dir(config_name, backup_id)
        if ver_dir.exists():
            shutil.rmtree(ver_dir)
            return True
        return False
