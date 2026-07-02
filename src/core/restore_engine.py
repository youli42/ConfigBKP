import shutil
import tempfile
import logging
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, QRunnable, Signal

from src.storage.base import StorageBackend, RestoreResult
from src.utils.file_locker import is_file_locked, get_locked_processes
from src.core.config_parser import resolve_path_for_platform
from src.utils.i18n import tr


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

    def _resolve_target_paths(self, backup_files: dict, source_types: dict) -> dict[str, Path]:
        original_paths: dict[str, Path] = {}
        cfg_paths = resolve_path_for_platform(self.config, "paths")
        cfg_data_paths = resolve_path_for_platform(self.config, "data_paths")
        from src.utils.path_expander import expand
        for rel_path in backup_files:
            st = source_types.get(rel_path, "config")
            candidates = cfg_data_paths if st == "data" else cfg_paths
            matched = False
            for cfg_path_str in candidates:
                cfg_path = expand(cfg_path_str)
                if cfg_path.name == Path(rel_path).name or str(Path(rel_path).parent) == "":
                    dst = cfg_path if not self.restore_dir else self.restore_dir / rel_path
                    original_paths[rel_path] = dst
                    matched = True
                    break
            if not matched:
                if self.restore_dir:
                    original_paths[rel_path] = self.restore_dir / rel_path
                else:
                    original_paths[rel_path] = Path(rel_path)
        return original_paths

    def run(self):
        config_name = self.config["name"]

        # Phase 1: 读取备份文件
        self.signals.message.emit(tr("正在读取备份文件..."))
        self.signals.progress.emit(10)
        backup_files = self.storage.get_files(config_name, self.backup_id)
        if not backup_files:
            logger.debug("[%s] 备份未找到: %s", config_name, self.backup_id)
            self.signals.error.emit(tr("未找到备份: {}").format(self.backup_id))
            return
        logger.debug("[%s] 从备份 %s 读取到 %d 文件", config_name, self.backup_id, len(backup_files))
        backup_dir = Path(tempfile.mkdtemp(prefix="restore_undo_"))

        # Phase 2: 解析目标路径
        self.signals.message.emit(tr("正在检测文件占用..."))
        self.signals.progress.emit(30)
        meta = self.storage.read_meta(config_name, self.backup_id)
        source_types: dict[str, str] = meta.get("source_types", {})
        try:
            original_paths = self._resolve_target_paths(backup_files, source_types)
        except Exception as e:
            shutil.rmtree(backup_dir, ignore_errors=True)
            logger.debug("[%s] 路径解析失败: %s", config_name, e)
            self.signals.error.emit(str(e))
            return

        # Phase 3: 检测文件占用
        src_files = {}
        locked_files = []
        for rel_path, src_path in backup_files.items():
            dst = original_paths.get(rel_path)
            if dst and is_file_locked(dst):
                locked_files.append(dst)
            if dst and self.restore_dir:
                resolved = dst.resolve()
                base = self.restore_dir.resolve()
                if base not in resolved.parents and resolved != base:
                    shutil.rmtree(backup_dir, ignore_errors=True)
                    self.signals.error.emit(tr("路径越界: {}").format(rel_path))
                    return
            src_files[rel_path] = (src_path, dst)

        if locked_files:
            procs = set()
            for f in locked_files:
                procs.update(get_locked_processes(f))
            logger.debug("[%s] %d 文件被占用: %s", config_name, len(locked_files), procs)
            shutil.rmtree(backup_dir, ignore_errors=True)
            self.signals.file_blocked.emit(tr("{} 个文件被占用").format(len(locked_files)), list(procs))
            return

        # Phase 4: 执行恢复
        self.signals.message.emit(tr("恢复前正在备份当前文件..."))
        self.signals.progress.emit(50)
        for _, (_, dst) in src_files.items():
            if dst and dst.exists():
                shutil.copy2(dst, backup_dir / dst.name)

        self.signals.message.emit(tr("正在恢复文件..."))
        self.signals.progress.emit(70)
        restored = []
        try:
            for rel_path, (src_path, dst) in src_files.items():
                if dst:
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src_path, dst)
                    restored.append(dst)
        except Exception as e:
            shutil.rmtree(backup_dir, ignore_errors=True)
            self.signals.error.emit(tr("部分文件恢复失败: {}").format(e))
            return

        shutil.rmtree(backup_dir, ignore_errors=True)
        logger.debug("[%s] 恢复完成，%d 文件", config_name, len(restored))
        self.signals.progress.emit(100)
        self.signals.message.emit(tr("恢复完成"))
        self.signals.done.emit(RestoreResult(config_name, restored, []))
