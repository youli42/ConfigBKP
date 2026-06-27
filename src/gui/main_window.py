from pathlib import Path
from PySide6.QtWidgets import QMainWindow, QTabWidget, QMessageBox
from src.gui.home_tab import HomeTab
from src.gui.config_tab import ConfigTab
from src.gui.settings_tab import SettingsTab
from src.storage.local import LocalStorage


CONFIG_DIR = Path(__file__).resolve().parent.parent.parent / "config" / "builtin"
USER_CONFIG_DIR = Path(__file__).resolve().parent.parent.parent / "config" / "user"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("WinConfigBKP - Windows 配置文件备份工具")
        self.setMinimumSize(900, 650)

        USER_CONFIG_DIR.mkdir(parents=True, exist_ok=True)

        self.storage = LocalStorage(Path.home() / "WinConfigBKP_backups")

        self.tabs = QTabWidget()
        self.home_tab = HomeTab(CONFIG_DIR, USER_CONFIG_DIR, self.storage)
        self.config_tab = ConfigTab(CONFIG_DIR, USER_CONFIG_DIR)
        self.settings_tab = SettingsTab(self.storage)

        self.tabs.addTab(self.home_tab, "备份/恢复")
        self.tabs.addTab(self.config_tab, "规则管理")
        self.tabs.addTab(self.settings_tab, "设置")

        self.setCentralWidget(self.tabs)

        self.tabs.currentChanged.connect(self._on_tab_changed)

    def _on_tab_changed(self, index: int):
        if index == 1:
            self.config_tab.refresh_rules()
        elif index == 0:
            self.home_tab.refresh_configs()
