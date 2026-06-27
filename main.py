import ctypes
import sys
import os
import logging
import argparse
import subprocess

from PySide6.QtWidgets import QApplication
from src.gui.main_window import MainWindow


logging.basicConfig(
    level=logging.DEBUG if os.environ.get("WINCONFIGBKP_DEBUG") else logging.INFO,
    format="[%(levelname)s] %(message)s",
    stream=sys.stderr,
)

logger = logging.getLogger(__name__)


def is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except AttributeError:
        return True


def run_silent_backup():
    logger.info("静默备份模式（--silent-backup）")
    from src.utils.app_path import get_config_dir, get_default_backup_dir
    from src.storage.local import LocalStorage
    from src.core.backup_engine import BatchBackupWorker, BatchBackupSignals, BackupSummary
    from src.core.config_parser import load_config
    from src.utils.path_expander import expand
    from pathlib import Path

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
            files = {}
            for p in cfg.get("paths", []):
                expanded = expand(p)
                if expanded.exists():
                    if expanded.is_file():
                        files[expanded.name] = expanded
                    elif expanded.is_dir():
                        for f in expanded.rglob("*"):
                            if f.is_file():
                                rel = str(f.relative_to(expanded.parent))
                                files[rel] = f
            items.append((cfg, files))

    import tempfile
    from PySide6.QtCore import QCoreApplication
    app = QCoreApplication(sys.argv)
    signals = BatchBackupSignals()
    results = []

    def on_done(summary: BackupSummary):
        results.append(summary)
        app.quit()

    signals.done.connect(on_done)
    worker = BatchBackupWorker(items, storage, get_default_backup_dir(), "", signals)
    from PySide6.QtCore import QThreadPool
    QThreadPool().start(worker)
    app.exec()

    if results:
        s = results[0]
        logger.info("备份完成: %d 成功, %d 跳过, %d 失败",
                    len(s.results), len(s.skipped), len(s.errors))
    else:
        logger.warning("备份未执行")


def main():
    parser = argparse.ArgumentParser(description="WinConfigBKP - Windows 配置文件备份工具")
    parser.add_argument("--silent-backup", action="store_true", help="静默备份模式（无 GUI）")
    args, _ = parser.parse_known_args()

    if args.silent_backup:
        run_silent_backup()
        return

    if not is_admin():
        cmd = subprocess.list2cmdline(sys.argv)
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, cmd, None, 1
        )
        sys.exit()

    app = QApplication(sys.argv)
    app.setApplicationName("WinConfigBKP")
    app.setOrganizationName("WinConfigBKP")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
