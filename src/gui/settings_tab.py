from pathlib import Path
import subprocess

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QCheckBox, QSpinBox, QComboBox, QPushButton, QTimeEdit,
    QFileDialog, QLineEdit, QMessageBox, QFormLayout,
)
from PySide6.QtCore import QTime, QSettings
from PySide6.QtWidgets import QApplication
from src.storage.base import StorageBackend
from src.utils.i18n import tr, install as install_locale, on_locale_changed, off_locale_changed


class SettingsTab(QWidget):
    def __init__(self, storage: StorageBackend):
        super().__init__()
        self.storage = storage
        self._setup_ui()
        self.retranslate_ui()
        self._retranslate_cb = self.retranslate_ui
        on_locale_changed(self._retranslate_cb)
        self.destroyed.connect(self._on_destroy)

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        self.scheduler_group = QGroupBox()
        sched_layout = QFormLayout(self.scheduler_group)

        self.sched_enabled = QCheckBox()
        sched_layout.addRow(self.sched_enabled)

        self.sched_time = QTimeEdit(QTime(22, 0))
        self.sched_time.setDisplayFormat("HH:mm")
        self._sched_time_label = QLabel()
        sched_layout.addRow(self._sched_time_label, self.sched_time)

        self.sched_target = QLineEdit(str(self.storage.base_dir))
        self.sched_browse = QPushButton()
        target_row = QHBoxLayout()
        target_row.addWidget(self.sched_target)
        target_row.addWidget(self.sched_browse)
        self._sched_target_label = QLabel()
        sched_layout.addRow(self._sched_target_label, target_row)

        self.sched_apply = QPushButton()
        sched_layout.addRow(self.sched_apply)

        layout.addWidget(self.scheduler_group)

        self.version_group = QGroupBox()
        ver_layout = QFormLayout(self.version_group)

        self.max_versions = QSpinBox()
        self.max_versions.setMinimum(1)
        self.max_versions.setMaximum(99)
        self.max_versions.setValue(10)
        self._max_versions_label = QLabel()
        ver_layout.addRow(self._max_versions_label, self.max_versions)

        self.strategy_combo = QComboBox()
        self._strategy_label = QLabel()
        ver_layout.addRow(self._strategy_label, self.strategy_combo)

        layout.addWidget(self.version_group)

        self.restore_group = QGroupBox()
        rest_layout = QFormLayout(self.restore_group)

        self.undo_backup = QCheckBox()
        self.undo_backup.setChecked(True)
        rest_layout.addRow(self.undo_backup)

        self.reboot_replace_btn = QPushButton()
        rest_layout.addRow(self.reboot_replace_btn)

        layout.addWidget(self.restore_group)

        self.lang_group = QGroupBox()
        lang_layout = QFormLayout(self.lang_group)
        self.lang_combo = QComboBox()
        self.lang_combo.addItem("中文", "zh_CN")
        self.lang_combo.addItem("English", "en_US")
        settings = QSettings()
        current_lang = settings.value("language", "zh_CN")
        idx = self.lang_combo.findData(current_lang)
        if idx >= 0:
            self.lang_combo.setCurrentIndex(idx)
        self.lang_combo.currentIndexChanged.connect(self._switch_lang)
        self._lang_label = QLabel()
        lang_layout.addRow(self._lang_label, self.lang_combo)
        layout.addWidget(self.lang_group)

        self.about_group = QGroupBox()
        about_layout = QVBoxLayout(self.about_group)
        about_layout.addWidget(QLabel("WinConfigBKP v1.0.0"))
        self._about_desc_label = QLabel()
        about_layout.addWidget(self._about_desc_label)
        self._about_path_label = QLabel()
        about_layout.addWidget(self._about_path_label)
        layout.addWidget(self.about_group)

        layout.addStretch()

        self.sched_enabled.toggled.connect(self._on_sched_toggle)
        self.sched_apply.clicked.connect(self._apply_scheduler)
        self.sched_browse.clicked.connect(self._browse_sched_target)
        self.reboot_replace_btn.clicked.connect(self._reboot_replace)

    def retranslate_ui(self):
        self.scheduler_group.setTitle(tr("定时备份"))
        self.sched_enabled.setText(tr("开启每日备份"))
        self._sched_time_label.setText(tr("备份时间:"))
        self.sched_browse.setText(tr("浏览..."))
        self._sched_target_label.setText(tr("备份目标:"))
        self.sched_apply.setText(tr("应用定时设置"))

        self.version_group.setTitle(tr("版本策略"))
        self._max_versions_label.setText(tr("最大保留版本数:"))
        idx = self.strategy_combo.currentIndex()
        self.strategy_combo.clear()
        self.strategy_combo.addItems([tr("增量备份"), tr("全量备份")])
        if 0 <= idx < self.strategy_combo.count():
            self.strategy_combo.setCurrentIndex(idx)
        self._strategy_label.setText(tr("备份策略:"))

        self.restore_group.setTitle(tr("恢复设置"))
        self.undo_backup.setText(tr("恢复前备份当前文件到临时目录"))
        self.reboot_replace_btn.setText(tr("注册重启时替换 (适用于被锁文件)"))

        self.lang_group.setTitle(tr("语言"))
        self._lang_label.setText(tr("界面语言:"))

        self.about_group.setTitle(tr("关于"))
        self._about_desc_label.setText(tr("Windows 配置文件备份工具"))
        self._about_path_label.setText(tr("备份目录: {}").format(self.storage.base_dir))

    def _browse_sched_target(self):
        folder = QFileDialog.getExistingDirectory(self, tr("选择备份目标目录"))
        if folder:
            self.sched_target.setText(folder)

    def _on_sched_toggle(self, enabled: bool):
        self.sched_time.setEnabled(enabled)
        self.sched_target.setEnabled(enabled)
        self.sched_browse.setEnabled(enabled)
        self.sched_apply.setEnabled(enabled)

    def _apply_scheduler(self):
        if not self.sched_enabled.isChecked():
            self._unregister_task()
            return
        self._register_task()

    def _register_task(self):
        script = Path(__file__).resolve().parent.parent.parent / "main.py"
        time_str = self.sched_time.text()
        hour, minute = time_str.split(":")
        task_name = "WinConfigBKP_DailyBackup"
        cmd = [
            "schtasks.exe", "/Create", "/F",
            "/TN", task_name,
            "/SC", "DAILY",
            "/ST", f"{hour}:{minute}",
            "/TR", f'python "{script}" --silent-backup',
            "/RL", "HIGHEST",
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            QMessageBox.information(self, tr("成功"), tr("每日备份任务已注册，时间: {}").format(time_str))
        except subprocess.CalledProcessError as e:
            QMessageBox.critical(self, tr("失败"), tr("注册任务失败:\n{}").format(e.stderr))

    def _unregister_task(self):
        task_name = "WinConfigBKP_DailyBackup"
        try:
            subprocess.run(
                ["schtasks.exe", "/Delete", "/F", "/TN", task_name],
                check=True, capture_output=True, text=True,
            )
            QMessageBox.information(self, tr("成功"), tr("已取消定时备份任务"))
        except subprocess.CalledProcessError:
            pass

    def _on_destroy(self):
        off_locale_changed(self._retranslate_cb)

    def _switch_lang(self, idx: int):
        locale = self.lang_combo.itemData(idx)
        settings = QSettings()
        settings.setValue("language", locale)
        install_locale(locale)

    def _reboot_replace(self):
        from src.utils.file_locker import schedule_reboot_replace
        QMessageBox.information(
            self, tr("重启时替换"),
            tr("此功能需要在恢复时选择「重启时替换」才会生效。\n"
               "当文件被程序占用时，系统将在下次重启前自动完成替换。")
        )
