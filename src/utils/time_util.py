from datetime import datetime


def utc_to_local(utc_str: str, fmt: str = "%Y-%m-%d %H:%M") -> str:
    try:
        s = utc_str.replace("Z", "+00:00")
        if "+" not in s and s.count("-") == 2:
            s += "+00:00"
        dt = datetime.fromisoformat(s)
        local = dt.astimezone()
        return local.strftime(fmt)
    except Exception:
        return utc_str[:16].replace("T", " ")
