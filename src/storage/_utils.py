from typing import Iterable
from src.storage.base import BackupSession


def build_sessions_from_meta(metas: Iterable[dict]) -> list[BackupSession]:
    session_map: dict[str, dict] = {}
    for meta in metas:
        sid = meta.get("session_id", meta["backup_id"])
        if sid not in session_map:
            session_map[sid] = {
                "session_id": sid,
                "timestamp": meta["timestamp"],
                "note": meta.get("note", ""),
                "config_names": [],
            }
        cfg_name = meta.get("config_name", "")
        if cfg_name not in session_map[sid]["config_names"]:
            session_map[sid]["config_names"].append(cfg_name)
    sessions = []
    for s in sorted(session_map.values(), key=lambda x: x["timestamp"], reverse=True):
        sessions.append(BackupSession(
            session_id=s["session_id"],
            timestamp=s["timestamp"],
            note=s["note"],
            config_names=s["config_names"],
        ))
    return sessions
