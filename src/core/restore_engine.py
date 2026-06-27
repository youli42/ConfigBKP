import shutil
from pathlib import Path
from typing import Optional
from datetime import datetime, timezone

from PySide6.QtCore import QObject, QRunnable, Signal

from src.storage.base import StorageBackend, RestoreResult
from src.utils.file_locker import is_file_locked, schedule_reboot_replace, get_locked_processes


class RestoreSignals(QObject):
    progress = Signal(int)
    message = Signal(str)
    done = Signal(object)
    error = Signal(str)
    file_blocked = Signal(str, list)


class RestoreWorker(QRunnable):
    def __init__(self, config: dict, storage: StorageBackend, backup_id: str,
                 restore_dir: Optional[Path], signals: RestoreSignals):
        super().__init__()
        self.config = config
        self.storage = storage
        self.backup_id = backup_id
        self.restore_dir = restore_dir
        self.signals = signals

    def run(self):
        try:
            config_name = self.config["name"]

            self.signals.message.emit("正在读取备份文件...")
            self.signals.progress.emit(10)

            backup_files = self.storage.get_files(config_name, self.backup_id)
            if not backup_files:
                self.signals.error.emit(f"未找到备份: {self.backup_id}")
                return

            self.signals.message.emit("正在检测文件占用...")
            self.signals.progress.emit(30)

            locked_files: list[Path] = []
            original_paths: dict[str, Path] = {}
            cfg_paths = self.config.get("paths", [])

            from src.utils.path_expander import expand
            for rel_path in backup_files:
                for cfg_path_str in cfg_paths:
                    cfg_path = expand(cfg_path_str)
                    if cfg_path.name == Path(rel_path).name or str(Path(rel_path).parent) == "":
                        dst = cfg_path if not self.restore_dir else self.restore_dir / rel_path
                        original_paths[rel_path] = dst
                        break
                else:
                    if self.restore_dir:
                        original_paths[rel_path] = self.restore_dir / rel_path
                    else:
                        original_paths[rel_path] = Path(rel_path)

            src_files = {}
            for rel_path, src_path in backup_files.items():
                dst = original_paths.get(rel_path)
                if dst and is_file_locked(dst):
                    locked_files.append(dst)
                src_files[rel_path] = (src_path, dst)

            if locked_files:
                procs = set()
                for f in locked_files:
                    procs.update(get_locked_processes(f))
                self.signals.file_blocked.emit(
                    f"{len(locked_files)} 个文件被占用",
                    list(procs),
                )
                return

            self.signals.message.emit("恢复前正在备份当前文件...")
            self.signals.progress.emit(50)

            backup_dir = Path(f"restore_undo_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}")
            backup_dir.mkdir(exist_ok=True)
            for _, (_, dst) in src_files.items():
                if dst and dst.exists():
                    undo_path = backup_dir / dst.name
                    shutil.copy2(dst, undo_path)

            self.signals.message.emit("正在恢复文件...")
            self.signals.progress.emit(70)

            restored = []
            failed = []
            for rel_path, (src_path, dst) in src_files.items():
                try:
                    if dst:
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(src_path, dst)
                        restored.append(dst)
                except Exception as e:
                    failed.append((dst, str(e)))

            if failed:
                self.signals.error.emit(f"部分文件恢复失败: {len(failed)} 个")
                return

            self.signals.progress.emit(100)
            self.signals.message.emit("恢复完成")
            self.signals.done.emit(RestoreResult(config_name, restored, []))

        except Exception as e:
            self.signals.error.emit(str(e))
