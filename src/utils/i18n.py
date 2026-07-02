import sys
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QTranslator, QCoreApplication


_current_locale = "zh_CN"
_callbacks: list[Callable[[], None]] = []
_translator: QTranslator | None = None


def _get_lang_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent / "_internal" / "lang"
    return Path(__file__).resolve().parent.parent.parent / "lang"


def install(locale: str):
    """Install QTranslator for the given locale, then notify all callbacks."""
    global _current_locale, _translator

    _current_locale = locale

    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()

    # Remove old translator if any
    if _translator is not None and app is not None:
        app.removeTranslator(_translator)
        _translator = None

    if locale == "zh_CN":
        # Source language — no .qm needed, QCoreApplication.translate() returns source text
        _notify()
        return

    # Load .qm file for the target locale
    qm_path = _get_lang_dir() / f"{locale}.qm"
    if qm_path.exists():
        new_translator = QTranslator()
        if new_translator.load(str(qm_path)):
            _translator = new_translator
            if app is not None:
                app.installTranslator(_translator)

    _notify()


def tr(key: str) -> str:
    """Translate key using the currently installed QTranslator."""
    app = QCoreApplication.instance()
    if app is None:
        return key
    return QCoreApplication.translate("App", key)


def current_locale() -> str:
    return _current_locale


def on_locale_changed(cb: Callable[[], None]) -> None:
    """Register a callback to be invoked when locale changes."""
    _callbacks.append(cb)


def off_locale_changed(cb: Callable[[], None]) -> None:
    """Unregister a previously registered callback."""
    _callbacks.remove(cb)


def _notify() -> None:
    for cb in _callbacks:
        cb()
