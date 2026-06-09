# -*- coding: utf-8 -*-
"""Capture backends for Recordrr.

Two interchangeable backends behind one tiny interface:
  - XvfbFfmpegCapturer (primary): ffmpeg x11grab off the Xvfb display + the
    PulseAudio null-sink monitor, GPU VAAPI encode. Headless, scriptable,
    background. This is the "light" path.
  - ObsCapturer (fallback, stub): drives a real OBS over obs-websocket for the
    case where a service blanks the Xvfb capture. Wired later; interface fixed
    now so the orchestrator never cares which backend it holds.

Both expose: start(outfile), stop(), and capture_for(outfile, seconds).

Note on ads: ffmpeg has no clean mid-file pause. Ad-skipping is done by
SEGMENTS — start() opens segment 0, pause() clean-stops the current segment at
ad start, resume() opens the next segment after the ad, and stop() concats every
segment (TS, -c copy) into the requested container. Both backends always encode
to an intermediate MPEG-TS per segment (in-band SPS/PPS + ADTS) so the concat is
a lossless byte-level copy with no re-encode and no A/V drift across the splice.
The orchestrator decides WHEN to pause/resume off the adapter's is_ad signal;
the capturer just owns the segment list.

Run standalone (POC):
    DISPLAY=:77 python3 -m Recordrr.modules.capture out.mkv 60
"""
import os
import subprocess
import sys
import time
from pathlib import Path

try:
    from Recordrr.config import recordrr_config as cfg
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
    from Recordrr.config import recordrr_config as cfg


