from PySide6.QtWidgets import QMainWindow, QTabWidget
from src.gui.home_tab import HomeTab
from src.gui.config_tab import ConfigTab
from src.gui.settings_tab import SettingsTab
from src.storage.local import LocalStorage
from src.utils.app_path import get_config_dir, get_default_backup_dir


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("WinConfigBKP - Windows 配置文件备份工具")
        self.setMinimumSize(900, 650)

        config_dir = get_config_dir()
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "user").mkdir(parents=True, exist_ok=True)

        backup_dir = get_default_backup_dir()
        backup_dir.mkdir(parents=True, exist_ok=True)
        self.storage = LocalStorage(backup_dir)

        self.tabs = QTabWidget()
        self.home_tab = HomeTab(config_dir, self.storage)
        self.config_tab = ConfigTab(config_dir)
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
