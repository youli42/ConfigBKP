from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QCheckBox, QGroupBox, QLabel,
    QPushButton, QProgressBar, QTableWidget, QTableWidgetItem, QHeaderView,
    QTextEdit, QComboBox, QFileDialog, QMessageBox, QAbstractItemView,
    QSplitter, QFrame,
)
from PySide6.QtCore import Qt, QThreadPool

from src.core.config_parser import load_config, filter_by_platform, generate_description
from src.core.backup_engine import BatchBackupWorker, BatchBackupSignals, BackupSummary
from src.core.restore_engine import RestoreWorker, RestoreSignals
from src.storage.base import StorageBackend, BackupVersion
from src.utils.path_expander import expand


class HomeTab(QWidget):
    def __init__(self, config_dir: Path, storage: StorageBackend):
        super().__init__()
        self.config_dir = config_dir
        self.storage = storage
        self.threadpool = QThreadPool()
        self._configs: dict[str, dict] = {}
        self._checkboxes: dict[str, QCheckBox] = {}
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        top_bar = QHBoxLayout()
        self.scan_btn = QPushButton("扫描本机已装软件")
        self.select_all_btn = QPushButton("全选")
        self.deselect_all_btn = QPushButton("取消全选")
        top_bar.addWidget(self.scan_btn)
        top_bar.addWidget(self.select_all_btn)
        top_bar.addWidget(self.deselect_all_btn)
        top_bar.addStretch()
        layout.addLayout(top_bar)

        splitter = QSplitter(Qt.Orientation.Vertical)

        upper = QWidget()
        upper_layout = QHBoxLayout(upper)
        upper_layout.setContentsMargins(0, 0, 0, 0)

        left_group = QGroupBox("配置规则")
        left_layout = QVBoxLayout(left_group)
        self.config_list = QWidget()
        self.config_list_layout = QVBoxLayout(self.config_list)
        self.config_list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll_area = QWidget()
        scroll_layout = QVBoxLayout(scroll_area)
        scroll_layout.addWidget(self.config_list)
        scroll_layout.addStretch()
        left_layout.addWidget(scroll_area)
        upper_layout.addWidget(left_group)

        right_group = QGroupBox("操作")
        right_layout = QVBoxLayout(right_group)

        self.note_input = QTextEdit()
        self.note_input.setPlaceholderText("备份备注（可选）")
        self.note_input.setMaximumHeight(60)
        right_layout.addWidget(QLabel("备注:"))
        right_layout.addWidget(self.note_input)

        target_layout = QHBoxLayout()
        target_layout.addWidget(QLabel("备份目标:"))
        self.target_combo = QComboBox()
        self.target_combo.addItems(["本地目录", "ZIP 打包"])
        self.target_browse_btn = QPushButton("浏览...")
        self.target_path_label = QLabel(str(self.storage.base_dir))
        target_layout.addWidget(self.target_combo)
        target_layout.addWidget(self.target_browse_btn)
        target_layout.addWidget(self.target_path_label)
        target_layout.addStretch()
        right_layout.addLayout(target_layout)

        btn_layout = QHBoxLayout()
        self.backup_btn = QPushButton("备份")
        self.backup_btn.setStyleSheet("background-color: #2196F3; color: white; padding: 8px 24px;")
        self.restore_btn = QPushButton("恢复")
        self.restore_btn.setStyleSheet("background-color: #FF5722; color: white; padding: 8px 24px;")
        btn_layout.addWidget(self.backup_btn)
        btn_layout.addWidget(self.restore_btn)
        btn_layout.addStretch()
        right_layout.addLayout(btn_layout)

        self.progress_bar = QProgressBar()
        right_layout.addWidget(self.progress_bar)

        self.status_label = QLabel("就绪")
        right_layout.addWidget(self.status_label)

        upper_layout.addWidget(right_group)
        splitter.addWidget(upper)

        bottom_group = QGroupBox("备份历史")
        bottom_layout = QVBoxLayout(bottom_group)
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(5)
        self.history_table.setHorizontalHeaderLabels(["时间", "配置", "描述", "备注", ""])
        self.history_table.horizontalHeader().setStretchLastSection(True)
        self.history_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.history_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.history_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        bottom_layout.addWidget(self.history_table)
        splitter.addWidget(bottom_group)

        layout.addWidget(splitter)

        self.scan_btn.clicked.connect(self._scan)
        self.select_all_btn.clicked.connect(self._select_all)
        self.deselect_all_btn.clicked.connect(self._deselect_all)
        self.backup_btn.clicked.connect(self._backup)
        self.restore_btn.clicked.connect(self._restore)
        self.target_browse_btn.clicked.connect(self._browse_target)

        self.refresh_configs()

    def refresh_configs(self):
        self._configs.clear()
        for child in reversed(self.config_list.findChildren(QWidget)):
            child.setParent(None)
            child.deleteLater()
        self._checkboxes.clear()

        for sub in ["builtin", "user"]:
            sub_dir = self.config_dir / sub
            if not sub_dir.exists():
                continue
            for fpath in sorted(sub_dir.glob("*.jsonc")):
                try:
                    cfg = load_config(fpath)
                except Exception:
                    continue
                if not cfg.get("enabled", True):
                    continue
                name = cfg.get("name", fpath.stem)
                self._configs[name] = cfg
                cb = QCheckBox(name)
                self._checkboxes[name] = cb
                desc = cfg.get("description", "")
                if desc:
                    cb.setToolTip(desc)
                self.config_list_layout.addWidget(cb)

        self.config_list_layout.addStretch()
        self._refresh_history()

    def _refresh_history(self, storage: Optional[StorageBackend] = None):
        self.history_table.setRowCount(0)
        seen: set[str] = set()
        all_versions: list[BackupVersion] = []
        s = storage or self.storage
        for name in self._configs:
            versions = s.list_versions(name)
            all_versions.extend(versions)
        all_versions.sort(key=lambda v: v.timestamp, reverse=True)
        for v in all_versions:
            row = self.history_table.rowCount()
            self.history_table.insertRow(row)
            self.history_table.setItem(row, 0, QTableWidgetItem(v.timestamp.replace("T", " ")[:19]))
            self.history_table.setItem(row, 1, QTableWidgetItem(v.config_name))
            self.history_table.setItem(row, 2, QTableWidgetItem(v.description[:80] if v.description else ""))
            self.history_table.setItem(row, 3, QTableWidgetItem(v.note))

    def _scan(self):
        from src.core.scanner import scan_installed
        matched = scan_installed([self.config_dir / "builtin", self.config_dir / "user"])
        for name, cb in self._checkboxes.items():
            cb.setChecked(name in matched)
        self.status_label.setText(f"扫描完成，匹配 {len(matched)} 条规则")

    def _select_all(self):
        for cb in self._checkboxes.values():
            cb.setChecked(True)

    def _deselect_all(self):
        for cb in self._checkboxes.values():
            cb.setChecked(False)

    def _browse_target(self):
        folder = QFileDialog.getExistingDirectory(self, "选择备份目标目录")
        if folder:
            self.target_path_label.setText(folder)

    def _get_selected_configs(self) -> list[dict]:
        selected = []
        for name, cb in self._checkboxes.items():
            if cb.isChecked():
                selected.append(self._configs[name])
        return selected

    def _backup(self):
        configs = self._get_selected_configs()
        if not configs:
            QMessageBox.warning(self, "提示", "请先选择要备份的配置")
            return

        self.backup_btn.setEnabled(False)
        self.restore_btn.setEnabled(False)
        self.progress_bar.setValue(0)

        target_type = self.target_combo.currentText()
        target_path_str = self.target_path_label.text()

        if target_type == "ZIP 打包":
            from src.storage.zip_storage import ZipStorage
            storage = ZipStorage(Path(target_path_str))
        else:
            from src.storage.local import LocalStorage
            storage = LocalStorage(Path(target_path_str))

        items = []
        note = self.note_input.toPlainText()
        for cfg in configs:
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
                else:
                    expanded_path = str(expanded)
                    if expanded_path not in str(files):
                        pass
            items.append((cfg, files))

        skipped = [cfg["name"] for cfg, files in items if not files]
        if skipped:
            reply = QMessageBox.question(
                self, "路径不存在",
                f"以下配置的源文件路径不存在，将被跳过：\n" + "\n".join(f"  • {n}" for n in skipped) +
                "\n\n是否继续备份其他配置？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                self.backup_btn.setEnabled(True)
                self.restore_btn.setEnabled(True)
                return

        signals = BatchBackupSignals()
        signals.progress.connect(self.progress_bar.setValue)
        signals.message.connect(self.status_label.setText)
        signals.done.connect(lambda summary: self._batch_backup_done(storage, summary))
        signals.error.connect(lambda msg: self._backup_error(msg))

        manifest_base_dir = Path(target_path_str)
        worker = BatchBackupWorker(items, storage, manifest_base_dir, note, signals)
        self.threadpool.start(worker)

    def _batch_backup_done(self, storage: StorageBackend, summary: BackupSummary):
        self.backup_btn.setEnabled(True)
        self.restore_btn.setEnabled(True)
        self.progress_bar.setValue(100)
        self._refresh_history(storage)
        parts = []
        if summary.results:
            total_files = sum(r.files_count for r in summary.results)
            parts.append(f"成功: {len(summary.results)} 个配置 ({total_files} 文件)")
        if summary.skipped:
            parts.append(f"跳过: {len(summary.skipped)} 个")
        if summary.errors:
            parts.append(f"失败: {len(summary.errors)} 个")
        msg = " | ".join(parts) if parts else "无任何操作"
        self.status_label.setText(f"备份完成: {msg}")
        lines = []
        if summary.results:
            lines.append("已备份:")
            for r in summary.results:
                lines.append(f"  ✓ {r.config_name} ({r.files_count} 文件)")
        if summary.skipped:
            lines.append("已跳过:")
            for name in summary.skipped:
                lines.append(f"  - {name}")
        if summary.errors:
            lines.append("失败:")
            for name, err in summary.errors:
                lines.append(f"  ✗ {name}: {err}")
        if lines:
            QMessageBox.information(self, "备份结果", "\n".join(lines))

    def _backup_error(self, msg: str):
        self.backup_btn.setEnabled(True)
        self.restore_btn.setEnabled(True)
        QMessageBox.critical(self, "备份失败", msg)

    def _restore(self):
        configs = self._get_selected_configs()
        if not configs:
            QMessageBox.warning(self, "提示", "请先选择要恢复的配置")
            return

        row = self.history_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "提示", "请先在历史记录中选择要恢复的版本")
            return

        backup_id = self.history_table.item(row, 0).text()
        config_name = self.history_table.item(row, 1).text()

        cfg = self._configs.get(config_name)
        if not cfg:
            QMessageBox.critical(self, "错误", f"未找到配置规则: {config_name}")
            return

        reply = QMessageBox.question(
            self, "确认恢复",
            f"确定要将 {config_name} 恢复到备份版本 {backup_id} 吗？\n"
            "当前文件将在恢复前备份到撤销目录。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self.backup_btn.setEnabled(False)
        self.restore_btn.setEnabled(False)
        self.progress_bar.setValue(0)

        signals = RestoreSignals()
        signals.progress.connect(self.progress_bar.setValue)
        signals.message.connect(self.status_label.setText)
        signals.done.connect(lambda result: self._restore_done(result))
        signals.error.connect(lambda msg: self._restore_error(msg))
        signals.file_blocked.connect(lambda msg, procs: self._handle_blocked(msg, procs))

        worker = RestoreWorker(cfg, self.storage, backup_id, None, signals)
        self.threadpool.start(worker)

    def _restore_done(self, result):
        self.backup_btn.setEnabled(True)
        self.restore_btn.setEnabled(True)
        self.status_label.setText(f"恢复完成，已恢复 {len(result.files_restored)} 个文件")
        QMessageBox.information(self, "恢复完成", f"已成功恢复 {len(result.files_restored)} 个文件")

    def _restore_error(self, msg: str):
        self.backup_btn.setEnabled(True)
        self.restore_btn.setEnabled(True)
        QMessageBox.critical(self, "恢复失败", msg)

    def _handle_blocked(self, msg: str, procs: list[str]):
        self.backup_btn.setEnabled(True)
        self.restore_btn.setEnabled(True)
        proc_text = "\n".join(f"  • {p}" for p in procs)
        QMessageBox.warning(
            self, "文件被占用",
            f"{msg}\n请关闭以下程序后重试：\n{proc_text}\n\n或使用设置中的「重启时替换」功能。"
        )