class XvfbFfmpegCapturer:
    """ffmpeg x11grab + pulse monitor. VAAPI GPU encode, automatic software fallback.

    AMD/mesa VAAPI often can't write packed headers -> no H264 extradata -> the mkv
    muxer refuses. We dodge it by encoding VAAPI to MPEG-TS (in-band SPS/PPS), then
    remuxing -c copy into the requested container on stop(). If VAAPI probes bad, we
    fall back to libx264 so capture never dies.
    """

    _vaapi_ok = None  # cached one-shot capability probe (class-level)

    def __init__(self):
        self._proc = None
        self.outfile = None
        self._mode = None
        self._segments = []     # finished segment TS paths, in record order
        self._seg_work = None   # the segment TS currently being written
        self._seg_idx = 0

    @classmethod
    def vaapi_available(cls) -> bool:
        """Probe once whether h264_vaapi can actually encode on this box."""
        if cls._vaapi_ok is not None:
            return cls._vaapi_ok
        Path("/tmp/recordrr").mkdir(parents=True, exist_ok=True)
        probe = "/tmp/recordrr/vaapi_probe.ts"
        rc = subprocess.run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=10",
            "-vaapi_device", cfg.VAAPI_DEVICE,
            "-vf", "format=nv12,hwupload",
            "-c:v", "h264_vaapi", "-f", "mpegts", probe,
        ], capture_output=True).returncode
        cls._vaapi_ok = (rc == 0 and os.path.exists(probe) and os.path.getsize(probe) > 0)
        return cls._vaapi_ok

    def _route_audio(self):
        """Ensure the null sink exists and ALL playback is routed into it.

        Without this, Chrome may be on a different sink (or started before the
        sink existed) -> recording captures silence. Idempotent, best-effort.
        """
        try:
            from Recordrr.modules.display import start_pulse
            start_pulse()  # creates the null sink + starts pulse if needed
        except Exception:
            pass
        routed = 0
        try:
            subprocess.run(["pactl", "set-default-sink", cfg.PULSE_SINK], capture_output=True)
            # unmute + full volume on the sink itself (a muted sink records silence
            # even with audio routed in).
            subprocess.run(["pactl", "set-sink-mute", cfg.PULSE_SINK, "0"], capture_output=True)
            subprocess.run(["pactl", "set-sink-volume", cfg.PULSE_SINK, "100%"], capture_output=True)
            out = subprocess.run(["pactl", "list", "short", "sink-inputs"],
                                 capture_output=True, text=True)
            for line in out.stdout.splitlines():
                if not line.strip():
                    continue
                sid = line.split("\t")[0]
                subprocess.run(["pactl", "move-sink-input", sid, cfg.PULSE_SINK],
                               capture_output=True)
                # the player may have muted the stream at the Pulse layer too.
                subprocess.run(["pactl", "set-sink-input-mute", sid, "0"], capture_output=True)
                subprocess.run(["pactl", "set-sink-input-volume", sid, "100%"], capture_output=True)
                routed += 1
        except Exception:
            pass
        return routed

    def audio_routed(self) -> int:
        """Number of playback streams currently on the recordrr sink (0 = the
        recording will be SILENT). Cheap pre-flight check for the orchestrator."""
        try:
            out = subprocess.run(["pactl", "list", "short", "sink-inputs"],
                                 capture_output=True, text=True)
            return sum(1 for ln in out.stdout.splitlines() if ln.strip())
        except Exception:
            return -1

    def _inputs(self) -> list:
        monitor = f"{cfg.PULSE_SINK}.monitor"
        return [
            "ffmpeg", "-hide_banner", "-loglevel", "warning", "-y",
            "-thread_queue_size", "512",
            "-f", "x11grab", "-framerate", str(cfg.FRAMERATE),
            "-draw_mouse", "0",   # keep the cursor out of the recording (VNC still shows it)
            "-video_size", f"{cfg.SCREEN_W}x{cfg.SCREEN_H}", "-i", f"{cfg.DISPLAY}.0",
            "-thread_queue_size", "512",
            "-f", "pulse", "-i", monitor,
        ]

    def _vaapi_cmd(self, work_ts: str) -> list:
        return self._inputs() + [
            "-vaapi_device", cfg.VAAPI_DEVICE, "-vf", "format=nv12,hwupload",
            "-c:v", "h264_vaapi", "-qp", str(cfg.QP),
            "-c:a", cfg.AUDIO_CODEC, "-b:a", cfg.AUDIO_BITRATE,
            "-f", "mpegts", work_ts,
        ]

    def _sw_cmd(self, work_ts: str) -> list:
        # MPEG-TS (not the final container) so segments concat losslessly; the
        # final remux to the requested container happens in _finalize().
        return self._inputs() + [
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-c:a", cfg.AUDIO_CODEC, "-b:a", cfg.AUDIO_BITRATE,
            "-f", "mpegts", work_ts,
        ]

    def _segment_path(self, idx: int) -> str:
        return f"{self.outfile}.seg{idx:03d}.ts"

    def _spawn_segment(self):
        """Start ffmpeg writing the current segment's TS. stdin=PIPE so we can
        send 'q' for a clean stop that finalizes the segment."""
        work = self._segment_path(self._seg_idx)
        self._seg_work = work
        cmd = self._vaapi_cmd(work) if self._mode == "vaapi" else self._sw_cmd(work)
        # :99 is auth'd (Xvfb -auth, not -ac) to stop the host-app display leak;
        # x11grab must present the cookie or it can't grab the framebuffer.
        env = os.environ.copy()
        env.setdefault("XAUTHORITY", cfg.XAUTHORITY)
        self._proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, env=env)
        return self._proc.pid

    def _stop_proc(self, timeout: float = 10.0):
        """Clean-stop the running ffmpeg (sends 'q' to finalize the TS)."""
        if not self._proc:
            return
        try:
            if self._proc.poll() is None:
                self._proc.communicate(input=b"q", timeout=timeout)
        except subprocess.TimeoutExpired:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._proc.kill()
        finally:
            self._proc = None

    def _close_segment(self):
        """Stop the active segment and keep it if it holds real data."""
        self._stop_proc()
        if (self._seg_work and os.path.exists(self._seg_work)
                and os.path.getsize(self._seg_work) > 0):
            self._segments.append(self._seg_work)
        self._seg_work = None

    def start(self, outfile: str):
        """Begin recording (segment 0). Non-blocking; returns immediately."""
        outfile = str(outfile)
        Path(outfile).parent.mkdir(parents=True, exist_ok=True)
        self.outfile = outfile
        self._segments = []
        self._seg_idx = 0
        self._route_audio()  # force Chrome's audio into the recorded sink
        want_vaapi = cfg.VIDEO_CODEC.endswith("vaapi")
        self._mode = "vaapi" if (want_vaapi and self.vaapi_available()) else "sw"
        return self._spawn_segment()

    def pause(self):
        """Close the current segment to drop an ad break out of the file. The
        recording session stays open — resume() opens the next segment, stop()
        concats them. No-op if not currently recording a segment."""
        if not self._proc:
            return
        self._close_segment()

    def resume(self):
        """Open the next segment after pause(). Re-routes audio because an ad
        break can spawn a fresh Pulse sink-input. No-op if already recording."""
        if self._proc:
            return
        self._route_audio()
        self._seg_idx += 1
        return self._spawn_segment()

    def stop(self, timeout: float = 10.0):
        """Stop cleanly; concat all segments into the requested container."""
        if not self._proc and not self._segments and not self._seg_work:
            return
        if self._proc:
            self._close_segment()
        self._finalize()

    def _finalize(self):
        """Concat every segment TS -> requested container, lossless (-c copy)."""
        segs = [s for s in self._segments if os.path.exists(s)]
        if not segs:
            return
        listfile = None
        if len(segs) == 1:
            # no ads paused (or all dropped): straight remux of the lone segment
            subprocess.run([
                "ffmpeg", "-hide_banner", "-loglevel", "warning", "-y",
                "-i", segs[0], "-c", "copy", self.outfile,
            ], check=False)
        else:
            listfile = self.outfile + ".concat.txt"
            with open(listfile, "w") as f:
                for seg in segs:
                    # concat demuxer: a literal ' inside the quoted path must be
                    # written as '\'' or ffmpeg ends the path early (apostrophes in
                    # episode titles — "Neptune's Ocean" — silently lost E10 once).
                    safe = os.path.abspath(seg).replace("'", r"'\''")
                    f.write(f"file '{safe}'\n")
            subprocess.run([
                "ffmpeg", "-hide_banner", "-loglevel", "warning", "-y",
                "-f", "concat", "-safe", "0", "-i", listfile,
                "-c", "copy", self.outfile,
            ], check=False)
        # Preservation law: only drop the source segments once the muxed output
        # actually exists and is non-empty. If concat/remux failed, KEEP the .ts
        # (and the concat list) so the footage is recoverable by hand.
        ok = os.path.exists(self.outfile) and os.path.getsize(self.outfile) > 0
        if not ok:
            print(f"[recordrr] FINALIZE FAILED — keeping {len(segs)} segment(s) "
                  f"for manual recovery: {segs[0]} ...")
            return
        if listfile:
            try:
                os.remove(listfile)
            except OSError:
                pass
        for seg in segs:
            try:
                os.remove(seg)
            except OSError:
                pass
        self._segments = []
        self._seg_work = None

    def is_running(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def is_paused(self) -> bool:
        """Session open (segments captured) but no segment currently recording."""
        return self._proc is None and bool(self._segments)

    def capture_for(self, outfile: str, seconds: float):
        """Convenience: record a fixed duration, then stop cleanly."""
        self.start(outfile)
        time.sleep(seconds)
        self.stop()
        return outfile


class ObsCapturer:
    """Fallback backend: real OBS over obs-websocket. Wired in a later step."""

    def __init__(self):
        raise NotImplementedError(
            "OBS fallback backend not built yet — use the xvfb backend for the POC."
        )


def get_capturer(backend: str = None):
    backend = (backend or cfg.CAPTURE_BACKEND).lower()
    if backend == "obs":
        return ObsCapturer()
    return XvfbFfmpegCapturer()


def ffprobe(path: str) -> str:
    out = subprocess.run(
        ["ffprobe", "-hide_banner", "-v", "error",
         "-show_entries", "format=duration:stream=codec_type,codec_name,width,height,r_frame_rate",
         "-of", "default=noprint_wrappers=1", path],
        capture_output=True, text=True,
    )
    return out.stdout.strip() or out.stderr.strip()


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "/tmp/recordrr/poc.mkv"
    secs = float(sys.argv[2]) if len(sys.argv) > 2 else 60.0
    cfg.ensure_dirs()
    cap = get_capturer("xvfb")
    print(f"[recordrr] capturing {secs:.0f}s of {cfg.DISPLAY} -> {out}")
    cap.capture_for(out, secs)
    print(f"[recordrr] done. ffprobe:\n{ffprobe(out)}")
