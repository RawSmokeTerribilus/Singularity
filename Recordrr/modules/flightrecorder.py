# -*- coding: utf-8 -*-
"""Recordrr flight recorder — passive, always-on timeline of a record run.

The diag modules (audiodiag / layerdiag / probe) are STOP-AND-INSPECT: you re-run
a service and hope it misbehaves on cue. The flight recorder is the inverse — it
writes down the full signal vector on EVERY poll of a REAL record, plus a line for
every state transition, so a failure is read after the fact instead of reproduced.

Output = one JSON object per line (JSONL) in LOGS_DIR/flight/. Append-only and
flushed per write, so a crash (or a lost .mkv — see the E10 concat loss) still
leaves the complete timeline on disk. Provider-agnostic: the same vector is logged
for Pluto, Prime, HBO, anything — the analyzer (`flightcheck`, later) reads one
format.

Line types:
  session  header: run metadata + tunables in effect
  s        sample: per-poll {ct,dur,ended,paused,src,ad,aud,fit,seg,peak,res}
  e        event:  a transition (rec_start / ad_pause / boundary_* / runaway / ...)
  end      footer: final status + ffprobe duration of the muxed file

Contract: NOTHING here may raise into the record loop. Every public method swallows
its own errors; a recorder that can't open its file degrades to a silent no-op.

Standalone tail (human-readable) of a flight log:
    python3 -m Recordrr.modules.flightrecorder <flight.jsonl>
"""
import json
import os
import sys
import time
from pathlib import Path

try:
    from Recordrr.config import recordrr_config as cfg
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
    from Recordrr.config import recordrr_config as cfg


def _enabled() -> bool:
    return os.getenv("RECORDRR_FLIGHT", "1").lower() not in ("0", "false", "no", "off")


def _slug(text: str) -> str:
    keep = [c if (c.isalnum() or c in "-_") else "-" for c in str(text)]
    return "".join(keep).strip("-")[:60] or "rec"


class _NullRecorder:
    """No-op stand-in so the orchestrator can call the recorder unconditionally
    (flight logging disabled, or the log file could not be opened)."""
    path = None

    def session(self, **k):           pass
    def sample(self, **k):            pass
    def event(self, name, **k):       pass
    def close(self, **k):             pass
    def __enter__(self):              return self
    def __exit__(self, *a):           return False


class FlightRecorder:
    """Append-only JSONL writer for one episode's record run."""

    def __init__(self, path: Path, start_t: float):
        self._path = Path(path)
        self._start = start_t
        self._fh = open(self._path, "a", buffering=1)   # line-buffered

    @property
    def path(self):
        return self._path

    def _write(self, obj: dict):
        try:
            obj["t"] = round(time.time(), 3)
            obj.setdefault("s", round(time.time() - self._start, 1))
            self._fh.write(json.dumps(obj, ensure_ascii=False) + "\n")
            self._fh.flush()
        except Exception:
            pass   # logging must never break the record loop

    def session(self, **meta):
        meta["type"] = "session"
        self._write(meta)

    def sample(self, **fields):
        fields["type"] = "s"
        self._write(fields)

    def event(self, name, **fields):
        fields["type"] = "e"
        fields["ev"] = name
        self._write(fields)

    def close(self, **summary):
        summary["type"] = "end"
        self._write(summary)
        try:
            self._fh.close()
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        # belt: if the caller didn't close() (e.g. exception path), flush+close.
        try:
            self._fh.close()
        except Exception:
            pass
        return False


def open_recorder(ep_code: str, outfile: str, start_t: float):
    """Factory: a live FlightRecorder, or a silent _NullRecorder if disabled or
    the log dir/file can't be opened. Caller always gets a usable object."""
    if not _enabled():
        return _NullRecorder()
    try:
        flight_dir = Path(cfg.LOGS_DIR) / "flight"
        flight_dir.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y%m%d-%H%M%S")
        stem = _slug(Path(outfile).stem)
        path = flight_dir / f"flight_{ts}_{_slug(ep_code)}_{stem}.jsonl"
        return FlightRecorder(path, start_t)
    except Exception:
        return _NullRecorder()


def short_src(src) -> str:
    """Compact a (possibly blob:) media src to a stable tail for change detection."""
    if not src:
        return ""
    s = str(src)
    return s[-40:] if len(s) > 40 else s


