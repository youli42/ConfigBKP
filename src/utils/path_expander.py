from pathlib import Path
import os
import re


_ENV_VAR_PATTERN = re.compile(r"%([^%]+)%")


def expand(path_str: str) -> Path:
    def _replace(m: re.Match) -> str:
        val = os.environ.get(m.group(1), "")
        return val
    expanded = _ENV_VAR_PATTERN.sub(_replace, path_str)
    return Path(expanded).resolve()
