import ctypes
import sys
import os
import logging
import argparse
import subprocess

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QSettings
from src.gui.main_window import MainWindow
from src.cli import run_silent_backup
from src.utils.i18n import install as install_locale


logging.basicConfig(
    level=logging.DEBUG if os.environ.get("WINCONFIGBKP_DEBUG") else logging.INFO,
    format="[%(levelname)s] %(message)s",
    stream=sys.stderr,
)


def is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except AttributeError:
        return True


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

    settings = QSettings()
    locale = settings.value("language", "zh_CN")
    install_locale(locale)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