# --------------------------------------------------------------------------
# Standalone: pretty-print a flight log (quick human read; flightcheck is the
# real analyzer, built next).
def _render(o):
    ty = o.get("type")
    s = o.get("s", "?")
    if ty == "session":
        print(f"== {o.get('show')} {o.get('ep')} — {o.get('title','')} "
              f"(expected {o.get('expected_runtime')}s, "
              f"reset>{o.get('boundary_reset')}s) -> {o.get('outfile')}")
    elif ty == "s":
        print(f"  [{s:>6}s] ct={o.get('ct')} dur={o.get('dur')} "
              f"end={o.get('end')} ad={o.get('ad')} aud={o.get('aud')} "
              f"fit={o.get('fit')} seg={o.get('seg')} peak={o.get('peak')} "
              f"res={o.get('res')} src…{o.get('src')}")
    elif ty == "e":
        extra = " ".join(f"{k}={v}" for k, v in o.items()
                         if k not in ("type", "ev", "t", "s"))
        print(f"  [{s:>6}s] * {o.get('ev')} {extra}")
    elif ty == "end":
        print(f"== END status={o.get('status')} reason={o.get('reason')} "
              f"out_dur={o.get('out_dur')} size_mb={o.get('size_mb')} "
              f"ads={o.get('ads_seen')} segs={o.get('segments')}")


def _follow(path):
    """Live-stream a flight log as it's written (tail -f, pretty). Reads from the
    top, then blocks for new lines. Stops on the 'end' record or Ctrl-C. Safe to
    run in a second terminal while a record is in flight — read-only, never
    touches the capture."""
    import time
    with open(path) as f:
        buf = ""
        while True:
            chunk = f.readline()
            if not chunk:
                time.sleep(0.5)
                continue
            buf += chunk
            if not buf.endswith("\n"):
                continue                       # half-written line; wait for the rest
            line, buf = buf.strip(), ""
            if not line:
                continue
            try:
                o = json.loads(line)
            except json.JSONDecodeError:
                print(f"  ?? {line}")
                continue
            _render(o)
            if o.get("type") == "end":
                return


def _tail(path):
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                o = json.loads(line)
            except json.JSONDecodeError:
                print(f"  ?? {line}")
                continue
            ty = o.get("type")
            s = o.get("s", "?")
            if ty == "session":
                print(f"== {o.get('show')} {o.get('ep')} — {o.get('title','')} "
                      f"(expected {o.get('expected_runtime')}s, "
                      f"reset>{o.get('boundary_reset')}s) -> {o.get('outfile')}")
            elif ty == "s":
                print(f"  [{s:>6}s] ct={o.get('ct')} dur={o.get('dur')} "
                      f"end={o.get('end')} ad={o.get('ad')} aud={o.get('aud')} "
                      f"fit={o.get('fit')} seg={o.get('seg')} peak={o.get('peak')} "
                      f"res={o.get('res')} src…{o.get('src')}")
            elif ty == "e":
                extra = " ".join(f"{k}={v}" for k, v in o.items()
                                 if k not in ("type", "ev", "t", "s"))
                print(f"  [{s:>6}s] * {o.get('ev')} {extra}")
            elif ty == "end":
                print(f"== END status={o.get('status')} reason={o.get('reason')} "
                      f"out_dur={o.get('out_dur')} size_mb={o.get('size_mb')} "
                      f"ads={o.get('ads_seen')} segs={o.get('segments')}")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a not in ("-f", "--follow")]
    follow = len(args) != len(sys.argv[1:])
    if not args:
        # no path → newest log in LOGS_DIR/flight (handy mid-record: just -f)
        try:
            from Recordrr.config import recordrr_config as cfg
            logs = sorted(Path(cfg.LOGS_DIR / "flight").glob("*.jsonl"),
                          key=lambda p: p.stat().st_mtime)
            args = [str(logs[-1])] if logs else []
        except Exception:
            args = []
    if not args:
        print("usage: python3 -m Recordrr.modules.flightrecorder [-f] [<flight.jsonl>]")
        sys.exit(1)
    try:
        (_follow if follow else _tail)(args[0])
    except KeyboardInterrupt:
        pass
