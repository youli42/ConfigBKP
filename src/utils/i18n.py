_current_locale = "zh_CN"
_translations: dict[str, str] = {}


def install(locale: str):
    global _current_locale, _translations
    _current_locale = locale
    _translations.clear()
    if locale == "zh_CN":
        return
    try:
        mod = __import__(f"lang.{locale}", fromlist=["DATA"])
        _translations.update(mod.DATA)
    except ImportError:
        pass


def tr(key: str) -> str:
    return _translations.get(key, key)


def current_locale() -> str:
    return _current_locale
