import json
import os

STATE_FILE_NAME = "app_state.json"

def get_state_file_path() -> str:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(script_dir, STATE_FILE_NAME)

def load_app_state() -> dict:
    """
    Loads saved playback state: last file played, last timestamp, and current playlist.
    """
    path = get_state_file_path()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception:
            pass
    return {
        "last_file": None,
        "last_timestamp": 0.0,
        "playlist": [],
        "playlist_index": 0,
        "memory_mode": "medium",
        "ambient_mode": "dot",
        "resume_where_left": False,
        "open_in_fullscreen": False,
        "autoplay_on_open": True,
        "file_positions": {}
    }

def save_app_state(
    file_path: str | None,
    timestamp: float,
    playlist: list[str] = None,
    playlist_index: int = 0,
    memory_mode: str = "medium",
    ambient_mode: str = "dot",
    resume_where_left: bool = False,
    open_in_fullscreen: bool = False,
    autoplay_on_open: bool = True,
    file_positions: dict = None
):
    """
    Saves app state JSON file in the same folder as main.py.
    """
    path = get_state_file_path()
    try:
        data = {
            "last_file": file_path,
            "last_timestamp": round(max(0.0, float(timestamp)), 2),
            "playlist": playlist or [],
            "playlist_index": max(0, int(playlist_index)),
            "memory_mode": str(memory_mode or "medium").lower(),
            "ambient_mode": str(ambient_mode or "dot").lower(),
            "resume_where_left": bool(resume_where_left),
            "open_in_fullscreen": bool(open_in_fullscreen),
            "autoplay_on_open": bool(autoplay_on_open),
            "file_positions": file_positions or {}
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass

