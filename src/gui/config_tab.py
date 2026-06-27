from pathlib import Path
import json5
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QPushButton,
    QPlainTextEdit, QLabel, QMessageBox, QFrame, QSplitter,
    QListWidget, QListWidgetItem,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from src.core.config_parser import load_config


class ConfigTab(QWidget):
    def __init__(self, config_dir: Path, user_config_dir: Path):
        super().__init__()
        self.config_dir = config_dir
        self.user_config_dir = user_config_dir
        self._current_file: Path | None = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        top_bar = QHBoxLayout()
        top_bar.addWidget(QLabel("选择规则:"))
        self.rule_selector = QComboBox()
        self.rule_selector.currentIndexChanged.connect(self._on_rule_selected)
        top_bar.addWidget(self.rule_selector)

        self.new_btn = QPushButton("新建")
        self.dup_btn = QPushButton("复制到用户")
        self.delete_btn = QPushButton("删除")
        top_bar.addWidget(self.new_btn)
        top_bar.addWidget(self.dup_btn)
        top_bar.addWidget(self.delete_btn)
        top_bar.addStretch()
        layout.addLayout(top_bar)

        self.editor = QPlainTextEdit()
        self.editor.setPlaceholderText("在此编辑 JSONC 配置...")
        self.editor.setFont(QFont("Consolas", 10))
        self.editor.textChanged.connect(self._validate)
        layout.addWidget(self.editor)

        bottom_bar = QHBoxLayout()
        self.validation_label = QLabel("")
        self.validation_label.setStyleSheet("color: green;")
        bottom_bar.addWidget(self.validation_label)

        self.save_btn = QPushButton("保存")
        self.scan_btn = QPushButton("扫描本机已装软件")
        self.reset_btn = QPushButton("恢复默认")
        bottom_bar.addStretch()
        bottom_bar.addWidget(self.scan_btn)
        bottom_bar.addWidget(self.reset_btn)
        bottom_bar.addWidget(self.save_btn)
        layout.addLayout(bottom_bar)

        self.save_btn.clicked.connect(self._save)
        self.scan_btn.clicked.connect(self._scan)
        self.reset_btn.clicked.connect(self._reset)
        self.new_btn.clicked.connect(self._new_rule)
        self.dup_btn.clicked.connect(self._dup_to_user)
        self.delete_btn.clicked.connect(self._delete_rule)

        self.refresh_rules()

    def refresh_rules(self):
        current = self.rule_selector.currentText()
        self.rule_selector.blockSignals(True)
        self.rule_selector.clear()
        for cfg_dir in [self.config_dir, self.user_config_dir]:
            if not cfg_dir.exists():
                continue
            for fpath in sorted(cfg_dir.glob("*.jsonc")):
                try:
                    cfg = load_config(fpath)
                    name = cfg.get("name", fpath.stem)
                    label = f"[{'内置' if cfg_dir == self.config_dir else '用户'}] {name}"
                    self.rule_selector.addItem(label, str(fpath))
                except Exception:
                    continue
        idx = self.rule_selector.findText(current)
        if idx >= 0:
            self.rule_selector.setCurrentIndex(idx)
        self.rule_selector.blockSignals(False)
        if self.rule_selector.count() > 0:
            self._on_rule_selected(0)

    def _on_rule_selected(self, index: int):
        if index < 0:
            self.editor.clear()
            self._current_file = None
            return
        fpath_str = self.rule_selector.itemData(index)
        if fpath_str:
            self._current_file = Path(fpath_str)
            try:
                content = self._current_file.read_text(encoding="utf-8")
                self.editor.setPlainText(content)
            except Exception as e:
                self.editor.clear()
                self.validation_label.setText(f"读取失败: {e}")
                self.validation_label.setStyleSheet("color: red;")

    def _validate(self):
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

    def _save(self):
        if not self._current_file:
            QMessageBox.warning(self, "提示", "请先选择或新建一个规则")
            return
        text = self.editor.toPlainText()
        try:
            json5.loads(text)
        except Exception as e:
            QMessageBox.critical(self, "语法错误", f"无法保存，JSONC 语法错误:\n{e}")
            return
        self._current_file.write_text(text, encoding="utf-8")
        self.validation_label.setText("已保存 ✔")
        QMessageBox.information(self, "保存成功", f"已保存到 {self._current_file}")

    def _scan(self):
        from src.core.scanner import scan_installed
        matched = scan_installed([self.config_dir, self.user_config_dir])
        QMessageBox.information(
            self, "扫描完成",
            f"扫描完成，匹配 {len(matched)} 条规则:\n" + "\n".join(f"  ✓ {m}" for m in matched)
        )

    def _reset(self):
        if not self._current_file or not self._current_file.exists():
            return
        reply = QMessageBox.question(
            self, "确认", "确定恢复默认内容吗？当前编辑内容将丢失。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._on_rule_selected(self.rule_selector.currentIndex())

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
        new_file = self.user_config_dir / f"new_rule_{len(list(self.user_config_dir.glob('*.jsonc'))) + 1}.jsonc"
        new_file.write_text(template, encoding="utf-8")
        self.refresh_rules()
        for i in range(self.rule_selector.count()):
            if self.rule_selector.itemData(i) == str(new_file):
                self.rule_selector.setCurrentIndex(i)
                break
        QMessageBox.information(self, "已创建", f"已创建新规则:\n{new_file}")

    def _dup_to_user(self):
        if not self._current_file or not self._current_file.exists():
            return
        if self._current_file.parent == self.user_config_dir:
            QMessageBox.information(self, "提示", "该规则已在用户目录中")
            return
        dst = self.user_config_dir / self._current_file.name
        dst.write_text(self._current_file.read_text(encoding="utf-8"), encoding="utf-8")
        self.refresh_rules()
        QMessageBox.information(self, "已复制", f"已复制到用户配置:\n{dst}")

    def _delete_rule(self):
        if not self._current_file or not self._current_file.exists():
            return
        if self._current_file.parent == self.config_dir:
            QMessageBox.warning(self, "禁止", "无法删除内置规则")
            return
        reply = QMessageBox.question(
            self, "确认删除", f"确定删除 {self._current_file.name} 吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._current_file.unlink()
            self.refresh_rules()
