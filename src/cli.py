import sys
import logging
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QThreadPool

from src.utils.app_path import get_config_dir, get_default_backup_dir
from src.storage.local import LocalStorage
from src.core.backup_engine import BatchBackupWorker, BatchBackupSignals, BackupSummary
from src.core.config_parser import load_config
from src.utils.file_utils import collect_files, filter_ignored


logger = logging.getLogger(__name__)


def run_silent_backup():
    logger.info("静默备份模式（--silent-backup）")
    config_dirs = [get_config_dir() / "builtin", get_config_dir() / "user"]
    storage = LocalStorage(get_default_backup_dir())
    items = []
    for cfg_dir in config_dirs:
        if not cfg_dir.exists():
            continue
        for fpath in sorted(cfg_dir.glob("*.jsonc")):
            try:
                cfg = load_config(fpath)
            except Exception:
                continue
            if not cfg.get("enabled", True):
                continue
            files = collect_files(cfg.get("paths", []))
            patterns = cfg.get("strategy", {}).get("ignore_patterns", [])
            files = filter_ignored(files, patterns)
            items.append((cfg, files))

    app = QCoreApplication(sys.argv)
    signals = BatchBackupSignals()
    results = []

    def on_done(summary: BackupSummary):
        results.append(summary)
        app.quit()

    signals.done.connect(on_done)
    worker = BatchBackupWorker(items, storage, get_default_backup_dir(), "", signals)
    QThreadPool().start(worker)
    app.exec()

    if results:
        s = results[0]
        logger.info("备份完成: %d 成功, %d 跳过, %d 失败",
                    len(s.results), len(s.skipped), len(s.errors))
    else:
        logger.warning("备份未执行")
