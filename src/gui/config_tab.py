from pathlib import Path
import json5
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QPlainTextEdit, QLabel, QMessageBox, QSplitter,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QTabWidget,
)
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt
from src.core.config_parser import load_config
from src.gui.config_wizard import ConfigWizard, parse_to_form_data


class ConfigTab(QWidget):
    def __init__(self, config_dir: Path):
        super().__init__()
        self.config_dir = config_dir
        self._current_file: Path | None = None
        self._suspend_enabled_toggle = False
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        top_bar = QHBoxLayout()
        self.new_btn = QPushButton("新建")
        self.delete_btn = QPushButton("删除")
        top_bar.addWidget(self.new_btn)
        top_bar.addWidget(self.delete_btn)
        self.mode_switcher = QTabWidget()
        self.mode_switcher.setTabPosition(QTabWidget.TabPosition.North)
        top_bar.addStretch()
        layout.addLayout(top_bar)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.rule_table = QTableWidget()
        self.rule_table.setColumnCount(3)
        self.rule_table.setHorizontalHeaderLabels(["名称", "启用", "描述"])
        self.rule_table.horizontalHeader().setStretchLastSection(True)
        self.rule_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.rule_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.rule_table.verticalHeader().setVisible(False)
        self.rule_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.rule_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.rule_table.itemSelectionChanged.connect(self._on_table_selected)
        self.rule_table.itemChanged.connect(self._on_enabled_toggled)
        splitter.addWidget(self.rule_table)

        self._editor_tabs = QTabWidget()
        self._editor_tabs.setTabPosition(QTabWidget.TabPosition.South)

        self.editor = QPlainTextEdit()
        self.editor.setPlaceholderText("在此编辑 JSONC 配置...")
        self.editor.setFont(QFont("Consolas", 10))
        self.editor.textChanged.connect(self._on_source_changed)
        self._editor_tabs.addTab(self.editor, "源码")

        self.wizard = ConfigWizard()
        self.wizard.set_on_finish(self._on_wizard_finish)
        self._editor_tabs.addTab(self.wizard, "向导")

        self._editor_tabs.currentChanged.connect(self._on_tab_switched)

        editor_widget = QWidget()
        editor_layout = QVBoxLayout(editor_widget)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_layout.addWidget(self._editor_tabs)
        bottom_bar = QHBoxLayout()
        self.validation_label = QLabel("")
        self.validation_label.setStyleSheet("color: green;")
        bottom_bar.addWidget(self.validation_label)
        self.save_btn = QPushButton("保存")
        self.scan_btn = QPushButton("扫描本机已装软件")
        bottom_bar.addStretch()
        bottom_bar.addWidget(self.scan_btn)
        bottom_bar.addWidget(self.save_btn)
        editor_layout.addLayout(bottom_bar)

        splitter.addWidget(editor_widget)
        editor_widget.setMinimumWidth(300)
        splitter.setSizes([250, 500])
        layout.addWidget(splitter)

        self.save_btn.clicked.connect(self._save)
        self.scan_btn.clicked.connect(self._scan)
        self.new_btn.clicked.connect(self._new_rule)
        self.delete_btn.clicked.connect(self._delete_rule)

        self.refresh_rules()

    def _on_source_changed(self):
        text = self.editor.toPlainText()
        if not text.strip():
            self.validation_label.setText("")
            return
        try:
            json5.loads(text)
            self.validation_label.setText("语法正确 ✔")
            self.validation_label.setStyleSheet("color: green;")
        except Exception as e:
            self.validation_label.setText(f"语法错误: {e}")
            self.validation_label.setStyleSheet("color: red;")

    def _on_tab_switched(self, idx: int):
        if idx == 0:
            content = self.wizard.get_jsonc()
            self.editor.setPlainText(content)
            self.editor.setFont(QFont("Consolas", 10))
        elif idx == 1:
            text = self.editor.toPlainText()
            if text.strip():
                try:
                    cfg = json5.loads(text)
                    self.wizard.load_rule(cfg)
                except Exception as e:
                    QMessageBox.warning(self, "解析警告",
                                        f"源码 JSONC 解析失败，向导将保持当前数据：\n{e}")

    def _on_wizard_finish(self, jsonc: str):
        text = self.editor.toPlainText()
        if text.strip():
            try:
                json5.loads(jsonc)
            except Exception:
                QMessageBox.critical(self, "错误", "生成的 JSONC 格式有误")
                return
        if self._current_file:
            self._current_file.write_text(jsonc, encoding="utf-8")
            self.validation_label.setText("已保存 ✔")
            QMessageBox.information(self, "保存成功", f"已保存到 {self._current_file}")

    def refresh_rules(self):
        current_path = str(self._current_file) if self._current_file else ""
        self.rule_table.blockSignals(True)
        self.rule_table.setRowCount(0)
        self._rule_paths: dict[int, str] = {}

        for sub in ["builtin", "user"]:
            sub_dir = self.config_dir / sub
            if not sub_dir.exists():
                continue
            for fpath in sorted(sub_dir.glob("*.jsonc")):
                try:
                    cfg = load_config(fpath)
                except Exception:
                    continue
                name = cfg.get("name", fpath.stem)
                version = cfg.get("version", 1)
                enabled = cfg.get("enabled", True)
                desc = cfg.get("description", "")
                self._add_rule_row(name, version, enabled, desc, str(fpath))

        self.rule_table.blockSignals(False)
        if current_path:
            for r in range(self.rule_table.rowCount()):
                if self._rule_paths.get(r) == current_path:
                    self.rule_table.selectRow(r)
                    return
        if self.rule_table.rowCount() > 0:
            self.rule_table.selectRow(0)

    def _add_rule_row(self, name: str, version: int, enabled: bool, desc: str, fpath: str):
        r = self.rule_table.rowCount()
        self.rule_table.insertRow(r)
        ver_badge = f"v{version}" if version else ""
        display_name = f"{name}  [{ver_badge}]" if ver_badge else name
        self.rule_table.setItem(r, 0, QTableWidgetItem(display_name))
        self.rule_table.item(r, 0).setData(Qt.ItemDataRole.UserRole, fpath)
        self.rule_table.item(r, 0).setToolTip(fpath)

        cb = QTableWidgetItem()
        cb.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        cb.setCheckState(Qt.CheckState.Checked if enabled else Qt.CheckState.Unchecked)
        self.rule_table.setItem(r, 1, cb)

        self.rule_table.setItem(r, 2, QTableWidgetItem(desc))
        self._rule_paths[r] = fpath

    def _on_table_selected(self):
        rows = self.rule_table.selectedItems()
        if not rows:
            self.editor.clear()
            self._current_file = None
            return
        r = rows[0].row()
        fpath_str = self.rule_table.item(r, 0).data(Qt.ItemDataRole.UserRole)
        if fpath_str:
            self._current_file = Path(fpath_str)
            try:
                content = self._current_file.read_text(encoding="utf-8")
                self.editor.setPlainText(content)
                cfg = json5.loads(content)
                self.wizard.load_rule(cfg)
                self._editor_tabs.setCurrentIndex(1)
            except Exception as e:
                self.editor.clear()
                self.validation_label.setText(f"读取失败: {e}")
                self.validation_label.setStyleSheet("color: red;")

    def _on_enabled_toggled(self, item: QTableWidgetItem):
        if self._suspend_enabled_toggle or item.column() != 1:
            return
        r = item.row()
        fpath_str = self.rule_table.item(r, 0).data(Qt.ItemDataRole.UserRole)
        if not fpath_str:
            return
        new_state = item.checkState() == Qt.CheckState.Checked
        fpath = Path(fpath_str)
        try:
            import re
            old_text = fpath.read_text(encoding="utf-8")
            new_val = "true" if new_state else "false"
            new_text, n = re.subn(
                r'("enabled"\s*:\s*)true|("enabled"\s*:\s*)false',
                lambda m: (m.group(1) or m.group(2)) + new_val,
                old_text, count=1,
            )
            if n == 0:
                raise ValueError("未找到 enabled 字段")
            fpath.write_text(new_text, encoding="utf-8")
        except Exception as e:
            self._suspend_enabled_toggle = True
            item.setCheckState(Qt.CheckState.Unchecked if new_state else Qt.CheckState.Checked)
            self._suspend_enabled_toggle = False
            QMessageBox.critical(self, "错误", f"写入失败，已回滚: {e}")

    def _save(self):
        if not self._current_file:
            QMessageBox.warning(self, "提示", "请先选择或新建一个规则")
            return
        tab_idx = self._editor_tabs.currentIndex()
        if tab_idx == 0:
            text = self.editor.toPlainText()
            try:
                json5.loads(text)
            except Exception as e:
                QMessageBox.critical(self, "语法错误", f"无法保存，JSONC 语法错误:\n{e}")
                return
            self._current_file.write_text(text, encoding="utf-8")
            self.validation_label.setText("已保存 ✔")
            QMessageBox.information(self, "保存成功", f"已保存到 {self._current_file}")
        else:
            jsonc = self.wizard.get_jsonc()
            try:
                json5.loads(jsonc)
            except Exception as e:
                QMessageBox.critical(self, "语法错误", f"生成的配置有误:\n{e}")
                return
            self._current_file.write_text(jsonc, encoding="utf-8")
            self.validation_label.setText("已保存 ✔")
            QMessageBox.information(self, "保存成功", f"已保存到 {self._current_file}")

    def _scan(self):
        from src.core.scanner import scan_installed
        matched = scan_installed([self.config_dir / "builtin", self.config_dir / "user"])
        QMessageBox.information(
            self, "扫描完成",
            f"扫描完成，匹配 {len(matched)} 条规则:\n" + "\n".join(f"  ✓ {m}" for m in matched)
        )

    def _new_rule(self):
        template = """{
  "name": "新配置",
  "description": "请填写描述",
  "version": 1,
  "enabled": true,
  "platform": "windows",
  "paths": [
    "%APPDATA%\\...\\config.json"
  ],
  "parser_fields": {},
  "strategy": {
    "type": "incremental",
    "max_versions": 10,
    "ignore_patterns": []
  }
}
"""
        user_dir = self.config_dir / "user"
        user_dir.mkdir(parents=True, exist_ok=True)
        new_file = user_dir / f"new_rule_{len(list(user_dir.glob('*.jsonc'))) + 1}.jsonc"
        new_file.write_text(template, encoding="utf-8")
        self.refresh_rules()
        for r in range(self.rule_table.rowCount()):
            if self.rule_table.item(r, 0).data(Qt.ItemDataRole.UserRole) == str(new_file):
                self.rule_table.selectRow(r)
                break
        QMessageBox.information(self, "已创建", f"已创建新规则:\n{new_file}")

    def _delete_rule(self):
        if not self._current_file or not self._current_file.exists():
            return
        reply = QMessageBox.question(
            self, "确认删除", f"确定删除 {self._current_file.name} 吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._current_file.unlink()
            self._current_file = None
            self.refresh_rules()
