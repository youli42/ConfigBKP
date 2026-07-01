import json as _json
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QCheckBox, QPushButton, QListWidget, QListWidgetItem,
    QTableWidget, QTableWidgetItem, QHeaderView, QSpinBox,
    QStackedWidget, QGroupBox, QFormLayout, QFileDialog,
    QInputDialog, QMessageBox, QAbstractItemView, QDialog,
    QDialogButtonBox, QGridLayout,
)
from PySide6.QtCore import Qt
from src.utils.i18n import tr, on_locale_changed, off_locale_changed


def serialize_to_jsonc(data: dict) -> str:
    obj = {
        "name": data.get("name", ""),
        "description": data.get("description", ""),
        "version": 1,
        "enabled": data.get("enabled", True),
        "platform": data.get("platform", "windows"),
        "paths": list(data.get("paths", [])),
        "parser_fields": dict(data.get("parser_fields", {})),
        "strategy": {
            "type": data.get("strategy", {}).get("type", "incremental"),
            "max_versions": data.get("strategy", {}).get("max_versions", 10),
            "ignore_patterns": list(data.get("strategy", {}).get("ignore_patterns", [])),
        },
    }
    return _json.dumps(obj, indent=2, ensure_ascii=False)


def parse_to_form_data(cfg: dict) -> dict:
    return {
        "name": cfg.get("name", ""),
        "description": cfg.get("description", ""),
        "enabled": cfg.get("enabled", True),
        "platform": cfg.get("platform", "windows"),
        "paths": list(cfg.get("paths", [])),
        "parser_fields": dict(cfg.get("parser_fields", {})),
        "strategy": {
            "type": cfg.get("strategy", {}).get("type", "incremental"),
            "max_versions": cfg.get("strategy", {}).get("max_versions", 10),
            "ignore_patterns": list(cfg.get("strategy", {}).get("ignore_patterns", [])),
        },
    }


class FieldEditDialog(QDialog):
    def __init__(self, parent=None, field_path="", label=""):
        super().__init__(parent)
        self.setWindowTitle(tr("添加解析字段"))
        self._result = (field_path, label)
        layout = QGridLayout(self)
        layout.addWidget(QLabel(tr("字段路径:")), 0, 0)
        self.path_edit = QLineEdit(field_path)
        self.path_edit.setPlaceholderText(tr("如: editor.fontSize"))
        layout.addWidget(self.path_edit, 0, 1)
        layout.addWidget(QLabel(tr("显示标签:")), 1, 0)
        self.label_edit = QLineEdit(label)
        self.label_edit.setPlaceholderText(tr("如: 字号"))
        layout.addWidget(self.label_edit, 1, 1)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons, 2, 0, 1, 2)

    def _accept(self):
        path = self.path_edit.text().strip()
        label = self.label_edit.text().strip()
        if not path:
            QMessageBox.warning(self, tr("提示"), tr("字段路径不能为空"))
            return
        if "[" in path:
            QMessageBox.warning(self, tr("提示"), tr("不支持数组索引路径"))
            return
        self._result = (path, label)
        self.accept()

    def result(self) -> tuple[str, str]:
        return self._result


