import fnmatch
from pathlib import Path


def filter_ignored(files: dict[str, Path], patterns: list[str]) -> dict[str, Path]:
    if not patterns:
        return files
    return {rel: fp for rel, fp in files.items()
            if not any(fnmatch.fnmatch(rel, p) for p in patterns)}


def collect_files(paths: list[str]) -> dict[str, Path]:
    from src.utils.path_expander import expand
    files: dict[str, Path] = {}
    for p in paths:
        expanded = expand(p)
        if expanded.exists():
            if expanded.is_file():
                files[expanded.name] = expanded
            elif expanded.is_dir():
                for f in expanded.rglob("*"):
                    if f.is_file():
                        rel = str(f.relative_to(expanded.parent))
                        files[rel] = f
    return files
