# main.py

文件职责：程序的唯一入口。检测是否以管理员身份运行，若不是则请求 UAC 提权重启；是则启动 PySide6 QApplication。

## 公开接口

| 函数/方法 | 参数 | 返回值 | 核心作用 | 副作用/异常 |
|-----------|------|--------|----------|-------------|
| `is_admin()` | 无 | `bool` | 调用 `shell32.IsUserAnAdmin` 判断当前进程是否有管理员权限 | `AttributeError` 时返回 `True`（非 Windows 平台兼容） |
| `main()` | 无 | `None` | 非管理员 → `ShellExecuteW(runas)` 提权重启；管理员 → 启动 QApplication + MainWindow | 非管理员时 `sys.exit(0)` 终止原进程 |

## 特别说明

- ⚠️ **管理员权限**：调用 `ctypes.windll.shell32.ShellExecuteW` 提权，参数 `runas` 触发 UAC 对话框。
- 打包后 `sys.executable` 指向 exe 自身路径，提权命令仍然有效。
