from pathlib import Path
import json5
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QPlainTextEdit, QLabel, QMessageBox, QSplitter,
    QListWidget, QAbstractItemView, QListWidgetItem,
    QTabWidget,
)
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt
from src.core.config_parser import load_config
from src.gui.config_wizard import ConfigWizard, parse_to_form_data
from src.utils.i18n import tr


class ConfigTab(QWidget):
    def __init__(self, config_dir: Path):
        super().__init__()
        self.config_dir = config_dir
        self._current_file: Path | None = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        top_bar = QHBoxLayout()
        self.new_btn = QPushButton(tr("新建"))
        self.delete_btn = QPushButton(tr("删除"))
        top_bar.addWidget(self.new_btn)
        top_bar.addWidget(self.delete_btn)
        self.mode_switcher = QTabWidget()
        self.mode_switcher.setTabPosition(QTabWidget.TabPosition.North)
        top_bar.addStretch()
        layout.addLayout(top_bar)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.rule_list = QListWidget()
        self.rule_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.rule_list.currentItemChanged.connect(self._on_list_selected)
        splitter.addWidget(self.rule_list)

        self._editor_tabs = QTabWidget()
        self._editor_tabs.setTabPosition(QTabWidget.TabPosition.South)

        self.editor = QPlainTextEdit()
        self.editor.setPlaceholderText(tr("在此编辑 JSONC 配置..."))
        self.editor.setFont(QFont("Consolas", 10))
        self.editor.textChanged.connect(self._on_source_changed)
        self._editor_tabs.addTab(self.editor, tr("源码"))

        self.wizard = ConfigWizard()
        self.wizard.set_on_finish(self._on_wizard_finish)
        self._editor_tabs.addTab(self.wizard, tr("向导"))

        self._editor_tabs.currentChanged.connect(self._on_tab_switched)

        editor_widget = QWidget()
        editor_layout = QVBoxLayout(editor_widget)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_layout.addWidget(self._editor_tabs)
        bottom_bar = QHBoxLayout()
        self.validation_label = QLabel("")
        self.validation_label.setStyleSheet("color: green;")
        bottom_bar.addWidget(self.validation_label)
        self.save_btn = QPushButton(tr("保存"))
        self.scan_btn = QPushButton(tr("扫描本机已装软件"))
        bottom_bar.addStretch()
        bottom_bar.addWidget(self.scan_btn)
        bottom_bar.addWidget(self.save_btn)
        editor_layout.addLayout(bottom_bar)

        splitter.addWidget(editor_widget)
        editor_widget.setMinimumWidth(300)
        splitter.setSizes([200, 500])
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
            self.validation_label.setText(tr("语法正确 ✔"))
            self.validation_label.setStyleSheet("color: green;")
        except Exception as e:
            self.validation_label.setText(tr("语法错误: {}").format(e))
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
                    QMessageBox.warning(self, tr("解析警告"),
                                        tr("源码 JSONC 解析失败，向导将保持当前数据：\n{}").format(e))

    def _on_wizard_finish(self, jsonc: str):
        text = self.editor.toPlainText()
        if text.strip():
            try:
                json5.loads(jsonc)
            except Exception:
                QMessageBox.critical(self, tr("错误"), tr("生成的 JSONC 格式有误"))
                return
        if self._current_file:
            self._current_file.write_text(jsonc, encoding="utf-8")
            self.validation_label.setText(tr("已保存 ✔"))
            QMessageBox.information(self, tr("保存成功"), tr("已保存到 {}").format(self._current_file))

    def refresh_rules(self):
        current_path = str(self._current_file) if self._current_file else ""
        self.rule_list.blockSignals(True)
        self.rule_list.clear()
        for sub in ["builtin", "user"]:
            sub_dir = self.config_dir / sub
            if not sub_dir.exists():
                continue
            for fpath in sorted(sub_dir.glob("*.jsonc")):
                try:
                    cfg = load_config(fpath)
                    name = cfg.get("name", fpath.stem)
                    item = QListWidgetItem(name)
                    item.setData(Qt.ItemDataRole.UserRole, str(fpath))
                    item.setToolTip(str(fpath))
                    self.rule_list.addItem(item)
                except Exception:
                    continue
        self.rule_list.blockSignals(False)
        if current_path:
            for i in range(self.rule_list.count()):
                if self.rule_list.item(i).data(Qt.ItemDataRole.UserRole) == current_path:
                    self.rule_list.setCurrentRow(i)
                    return
        if self.rule_list.count() > 0:
            self.rule_list.setCurrentRow(0)

    def _on_list_selected(self, current: QListWidgetItem | None, previous: QListWidgetItem | None):
        if not current:
            self.editor.clear()
            self._current_file = None
            return
        fpath_str = current.data(Qt.ItemDataRole.UserRole)
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
                self.validation_label.setText(tr("读取失败: {}").format(e))
                self.validation_label.setStyleSheet("color: red;")

    def _save(self):
        if not self._current_file:
            QMessageBox.warning(self, tr("提示"), tr("请先选择或新建一个规则"))
            return
        tab_idx = self._editor_tabs.currentIndex()
        if tab_idx == 0:
            text = self.editor.toPlainText()
            try:
                json5.loads(text)
            except Exception as e:
                QMessageBox.critical(self, tr("语法错误"), tr("无法保存，JSONC 语法错误:\n{}").format(e))
                return
            self._current_file.write_text(text, encoding="utf-8")
            self.validation_label.setText(tr("已保存 ✔"))
            QMessageBox.information(self, tr("保存成功"), tr("已保存到 {}").format(self._current_file))
        else:
            jsonc = self.wizard.get_jsonc()
            try:
                json5.loads(jsonc)
            except Exception as e:
                QMessageBox.critical(self, tr("语法错误"), tr("生成的配置有误:\n{}").format(e))
                return
            self._current_file.write_text(jsonc, encoding="utf-8")
            self.validation_label.setText(tr("已保存 ✔"))
            QMessageBox.information(self, tr("保存成功"), tr("已保存到 {}").format(self._current_file))

    def _scan(self):
        from src.core.scanner import scan_installed
        matched = scan_installed([self.config_dir / "builtin", self.config_dir / "user"])
        QMessageBox.information(
            self, tr("扫描完成"),
            tr("扫描完成，匹配 {} 条规则:\n{}").format(
                len(matched), "\n".join(f"  ✓ {m}" for m in matched))
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
        for i in range(self.rule_list.count()):
            if self.rule_list.item(i).data(Qt.ItemDataRole.UserRole) == str(new_file):
                self.rule_list.setCurrentRow(i)
                break
        QMessageBox.information(self, tr("已创建"), tr("已创建新规则:\n{}").format(new_file))

    def _delete_rule(self):
        if not self._current_file or not self._current_file.exists():
            return
        reply = QMessageBox.question(
            self, tr("确认删除"), tr("确定删除 {} 吗？").format(self._current_file.name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._current_file.unlink()
            self._current_file = None
            self.refresh_rules()
