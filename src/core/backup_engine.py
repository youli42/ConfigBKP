import json
import os
from pathlib import Path
from typing import Optional
from datetime import datetime, timezone
from PySide6.QtCore import QObject, QRunnable, Signal, Slot
from src.storage.base import StorageBackend, BackupResult
from src.core.manifest_manager import ManifestManager
from src.core.config_parser import generate_description
from src.utils.path_expander import expand


class BackupSignals(QObject):
    progress = Signal(int)
    message = Signal(str)
    done = Signal(object)
    error = Signal(str)


class BackupWorker(QRunnable):
    def __init__(self, config: dict, files: dict[str, Path], storage: StorageBackend,
                 manifest_dir: Path, note: str, signals: BackupSignals):
        super().__init__()
        self.config = config
        self.files = files
        self.storage = storage
        self.manifest_dir = manifest_dir
        self.note = note
        self.signals = signals

    def run(self):
        try:
            config_name = self.config["name"]
            backup_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")

            self.signals.message.emit("正在计算文件哈希...")
            self.signals.progress.emit(10)

            manifest_mgr = ManifestManager(self.manifest_dir)
            changed, _ = manifest_mgr.compute_changes(self.files)

            if not changed:
                self.signals.message.emit("无文件变化，跳过备份")
                self.signals.progress.emit(100)
                self.signals.done.emit(BackupResult(backup_id, config_name, 0, 0, self.note))
                return

            self.signals.message.emit(f"发现 {len(changed)} 个文件变化，正在备份...")
            self.signals.progress.emit(30)

            changed_files = {}
            for abs_path in changed:
                for rel_path, fp in self.files.items():
                    if fp == abs_path:
                        changed_files[rel_path] = fp
                        break

            description = generate_description(
                config_name, self.config, changed_files
            )

            self.signals.message.emit("正在写入备份...")
            self.signals.progress.emit(60)
            result = self.storage.save(
                backup_id=backup_id,
                config_name=config_name,
                files=changed_files,
                note=self.note,
                description=description,
            )

            manifest_mgr.update_manifest(changed_files, backup_id)

            self._prune_versions(config_name)

            self.signals.progress.emit(100)
            self.signals.message.emit("备份完成")
            self.signals.done.emit(result)

        except Exception as e:
            self.signals.error.emit(str(e))

    def _prune_versions(self, config_name: str):
        max_versions = self.config.get("strategy", {}).get("max_versions", 10)
        versions = self.storage.list_versions(config_name)
        if len(versions) > max_versions:
            for old in versions[max_versions:]:
                self.storage.delete_version(config_name, old.backup_id)


class BackupSummary:
    def __init__(self):
        self.results: list[BackupResult] = []
        self.skipped: list[str] = []
        self.errors: list[tuple[str, str]] = []

    @property
    def success_count(self) -> int:
        return len(self.results)

    @property
    def total_count(self) -> int:
        return self.success_count + len(self.skipped) + len(self.errors)


class BatchBackupSignals(QObject):
    progress = Signal(int)
    message = Signal(str)
    done = Signal(object)
    error = Signal(str)


class BatchBackupWorker(QRunnable):
    def __init__(self, items: list[tuple[dict, dict[str, Path]]],
                 storage: StorageBackend, manifest_base_dir: Path,
                 note: str, signals: BatchBackupSignals):
        super().__init__()
        self.items = items
        self.storage = storage
        self.manifest_base_dir = manifest_base_dir
        self.note = note
        self.signals = signals
        self._config_index: dict[str, dict] = {}

    def run(self):
        summary = BackupSummary()
        total = len(self.items)
        for idx, (cfg, files) in enumerate(self.items):
            name = cfg["name"]
            self._config_index[name] = cfg
            self.signals.message.emit(f"[{idx+1}/{total}] 正在处理 {name}...")
            try:
                if not files:
                    summary.skipped.append(name)
                    self.signals.message.emit(f"[{idx+1}/{total}] {name}: 无文件，已跳过")
                    self.signals.progress.emit(int((idx + 1) / total * 100))
                    continue
                backup_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
                manifest_dir = self.manifest_base_dir / name
                manifest_mgr = ManifestManager(manifest_dir)
                changed, _ = manifest_mgr.compute_changes(files)
                if not changed:
                    summary.skipped.append(name)
                    self.signals.message.emit(f"[{idx+1}/{total}] {name}: 无变化，已跳过")
                    self.signals.progress.emit(int((idx + 1) / total * 100))
                    continue
                changed_files = {rel: fp for rel, fp in files.items() if fp in changed}
                description = generate_description(name, cfg, changed_files)
                result = self.storage.save(
                    backup_id=backup_id, config_name=name,
                    files=changed_files, note=self.note, description=description,
                )
                manifest_mgr.update_manifest(changed_files, backup_id)
                self._prune_versions(name)
                summary.results.append(result)
                self.signals.message.emit(f"[{idx+1}/{total}] {name}: 备份完成 ({result.files_count} 文件)")
            except Exception as e:
                summary.errors.append((name, str(e)))
                self.signals.message.emit(f"[{idx+1}/{total}] {name}: 失败 - {e}")
            self.signals.progress.emit(int((idx + 1) / total * 100))
        self.signals.done.emit(summary)

    def _prune_versions(self, config_name: str):
        cfg = self._config_index.get(config_name, {})
        max_versions = cfg.get("strategy", {}).get("max_versions", 10)
        versions = self.storage.list_versions(config_name)
        if len(versions) > max_versions:
            for old in versions[max_versions:]:
                self.storage.delete_version(config_name, old.backup_id)
