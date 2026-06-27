from pathlib import Path
import subprocess

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QCheckBox, QSpinBox, QComboBox, QPushButton, QTimeEdit,
    QFileDialog, QLineEdit, QMessageBox, QFormLayout,
)
from PySide6.QtCore import QTime
from src.storage.base import StorageBackend


class SettingsTab(QWidget):
    def __init__(self, storage: StorageBackend):
        super().__init__()
        self.storage = storage
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        scheduler_group = QGroupBox("定时备份")
        sched_layout = QFormLayout(scheduler_group)

        self.sched_enabled = QCheckBox("开启每日备份")
        sched_layout.addRow(self.sched_enabled)

        self.sched_time = QTimeEdit(QTime(22, 0))
        self.sched_time.setDisplayFormat("HH:mm")
        sched_layout.addRow("备份时间:", self.sched_time)

        self.sched_target = QLineEdit(str(self.storage.base_dir))
        self.sched_browse = QPushButton("浏览...")
        target_row = QHBoxLayout()
        target_row.addWidget(self.sched_target)
        target_row.addWidget(self.sched_browse)
        sched_layout.addRow("备份目标:", target_row)

        self.sched_apply = QPushButton("应用定时设置")
        sched_layout.addRow(self.sched_apply)

        layout.addWidget(scheduler_group)

        version_group = QGroupBox("版本策略")
        ver_layout = QFormLayout(version_group)

        self.max_versions = QSpinBox()
        self.max_versions.setMinimum(1)
        self.max_versions.setMaximum(99)
        self.max_versions.setValue(10)
        ver_layout.addRow("最大保留版本数:", self.max_versions)

        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems(["增量备份", "全量备份"])
        ver_layout.addRow("备份策略:", self.strategy_combo)

        layout.addWidget(version_group)

        restore_group = QGroupBox("恢复设置")
        rest_layout = QFormLayout(restore_group)

        self.undo_backup = QCheckBox("恢复前备份当前文件到临时目录")
        self.undo_backup.setChecked(True)
        rest_layout.addRow(self.undo_backup)

        self.reboot_replace_btn = QPushButton("注册重启时替换 (适用于被锁文件)")
        rest_layout.addRow(self.reboot_replace_btn)

        layout.addWidget(restore_group)

        about_group = QGroupBox("关于")
        about_layout = QVBoxLayout(about_group)
        about_layout.addWidget(QLabel("WinConfigBKP v1.0.0"))
        about_layout.addWidget(QLabel("Windows 配置文件备份工具"))
        about_layout.addWidget(QLabel(f"备份目录: {self.storage.base_dir}"))
        layout.addWidget(about_group)

        layout.addStretch()

        self.sched_enabled.toggled.connect(self._on_sched_toggle)
        self.sched_apply.clicked.connect(self._apply_scheduler)
        self.sched_browse.clicked.connect(self._browse_sched_target)
        self.reboot_replace_btn.clicked.connect(self._reboot_replace)

    def _browse_sched_target(self):
        folder = QFileDialog.getExistingDirectory(self, "选择备份目标目录")
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
            QMessageBox.information(self, "成功", f"每日备份任务已注册，时间: {time_str}")
        except subprocess.CalledProcessError as e:
            QMessageBox.critical(self, "失败", f"注册任务失败:\n{e.stderr}")

    def _unregister_task(self):
        task_name = "WinConfigBKP_DailyBackup"
        try:
            subprocess.run(
                ["schtasks.exe", "/Delete", "/F", "/TN", task_name],
                check=True, capture_output=True, text=True,
            )
            QMessageBox.information(self, "成功", "已取消定时备份任务")
        except subprocess.CalledProcessError:
            pass

    def _reboot_replace(self):
        from src.utils.file_locker import schedule_reboot_replace
        QMessageBox.information(
            self, "重启时替换",
            "此功能需要在恢复时选择「重启时替换」才会生效。\n"
            "当文件被程序占用时，系统将在下次重启前自动完成替换。"
        )