class ConfigWizard(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._data: dict = parse_to_form_data({})
        self._setup_ui()
        self.retranslate_ui()
        self._retranslate_cb = self.retranslate_ui
        on_locale_changed(self._retranslate_cb)
        self.destroyed.connect(self._on_destroy)

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        mode_bar = QHBoxLayout()
        self.mode_label = QLabel()
        mode_bar.addWidget(self.mode_label)
        mode_bar.addStretch()
        layout.addLayout(mode_bar)

        main_split = QHBoxLayout()

        self._step_group = QGroupBox()
        step_layout = QVBoxLayout(self._step_group)
        self._step_btns = []
        self._step_names = ["基本信息", "源路径", "解析字段", "备份策略"]
        for i, s in enumerate(self._step_names):
            btn = QPushButton(f"  \u25cb {s}")
            btn.setFlat(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("QPushButton { text-align: left; padding: 4px 8px; border: none; } "
                              "QPushButton:hover { background-color: #e0e0e0; }")
            btn.clicked.connect(lambda checked, idx=i: self._jump_to(idx))
            self._step_btns.append(btn)
            step_layout.addWidget(btn)
        step_layout.addStretch()
        main_split.addWidget(self._step_group)

        self._stack = QStackedWidget()
        self._page_widgets = []
        for i in range(4):
            page = QWidget()
            self._stack.addWidget(page)
            self._page_widgets.append(page)

        self._build_page0()
        self._build_page1()
        self._build_page2()
        self._build_page3()

        main_split.addWidget(self._stack, 1)
        layout.addLayout(main_split)

        nav_layout = QHBoxLayout()
        self.prev_btn = QPushButton()
        self.next_btn = QPushButton()
        self.finish_btn = QPushButton()
        self.finish_btn.setStyleSheet("background-color: #2196F3; color: white; padding: 6px 16px;")
        nav_layout.addWidget(self.prev_btn)
        nav_layout.addWidget(self.next_btn)
        nav_layout.addStretch()
        nav_layout.addWidget(self.finish_btn)
        layout.addLayout(nav_layout)

        self.prev_btn.clicked.connect(self._prev)
        self.next_btn.clicked.connect(self._next)
        self.finish_btn.clicked.connect(self._finish)

        self._update_step(0)

    def _build_page0(self):
        page = self._page_widgets[0]
        layout = QFormLayout(page)
        self.wiz_name = QLineEdit()
        self._wiz_name_label = QLabel()
        layout.addRow(self._wiz_name_label, self.wiz_name)
        self.wiz_desc = QLineEdit()
        self._wiz_desc_label = QLabel()
        layout.addRow(self._wiz_desc_label, self.wiz_desc)
        self.wiz_platform = QComboBox()
        self.wiz_platform.addItems(["windows", "macos", "linux", "cross-platform"])
        self._wiz_platform_label = QLabel()
        layout.addRow(self._wiz_platform_label, self.wiz_platform)
        self.wiz_enabled = QCheckBox()
        self.wiz_enabled.setChecked(True)
        layout.addRow("", self.wiz_enabled)

    def _build_page1(self):
        page = self._page_widgets[1]
        layout = QVBoxLayout(page)
        self.wiz_paths_list = QListWidget()
        layout.addWidget(self.wiz_paths_list)
        btn_row = QHBoxLayout()
        self.wiz_path_add_btn = QPushButton()
        self.wiz_path_browse_dir_btn = QPushButton()
        self.wiz_path_browse_file_btn = QPushButton()
        self.wiz_path_del_btn = QPushButton()
        btn_row.addWidget(self.wiz_path_add_btn)
        btn_row.addWidget(self.wiz_path_browse_dir_btn)
        btn_row.addWidget(self.wiz_path_browse_file_btn)
        btn_row.addWidget(self.wiz_path_del_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)
        self.wiz_path_add_btn.clicked.connect(self._add_path)
        self.wiz_path_browse_dir_btn.clicked.connect(self._browse_dir)
        self.wiz_path_browse_file_btn.clicked.connect(self._browse_file)
        self.wiz_path_del_btn.clicked.connect(self._del_path)

    def _add_path(self):
        text, ok = QInputDialog.getText(self, tr("添加路径"), tr("输入文件或目录路径：\n支持 %APPDATA% 等环境变量"),
                                        text="%APPDATA%\\")
        if ok and text.strip():
            self.wiz_paths_list.addItem(text.strip())

    def _browse_dir(self):
        folder = QFileDialog.getExistingDirectory(self, tr("选择配置文件目录"))
        if folder:
            self.wiz_paths_list.addItem(str(Path(folder)))

    def _browse_file(self):
        f = QFileDialog.getOpenFileName(self, tr("选择配置文件"))
        if f and f[0]:
            self.wiz_paths_list.addItem(str(Path(f[0])))

    def _del_path(self):
        row = self.wiz_paths_list.currentRow()
        if row >= 0:
            self.wiz_paths_list.takeItem(row)

    def _build_page2(self):
        page = self._page_widgets[2]
        layout = QVBoxLayout(page)
        self.wiz_fields_table = QTableWidget(0, 2)
        self.wiz_fields_table.horizontalHeader().setStretchLastSection(True)
        self.wiz_fields_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        layout.addWidget(self.wiz_fields_table)
        btn_row = QHBoxLayout()
        self.wiz_field_add_btn = QPushButton()
        self.wiz_field_del_btn = QPushButton()
        btn_row.addWidget(self.wiz_field_add_btn)
        btn_row.addWidget(self.wiz_field_del_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)
        self.wiz_field_add_btn.clicked.connect(self._add_field)
        self.wiz_field_del_btn.clicked.connect(self._del_field)

    def _add_field(self):
        dlg = FieldEditDialog(self)
        if dlg.exec():
            path, label = dlg.result()
            row = self.wiz_fields_table.rowCount()
            self.wiz_fields_table.insertRow(row)
            self.wiz_fields_table.setItem(row, 0, QTableWidgetItem(path))
            self.wiz_fields_table.setItem(row, 1, QTableWidgetItem(label))

    def _del_field(self):
        row = self.wiz_fields_table.currentRow()
        if row >= 0:
            self.wiz_fields_table.removeRow(row)

    def _build_page3(self):
        page = self._page_widgets[3]
        layout = QFormLayout(page)
        self.wiz_strat_type = QComboBox()
        self.wiz_strat_type.addItems(["incremental", "full"])
        self._wiz_strat_type_label = QLabel()
        layout.addRow(self._wiz_strat_type_label, self.wiz_strat_type)
        self.wiz_strat_max = QSpinBox()
        self.wiz_strat_max.setMinimum(1)
        self.wiz_strat_max.setMaximum(99)
        self.wiz_strat_max.setValue(10)
        self._wiz_strat_max_label = QLabel()
        layout.addRow(self._wiz_strat_max_label, self.wiz_strat_max)
        self.wiz_ignore_list = QListWidget()
        self._wiz_ignore_label = QLabel()
        layout.addRow(self._wiz_ignore_label, self.wiz_ignore_list)
        ig_btn_row = QHBoxLayout()
        self.wiz_ignore_add_btn = QPushButton()
        self.wiz_ignore_del_btn = QPushButton()
        ig_btn_row.addWidget(self.wiz_ignore_add_btn)
        ig_btn_row.addWidget(self.wiz_ignore_del_btn)
        ig_btn_row.addStretch()
        layout.addRow("", ig_btn_row)
        self.wiz_ignore_add_btn.clicked.connect(self._add_ignore)
        self.wiz_ignore_del_btn.clicked.connect(self._del_ignore)

    def _add_ignore(self):
        text, ok = QInputDialog.getText(self, tr("添加忽略模式"), tr("Glob 模式：\n如 *.log 或 __pycache__/"))
        if ok and text.strip():
            self.wiz_ignore_list.addItem(text.strip())

    def _del_ignore(self):
        row = self.wiz_ignore_list.currentRow()
        if row >= 0:
            self.wiz_ignore_list.takeItem(row)

    def retranslate_ui(self):
        self.mode_label.setText(tr("向导模式"))
        self._step_group.setTitle(tr("步骤"))
        current_idx = self._stack.currentIndex() if hasattr(self, '_stack') else 0
        for i, s in enumerate(self._step_names):
            translated = tr(s)
            bullet = "\u25cf" if i == current_idx else "\u25cb"
            self._step_btns[i].setText(f"  {bullet} {translated}")
        self._wiz_name_label.setText(tr("名称:"))
        self.wiz_name.setPlaceholderText(tr("必填，如: VS Code"))
        self._wiz_desc_label.setText(tr("描述:"))
        self.wiz_desc.setPlaceholderText(tr("选填，如: Visual Studio Code 编辑器配置"))
        self._wiz_platform_label.setText(tr("平台:"))
        self.wiz_enabled.setText(tr("启用"))
        self.wiz_path_add_btn.setText(tr("添加路径"))
        self.wiz_path_browse_dir_btn.setText(tr("浏览目录..."))
        self.wiz_path_browse_file_btn.setText(tr("浏览文件..."))
        self.wiz_path_del_btn.setText(tr("删除路径"))
        self.wiz_fields_table.setHorizontalHeaderLabels([tr("字段路径"), tr("显示标签")])
        self.wiz_field_add_btn.setText(tr("添加字段"))
        self.wiz_field_del_btn.setText(tr("删除字段"))
        self._wiz_strat_type_label.setText(tr("备份类型:"))
        self._wiz_strat_max_label.setText(tr("最大版本数:"))
        self._wiz_ignore_label.setText(tr("忽略模式:"))
        self.wiz_ignore_add_btn.setText(tr("添加"))
        self.wiz_ignore_del_btn.setText(tr("删除"))
        self.prev_btn.setText(tr("上一步"))
        self.next_btn.setText(tr("下一步"))
        self.finish_btn.setText(tr("完成"))

    def _on_destroy(self):
        off_locale_changed(self._retranslate_cb)

    def _update_step(self, idx: int):
        for i, btn in enumerate(self._step_btns):
            text = btn.text().strip()
            label = text.lstrip("\u25cb\u25cf ").strip()
            btn.setText(f"  {'\u25cf' if i == idx else '\u25cb'} {label}")
        self._stack.setCurrentIndex(idx)
        self.prev_btn.setEnabled(idx > 0)
        self.next_btn.setVisible(idx < 3)
        self.finish_btn.setVisible(idx == 3)

    def _jump_to(self, idx: int):
        self._collect_current()
        self._update_step(idx)

    def _prev(self):
        if self._stack.currentIndex() > 0:
            self._collect_current()
            self._update_step(self._stack.currentIndex() - 1)

    def _next(self):
        if self._stack.currentIndex() < 3:
            self._collect_current()
            self._update_step(self._stack.currentIndex() + 1)

    def _collect_current(self):
        idx = self._stack.currentIndex()
        if idx == 0:
            self._data["name"] = self.wiz_name.text().strip()
            self._data["description"] = self.wiz_desc.text().strip()
            self._data["platform"] = self.wiz_platform.currentText()
            self._data["enabled"] = self.wiz_enabled.isChecked()
        elif idx == 1:
            paths = []
            for i in range(self.wiz_paths_list.count()):
                paths.append(self.wiz_paths_list.item(i).text())
            self._data["paths"] = paths
        elif idx == 2:
            fields = {}
            for r in range(self.wiz_fields_table.rowCount()):
                k = self.wiz_fields_table.item(r, 0)
                v = self.wiz_fields_table.item(r, 1)
                if k and k.text():
                    fields[k.text()] = v.text() if v else ""
            self._data["parser_fields"] = fields
        elif idx == 3:
            self._data["strategy"]["type"] = self.wiz_strat_type.currentText()
            self._data["strategy"]["max_versions"] = self.wiz_strat_max.value()
            ignores = []
            for i in range(self.wiz_ignore_list.count()):
                ignores.append(self.wiz_ignore_list.item(i).text())
            self._data["strategy"]["ignore_patterns"] = ignores

    def _finish(self):
        self._collect_current()
        if not self._data.get("name"):
            QMessageBox.warning(self, tr("提示"), tr("名称不能为空"))
            self._update_step(0)
            return
        jsonc = serialize_to_jsonc(self._data)
        self._on_finish(jsonc)

    def _on_finish(self, jsonc: str):
        pass

    def set_on_finish(self, callback):
        self._on_finish = callback

    def load_rule(self, cfg: dict):
        self._data = parse_to_form_data(cfg)
        self._sync_to_ui()

    def _sync_to_ui(self):
        self.wiz_name.setText(self._data.get("name", ""))
        self.wiz_desc.setText(self._data.get("description", ""))
        plat = self._data.get("platform", "windows")
        idx = self.wiz_platform.findText(plat)
        if idx >= 0:
            self.wiz_platform.setCurrentIndex(idx)
        self.wiz_enabled.setChecked(self._data.get("enabled", True))

        self.wiz_paths_list.clear()
        for p in self._data.get("paths", []):
            self.wiz_paths_list.addItem(p)

        self.wiz_fields_table.setRowCount(0)
        for k, v in self._data.get("parser_fields", {}).items():
            row = self.wiz_fields_table.rowCount()
            self.wiz_fields_table.insertRow(row)
            self.wiz_fields_table.setItem(row, 0, QTableWidgetItem(k))
            self.wiz_fields_table.setItem(row, 1, QTableWidgetItem(v))

        strat = self._data.get("strategy", {})
        st = strat.get("type", "incremental")
        sidx = self.wiz_strat_type.findText(st)
        if sidx >= 0:
            self.wiz_strat_type.setCurrentIndex(sidx)
        self.wiz_strat_max.setValue(strat.get("max_versions", 10))
        self.wiz_ignore_list.clear()
        for ig in strat.get("ignore_patterns", []):
            self.wiz_ignore_list.addItem(ig)

        self._update_step(0)

    def get_jsonc(self) -> str:
        self._collect_current()
        return serialize_to_jsonc(self._data)
