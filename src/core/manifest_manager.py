import json
from pathlib import Path
from typing import Dict, Optional
from src.utils.file_hasher import file_info
from datetime import datetime, timezone


class ManifestManager:
    def __init__(self, storage_dir: Path):
        self.storage_dir = storage_dir
        self.manifest_path = storage_dir / "manifest.json"

    def load(self) -> dict:
        if not self.manifest_path.exists():
            return {"last_backup": None, "files": {}}
        with open(self.manifest_path, encoding="utf-8") as f:
            return json.load(f)

    def save(self, manifest: dict):
        manifest["last_backup"] = datetime.now(timezone.utc).isoformat()
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        with open(self.manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)

    def compute_changes(self, files: dict[str, Path]) -> tuple[list[Path], list[Path]]:
        manifest = self.load()
        prev_files: Dict[str, dict] = manifest.get("files", {})
        changed: list[Path] = []
        unchanged: list[Path] = []
        for rel_path, abs_path in files.items():
            prev = prev_files.get(rel_path)
            if not prev:
                changed.append(abs_path)
                continue
            current_info = file_info(abs_path)
            if current_info["sha256"] != prev.get("sha256"):
                changed.append(abs_path)
            else:
                unchanged.append(abs_path)
        return changed, unchanged

    def update_manifest(self, files: dict[str, Path], backup_id: str):
        manifest = self.load()
        new_files = {}
        for rel_path, abs_path in files.items():
            new_files[rel_path] = file_info(abs_path)
            new_files[rel_path]["backup_id"] = backup_id
        manifest["files"].update(new_files)
        self.save(manifest)

    def get_backup_ids(self) -> set[str]:
        manifest = self.load()
        ids: set[str] = set()
        for info in manifest.get("files", {}).values():
            bid = info.get("backup_id")
            if bid:
                ids.add(bid)
        return ids
