import ctypes
import sys
import os

from PySide6.QtWidgets import QApplication
from src.gui.main_window import MainWindow


def is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except AttributeError:
        return True


def main():
    if not is_admin():
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1
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
