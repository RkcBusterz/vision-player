import os
import sys

script_dir = os.path.dirname(os.path.abspath(__file__))
if hasattr(os, "add_dll_directory"):
    try:
        os.add_dll_directory(script_dir)
    except Exception:
        pass
os.environ["PATH"] = script_dir + os.pathsep + os.environ.get("PATH", "")

import mpv
from PyQt6.QtCore import QObject, pyqtSignal

class EngineSignals(QObject):
    time_updated = pyqtSignal(float)
    duration_changed = pyqtSignal(float)
    playback_state_changed = pyqtSignal(bool)
    audio_tracks_found = pyqtSignal(list)
    audio_track_changed = pyqtSignal(int)
    subtitle_tracks_found = pyqtSignal(list)
    subtitle_track_changed = pyqtSignal(object)
    playback_ended = pyqtSignal()

class MPVEngine:
    def __init__(self, win_id: int):
        self.signals = EngineSignals()
        self.current_file = None
        self.duration = 0.0
        self._last_track_signature = None
        self._last_sub_signature = None

        self.player = mpv.MPV(
            wid=str(win_id),
            vo="gpu",
            hwdec="auto",
            demuxer_max_bytes="32MiB",
            demuxer_max_back_bytes="0MiB",
            cache="yes",
            cache_secs="2.0",
            audio_display="no",
            af="scaletempo2",
            input_default_bindings="no",
            input_vo_keyboard="no",
            osc="no",
            keep_open="yes"
        )

        @self.player.property_observer('time-pos')
        def on_time_pos(_name, value):
            if value is not None:
                self.signals.time_updated.emit(float(value))

        @self.player.property_observer('duration')
        def on_duration(_name, value):
            if value is not None and value > 0:
                self.duration = float(value)
                self.signals.duration_changed.emit(self.duration)

        @self.player.property_observer('pause')
        def on_pause(_name, is_paused):
            if is_paused is not None:
                self.signals.playback_state_changed.emit(not bool(is_paused))

        @self.player.property_observer('aid')
        def on_aid(_name, value):
            if isinstance(value, int):
                self.signals.audio_track_changed.emit(value)

        @self.player.property_observer('sid')
        def on_sid(_name, value):
            if isinstance(value, int):
                self.signals.subtitle_track_changed.emit(value)
            else:
                self.signals.subtitle_track_changed.emit(None)

        @self.player.property_observer('track-list')
        def on_track_list(_name, tracks):
            if not tracks:
                return
            audio_tracks = []
            selected_audio_id = None
            sub_tracks = []
            selected_sub_id = None

            for t in tracks:
                track_type = t.get('type')
                track_id = t.get('id', 1)
                lang = t.get('lang', '').upper()
                title = t.get('title', '')

                if track_type == 'audio':
                    label = f"Audio {track_id}"
                    if lang:
                        label += f" ({lang})"
                    elif title:
                        label += f" ({title[:12]})"
                    audio_tracks.append({"id": track_id, "label": label})
                    if t.get('selected'):
                        selected_audio_id = track_id
                elif track_type == 'sub':
                    label = f"Sub {track_id}"
                    if lang and title:
                        label += f" ({lang} - {title[:14]})"
                    elif lang:
                        label += f" ({lang})"
                    elif title:
                        label += f" ({title[:18]})"
                    sub_tracks.append({"id": track_id, "label": label})
                    if t.get('selected'):
                        selected_sub_id = track_id

            if not audio_tracks:
                audio_tracks = [{"id": 1, "label": "Default Audio"}]

            sig = tuple((t["id"], t["label"]) for t in audio_tracks)
            if sig != self._last_track_signature:
                self._last_track_signature = sig
                self.signals.audio_tracks_found.emit(audio_tracks)

            if selected_audio_id is not None:
                self.signals.audio_track_changed.emit(int(selected_audio_id))

            sub_sig = tuple((t["id"], t["label"]) for t in sub_tracks)
            if sub_sig != self._last_sub_signature:
                self._last_sub_signature = sub_sig
                self.signals.subtitle_tracks_found.emit(sub_tracks)

            if selected_sub_id is not None:
                self.signals.subtitle_track_changed.emit(int(selected_sub_id))
            elif getattr(self.player, 'sid', None) in ('no', False, None):
                self.signals.subtitle_track_changed.emit(None)

        @self.player.event_callback('playback-restart')
        def on_playback_restart(event):
            self.signals.playback_state_changed.emit(not bool(self.player.pause))

        @self.player.event_callback('end-file')
        def on_end_file(event):
            reason = getattr(event, 'reason', None)
            if reason in (0, 'eof', 'EOF') or (hasattr(reason, 'value') and reason.value == 0):
                self.signals.playback_ended.emit()

    def set_memory_mode(self, mode: str):
        """
        Dynamically adjusts mpv's memory caching and demuxer buffers:
          - Low: 0-200MB (16MiB forward, 0MiB back, 1.0s cache)
          - Medium: 0-400MB (64MiB forward, 32MiB back, 5.0s cache)
          - High: 0-800MB (256MiB forward, 128MiB back, 15.0s cache)
        """
        mode = (mode or "medium").lower()
        try:
            if mode == "low":
                self.player.demuxer_max_bytes = "16MiB"
                self.player.demuxer_max_back_bytes = "0MiB"
                self.player.cache_secs = 1.0
            elif mode == "high":
                self.player.demuxer_max_bytes = "256MiB"
                self.player.demuxer_max_back_bytes = "128MiB"
                self.player.cache_secs = 15.0
            else:
                self.player.demuxer_max_bytes = "64MiB"
                self.player.demuxer_max_back_bytes = "32MiB"
                self.player.cache_secs = 5.0
        except Exception:
            pass

    def load_file(self, file_path: str, autoplay: bool = True):
        
        self.current_file = file_path
        self._last_track_signature = None
        self._last_sub_signature = None
        self.player.play(file_path)
        self.player.pause = not autoplay
        self.signals.playback_state_changed.emit(autoplay)

    def toggle_play(self):
        if not self.current_file:
            return
        self.player.pause = not self.player.pause

    def seek(self, target_seconds: float, exact: bool = True):
        if self.current_file and self.duration > 0:
            target = max(0.0, min(target_seconds, self.duration))
            mode = "exact" if exact else "keyframes"
            self.player.command("seek", target, "absolute", mode)

    def seek_relative(self, delta_seconds: float):
        if self.current_file:
            self.player.command("seek", delta_seconds, "relative", "exact")

    def set_speed(self, speed: float):
        self.player.speed = max(0.3, min(speed, 3.0))

    def set_audio_track(self, track_id: int):
        if self.current_file:
            try:
                self.player.aid = int(track_id)
            except Exception:
                pass

    def set_subtitle_track(self, track_id):
        if self.current_file:
            try:
                if track_id is None or track_id == 0 or track_id == 'no':
                    self.player.sid = 'no'
                else:
                    self.player.sid = int(track_id)
            except Exception:
                pass

    def add_subtitle_file(self, file_path: str) -> bool:
        if self.current_file and os.path.exists(file_path):
            try:
                self.player.command("sub-add", file_path, "select")
                return True
            except Exception:
                pass
        return False

    def adjust_sub_delay(self, delta: float) -> float:
        if self.current_file:
            try:
                cur = float(getattr(self.player, 'sub_delay', 0.0) or 0.0)
                new_delay = round(cur + delta, 2)
                self.player.sub_delay = new_delay
                return new_delay
            except Exception:
                pass
        return 0.0

    def reset_sub_delay(self):
        if self.current_file:
            try:
                self.player.sub_delay = 0.0
            except Exception:
                pass

    def get_stats(self) -> dict:
        if not self.current_file:
            return {}

        ram_mb = 0.0
        try:
            import ctypes
            from ctypes import wintypes
            class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
                _fields_ = [
                    ('cb', wintypes.DWORD),
                    ('PageFaultCount', wintypes.DWORD),
                    ('PeakWorkingSetSize', ctypes.c_size_t),
                    ('WorkingSetSize', ctypes.c_size_t),
                    ('QuotaPeakPagedPoolUsage', ctypes.c_size_t),
                    ('QuotaPagedPoolUsage', ctypes.c_size_t),
                    ('QuotaPeakNonPagedPoolUsage', ctypes.c_size_t),
                    ('QuotaNonPagedPoolUsage', ctypes.c_size_t),
                    ('PagefileUsage', ctypes.c_size_t),
                    ('PeakPagefileUsage', ctypes.c_size_t),
                ]
            kernel32 = ctypes.windll.kernel32
            hProcess = kernel32.OpenProcess(0x0400 | 0x0010, False, os.getpid())
            pmc = PROCESS_MEMORY_COUNTERS()
            pmc.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
            if kernel32.K32GetProcessMemoryInfo(hProcess, ctypes.byref(pmc), pmc.cb):
                ram_mb = round(pmc.WorkingSetSize / (1024 * 1024), 1)
            kernel32.CloseHandle(hProcess)
        except Exception:
            pass

        cache_mb = 0.0
        cache_secs = 0.0
        try:
            cache = getattr(self.player, 'demuxer_cache_state', None)
            if isinstance(cache, dict):
                cache_mb = round(cache.get('fw-bytes', 0) / (1024 * 1024), 2)
                cache_secs = round(cache.get('fw-sec', 0.0) or 0.0, 1)
        except Exception:
            pass

        file_size_str = "Unknown"
        try:
            if os.path.exists(self.current_file):
                size_b = os.path.getsize(self.current_file)
                if size_b >= 1024 * 1024 * 1024:
                    file_size_str = f"{size_b / (1024**3):.2f} GB"
                elif size_b >= 1024 * 1024:
                    file_size_str = f"{size_b / (1024**2):.1f} MB"
                else:
                    file_size_str = f"{size_b / 1024:.1f} KB"
        except Exception:
            pass

        w = getattr(self.player, 'width', None)
        h = getattr(self.player, 'height', None)
        resolution = f"{w} × {h}" if w and h else "Unknown"

        v_codec = getattr(self.player, 'video_format', None) or getattr(self.player, 'video_codec', None) or "None"
        a_codec = getattr(self.player, 'audio_codec_name', None) or getattr(self.player, 'audio_format', None) or "None"
        fps = getattr(self.player, 'estimated_vf_fps', None) or getattr(self.player, 'container_fps', None)
        fps_str = f"{fps:.2f} FPS" if isinstance(fps, (int, float)) and fps > 0 else "Unknown"

        hwdec = getattr(self.player, 'hwdec_current', None)
        hwdec_str = f"{hwdec} (GPU Active)" if hwdec and hwdec != 'no' else "Software (CPU)"

        cur_frame = getattr(self.player, 'estimated_frame_number', None)
        total_frames = getattr(self.player, 'estimated_frame_count', None)
        if cur_frame is not None and total_frames is not None and total_frames > 0:
            frames_str = f"{cur_frame:,} / {total_frames:,}"
        elif cur_frame is not None:
            frames_str = f"{cur_frame:,}"
        else:
            frames_str = "Unavailable"

        dropped = getattr(self.player, 'frame_drop_count', 0) or 0
        v_bitrate = getattr(self.player, 'video_bitrate', None)
        v_br_str = f"{int(v_bitrate / 1000):,} kbps" if v_bitrate else "Variable"
        a_bitrate = getattr(self.player, 'audio_bitrate', None)
        a_br_str = f"{int(a_bitrate / 1000):,} kbps" if a_bitrate else "Variable"

        v_params = getattr(self.player, 'video_params', {}) or {}
        pix_fmt = v_params.get('pixelformat', 'Unknown')

        a_params = getattr(self.player, 'audio_params', {}) or {}
        sample_rate = a_params.get('samplerate', None)
        sr_str = f"{sample_rate:,} Hz" if sample_rate else "Unknown"
        channels = a_params.get('channel-count', None) or a_params.get('channels', 'Unknown')

        return {
            "file_name": os.path.basename(self.current_file),
            "file_path": self.current_file,
            "file_size": file_size_str,
            "container": getattr(self.player, 'file_format', 'Unknown') or 'Unknown',
            "resolution": resolution,
            "video_codec": str(v_codec).upper(),
            "pixel_format": str(pix_fmt),
            "fps": fps_str,
            "hwdec": hwdec_str,
            "video_bitrate": v_br_str,
            "frames": frames_str,
            "dropped_frames": f"{dropped:,}",
            "audio_codec": str(a_codec).upper(),
            "channels": f"{channels} Channels" if str(channels).isdigit() else str(channels),
            "sample_rate": sr_str,
            "audio_bitrate": a_br_str,
            "process_ram": f"{ram_mb} MB",
            "cache_buffer": f"{cache_mb} MB ({cache_secs}s)",
            "speed": f"{getattr(self.player, 'speed', 1.0):.2f}x"
        }

    def terminate(self):
        try:
            self.player.terminate()
        except Exception:
            pass
