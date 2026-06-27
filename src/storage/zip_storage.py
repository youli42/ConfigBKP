import json
import zipfile
import shutil
from pathlib import Path
from typing import Optional
from datetime import datetime, timezone
from src.storage.base import StorageBackend, BackupResult, RestoreResult, BackupVersion, BackupSession
import tempfile


def _read_meta_from_zip(zip_path: Path) -> dict:
    with zipfile.ZipFile(zip_path) as zf:
        return json.loads(zf.read(".metadata.json"))


class ZipStorage(StorageBackend):
    def __init__(self, archive_dir: Path):
        self.archive_dir = archive_dir
        self._temp_dir: Optional[Path] = None

    def _zip_path(self, config_name: str, backup_id: str) -> Path:
        return self.archive_dir / config_name / f"{backup_id}.zip"

    def _ensure_temp(self) -> Path:
        if self._temp_dir is None:
            self._temp_dir = Path(tempfile.mkdtemp(prefix="winbkp_"))
        return self._temp_dir

    def save(self, backup_id: str, config_name: str, files: dict[str, Path], note: str, description: str,
             session_id: str = "") -> BackupResult:
        zip_path = self._zip_path(config_name, backup_id)
        zip_path.parent.mkdir(parents=True, exist_ok=True)
        total_size = 0
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for rel_path, src_path in files.items():
                zf.write(src_path, rel_path)
                total_size += src_path.stat().st_size
            metadata = {
                "backup_id": backup_id,
                "config_name": config_name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "note": note,
                "description": description,
                "session_id": session_id,
            }
            zf.writestr(".metadata.json", json.dumps(metadata, indent=2, ensure_ascii=False))
        return BackupResult(backup_id, config_name, len(files), total_size, note, session_id)

    def list_versions(self, config_name: str) -> list[BackupVersion]:
        cfg_dir = self.archive_dir / config_name
        if not cfg_dir.exists():
            return []
        versions = []
        for zip_file in sorted(cfg_dir.glob("*.zip"), reverse=True):
            meta = _read_meta_from_zip(zip_file)
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
        session_map: dict[str, dict] = {}
        if not self.archive_dir.exists():
            return []
        for cfg_entry in sorted(self.archive_dir.iterdir()):
            if not cfg_entry.is_dir():
                continue
            config_name = cfg_entry.name
            for zip_file in sorted(cfg_entry.glob("*.zip"), reverse=True):
                try:
                    meta = _read_meta_from_zip(zip_file)
                except Exception:
                    continue
                sid = meta.get("session_id", meta["backup_id"])
                if sid not in session_map:
                    session_map[sid] = {
                        "session_id": sid,
                        "timestamp": meta["timestamp"],
                        "note": meta.get("note", ""),
                        "config_names": [],
                    }
                cfg_name = meta.get("config_name", config_name)
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

    def restore(self, config_name: str, backup_id: str, target_dir: Optional[Path] = None) -> RestoreResult:
        zip_path = self._zip_path(config_name, backup_id)
        if not zip_path.exists():
            raise FileNotFoundError(f"Backup {backup_id} not found")
        restored = []
        extract_dir = self._ensure_temp() / backup_id
        extract_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(extract_dir)
        for item in extract_dir.rglob("*"):
            if item.is_file() and item.name != ".metadata.json":
                rel = item.relative_to(extract_dir)
                if target_dir:
                    dst = target_dir / rel
                else:
                    dst = rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, dst)
                restored.append(dst)
        shutil.rmtree(extract_dir, ignore_errors=True)
        return RestoreResult(config_name, restored, [])

    def get_files(self, config_name: str, backup_id: str) -> dict[str, Path]:
        zip_path = self._zip_path(config_name, backup_id)
        if not zip_path.exists():
            return {}
        extract_dir = self._ensure_temp() / backup_id
        extract_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(extract_dir)
        files = {}
        for item in extract_dir.rglob("*"):
            if item.is_file() and item.name != ".metadata.json":
                rel = str(item.relative_to(extract_dir))
                files[rel] = item
        return files

    def delete_version(self, config_name: str, backup_id: str) -> bool:
        zip_path = self._zip_path(config_name, backup_id)
        if zip_path.exists():
            zip_path.unlink()
            return True
        return False

    def cleanup(self):
        if self._temp_dir and self._temp_dir.exists():
            shutil.rmtree(self._temp_dir, ignore_errors=True)
