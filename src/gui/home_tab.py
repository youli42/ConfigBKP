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
        self._backup_signals: BatchBackupSignals | None = None
        self._restore_signals: RestoreSignals | None = None
        self._is_restoring = False
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
        history_splitter = QSplitter(Qt.Orientation.Horizontal)

        self.session_table = QTableWidget()
        self.session_table.setColumnCount(3)
        self.session_table.setHorizontalHeaderLabels(["时间", "备注", "配置数"])
        self.session_table.horizontalHeader().setStretchLastSection(True)
        self.session_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.session_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.session_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.session_table.itemSelectionChanged.connect(self._on_session_selected)

        detail_widget = QWidget()
        detail_layout = QVBoxLayout(detail_widget)
        detail_layout.setContentsMargins(0, 0, 0, 0)
        self.detail_table = QTableWidget()
        self.detail_table.setColumnCount(3)
        self.detail_table.setHorizontalHeaderLabels(["配置", "文件数", "描述"])
        self.detail_table.horizontalHeader().setStretchLastSection(True)
        self.detail_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.detail_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.restore_session_btn = QPushButton("恢复此批次")
        self.restore_session_btn.setStyleSheet("background-color: #FF5722; color: white; padding: 6px 16px;")
        detail_layout.addWidget(self.detail_table)
        detail_layout.addWidget(self.restore_session_btn)

        history_splitter.addWidget(self.session_table)
        history_splitter.addWidget(detail_widget)
        history_splitter.setSizes([400, 300])
        bottom_layout.addWidget(history_splitter)
        splitter.addWidget(bottom_group)

        layout.addWidget(splitter)

        self.scan_btn.clicked.connect(self._scan)
        self.select_all_btn.clicked.connect(self._select_all)
        self.deselect_all_btn.clicked.connect(self._deselect_all)
        self.backup_btn.clicked.connect(self._backup)
        self.restore_btn.clicked.connect(self._restore_selected)
        self.target_browse_btn.clicked.connect(self._browse_target)
        self.restore_session_btn.clicked.connect(self._restore_session)

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
        self._refresh_sessions()

    def _refresh_sessions(self, storage: Optional[StorageBackend] = None):
        self.session_table.setRowCount(0)
        self.detail_table.setRowCount(0)
        s = storage or self.storage
        sessions = s.list_sessions()
        self._session_data: dict[str, list[tuple[str, str, str]]] = {}
        for sess in sessions:
            for name in sess.config_names:
                versions = s.list_versions(name)
                for v in versions:
                    if v.session_id == sess.session_id:
                        self._session_data.setdefault(sess.session_id, []).append(
                            (v.config_name, v.backup_id, v.description[:60] if v.description else "")
                        )
            row = self.session_table.rowCount()
            self.session_table.insertRow(row)
            self.session_table.setItem(row, 0, QTableWidgetItem(sess.timestamp.replace("T", " ")[:19]))
            self.session_table.setItem(row, 1, QTableWidgetItem(sess.note[:40] if sess.note else ""))
            self.session_table.setItem(row, 2, QTableWidgetItem(str(sess.total_count)))
            self.session_table.item(row, 0).setData(Qt.ItemDataRole.UserRole, sess.session_id)

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

        self._backup_signals = BatchBackupSignals()
        self._backup_signals.progress.connect(self.progress_bar.setValue)
        self._backup_signals.message.connect(self.status_label.setText)
        self._backup_signals.done.connect(lambda summary: self._batch_backup_done(storage, summary))
        self._backup_signals.error.connect(lambda msg: self._backup_error(msg))

        manifest_base_dir = Path(target_path_str)
        worker = BatchBackupWorker(items, storage, manifest_base_dir, note, self._backup_signals)
        self.threadpool.start(worker)

    def _on_session_selected(self):
        self.detail_table.setRowCount(0)
        rows = self.session_table.selectedItems()
        if not rows:
            return
        sid = self.session_table.item(rows[0].row(), 0).data(Qt.ItemDataRole.UserRole)
        entries = self._session_data.get(sid, [])
        for config_name, backup_id, desc in entries:
            row = self.detail_table.rowCount()
            self.detail_table.insertRow(row)
            self.detail_table.setItem(row, 0, QTableWidgetItem(config_name))
            self.detail_table.setItem(row, 1, QTableWidgetItem(""))
            self.detail_table.setItem(row, 2, QTableWidgetItem(desc))
            self.detail_table.item(row, 0).setData(Qt.ItemDataRole.UserRole, backup_id)
        self._selected_session_id = sid

    def _batch_backup_done(self, storage: StorageBackend, summary: BackupSummary):
        self.backup_btn.setEnabled(True)
        self.restore_btn.setEnabled(True)
        self.progress_bar.setValue(100)
        self._backup_signals = None
        self._refresh_sessions(storage)
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
        self._backup_signals = None
        QMessageBox.critical(self, "备份失败", msg)

    def _restore_single(self, config_name: str, backup_id: str):
        if self._is_restoring:
            QMessageBox.warning(self, "提示", "正在执行恢复操作，请等待完成")
            return
        cfg = self._configs.get(config_name)
        if not cfg:
            QMessageBox.critical(self, "错误", f"未找到配置规则: {config_name}")
            return
        self._is_restoring = True
        self.backup_btn.setEnabled(False)
        self.restore_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self._restore_signals = RestoreSignals()
        self._restore_signals.progress.connect(self.progress_bar.setValue)
        self._restore_signals.message.connect(self.status_label.setText)
        self._restore_signals.done.connect(lambda result: self._restore_done(result))
        self._restore_signals.error.connect(lambda msg: self._restore_error(msg))
        self._restore_signals.file_blocked.connect(lambda msg, procs: self._handle_blocked(msg, procs))
        worker = RestoreWorker(cfg, self.storage, backup_id, None, self._restore_signals)
        self.threadpool.start(worker)

    def _restore_selected(self):
        rows = self.detail_table.selectedItems()
        if not rows:
            QMessageBox.warning(self, "提示", "请在右侧详情表中选择要恢复的配置")
            return
        item = rows[0]
        config_name = self.detail_table.item(item.row(), 0).text()
        backup_id = self.detail_table.item(item.row(), 0).data(Qt.ItemDataRole.UserRole)
        reply = QMessageBox.question(
            self, "确认恢复",
            f"确定要将 {config_name} 恢复到选中版本吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._restore_single(config_name, backup_id)

    def _restore_session(self):
        if not hasattr(self, '_selected_session_id') or not self._selected_session_id:
            QMessageBox.warning(self, "提示", "请先在左侧选择一个备份记录")
            return
        entries = self._session_data.get(self._selected_session_id, [])
        if not entries:
            QMessageBox.information(self, "提示", "该备份记录无可恢复的版本")
            return
        names = [e[0] for e in entries]
        reply = QMessageBox.question(
            self, "确认恢复批次",
            f"将依次恢复以下 {len(names)} 个配置：\n" + "\n".join(f"  • {n}" for n in names),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._restore_session_queue = list(entries)
            self._restore_next_in_session()

    def _restore_next_in_session(self):
        if not self._restore_session_queue:
            self._is_restoring = False
            self._restore_session_queue = []
            self.status_label.setText("批次恢复完成")
            QMessageBox.information(self, "恢复完成", "批次中所有配置已恢复")
            return
        config_name, backup_id, _ = self._restore_session_queue.pop(0)
        self._restore_single(config_name, backup_id)

    def _restore_done(self, result):
        self.backup_btn.setEnabled(True)
        self.restore_btn.setEnabled(True)
        self._restore_signals = None
        self._is_restoring = False
        self.status_label.setText(f"已恢复 {result.config_name}")
        if hasattr(self, '_restore_session_queue') and self._restore_session_queue:
            self._restore_next_in_session()
        else:
            self._restore_session_queue = []
            QMessageBox.information(self, "恢复完成", f"已成功恢复 {result.config_name}")

    def _restore_error(self, msg: str):
        self.backup_btn.setEnabled(True)
        self.restore_btn.setEnabled(True)
        self._restore_signals = None
        self._is_restoring = False
        self._restore_session_queue = []
        QMessageBox.critical(self, "恢复失败", msg)

    def _handle_blocked(self, msg: str, procs: list[str]):
        self.backup_btn.setEnabled(True)
        self.restore_btn.setEnabled(True)
        self._restore_signals = None
        self._is_restoring = False
        self._restore_session_queue = []
        proc_text = "\n".join(f"  • {p}" for p in procs)
        QMessageBox.warning(
            self, "文件被占用",
            f"{msg}\n请关闭以下程序后重试：\n{proc_text}\n\n或使用设置中的「重启时替换」功能。"
        )
