import shutil
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime, timezone

from PySide6.QtCore import QObject, QRunnable, Signal

from src.storage.base import StorageBackend, RestoreResult
from src.utils.file_locker import is_file_locked, schedule_reboot_replace, get_locked_processes


logger = logging.getLogger(__name__)


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
                logger.debug("[%s] 备份未找到: %s", config_name, self.backup_id)
                self.signals.error.emit(f"未找到备份: {self.backup_id}")
                return

            logger.debug("[%s] 从备份 %s 读取到 %d 文件", config_name, self.backup_id, len(backup_files))

            import tempfile
            backup_dir = Path(tempfile.mkdtemp(prefix="restore_undo_"))

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
                if dst and self.restore_dir:
                    resolved = dst.resolve()
                    base = self.restore_dir.resolve()
                    if base not in resolved.parents and resolved != base:
                        self.signals.error.emit(f"路径越界: {rel_path}")
                        return
                src_files[rel_path] = (src_path, dst)

            if locked_files:
                procs = set()
                for f in locked_files:
                    procs.update(get_locked_processes(f))
                logger.debug("[%s] %d 文件被占用: %s", config_name, len(locked_files), procs)
                shutil.rmtree(backup_dir, ignore_errors=True)
                self.signals.file_blocked.emit(
                    f"{len(locked_files)} 个文件被占用",
                    list(procs),
                )
                return

            self.signals.message.emit("恢复前正在备份当前文件...")
            self.signals.progress.emit(50)

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
                logger.debug("[%s] %d 文件恢复失败", config_name, len(failed))
                shutil.rmtree(backup_dir, ignore_errors=True)
                self.signals.error.emit(f"部分文件恢复失败: {len(failed)} 个")
                return

            shutil.rmtree(backup_dir, ignore_errors=True)
            logger.debug("[%s] 恢复完成，%d 文件", config_name, len(restored))
            self.signals.progress.emit(100)
            self.signals.message.emit("恢复完成")
            self.signals.done.emit(RestoreResult(config_name, restored, []))

        except Exception as e:
            logger.debug("[%s] 恢复异常: %s", self.config.get("name", "?"), e)
            self.signals.error.emit(str(e))
