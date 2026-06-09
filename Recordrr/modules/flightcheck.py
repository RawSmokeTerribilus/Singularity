# -*- coding: utf-8 -*-
"""Recordrr flightcheck — offline analyzer for flight-recorder logs.

Reads a flight .jsonl (or a dir / glob of them) and turns each into a one-line
VERDICT, so a 90-minute file becomes a sentence instead of an archaeology dig.
Provider-agnostic: it reads the signal vector the flight recorder wrote, not
anything Pluto-specific.

Verdicts (worst wins):
  OK        finished on a real boundary, duration ~ expected, audio held
  CLEAN-OP  operator stopped it deliberately; duration plausible
  MERGED    duration ~ a whole multiple of expected → two+ episodes welded
            (the E01 "two clean eps in one file" case)
  RUNAWAY   hit the runtime guard — boundary detection never fired
  LONG      well over expected but not a clean multiple (ad-sea / overrun)
  SHORT     well under expected → truncated / aborted / no-playback
  MUTE      a sustained silent stretch was recorded
  RESDROP   resolution fell below the run's own best (quality loss)
  ERROR     finalize failed / no output duration

Flags (MUTE / RESDROP / ADSEA) are additive notes appended to the line.

Usage:
  python3 -m Recordrr.modules.flightcheck                  # scan LOGS_DIR/flight
  python3 -m Recordrr.modules.flightcheck <file.jsonl> ... # specific logs
  python3 -m Recordrr.modules.flightcheck -v <file.jsonl>  # + per-finding detail
"""
import glob
import json
import sys
from pathlib import Path

try:
    from Recordrr.config import recordrr_config as cfg
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
    from Recordrr.config import recordrr_config as cfg

# A silent stretch this many consecutive content samples long = a real MUTE
# (one stray false reading during an unmute reassert shouldn't trip it).
MUTE_RUN = 3
# duration tolerance around expected for a "clean" verdict
SHORT_FACTOR = 0.5
OK_HIGH = 1.20
# within this of an integer multiple (2x, 3x...) of expected = welded episodes
MERGE_TOL = 0.18
# RESDROP needs this many content samples below the dominant res. A single stray
# high/low sample = an ad frame whose ad-marker was missed on one poll (the
# ad/content boundary lands on one wrong sample at ad_poll=1), not real loss.
RESDROP_RUN = 3


def load(path):
    """Parse a flight .jsonl into (session, samples, events, end). Tolerant of
    truncated/garbage lines (a crashed run may leave a half-written tail)."""
    session, end = {}, {}
    samples, events = [], []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                o = json.loads(line)
            except json.JSONDecodeError:
                continue
            ty = o.get("type")
            if ty == "session":
                session = o
            elif ty == "s":
                samples.append(o)
            elif ty == "e":
                events.append(o)
            elif ty == "end":
                end = o
    return session, samples, events, end


def analyze(path):
    session, samples, events, end = load(path)
    ev_names = [e.get("ev") for e in events]
    expected = session.get("expected_runtime") or 0
    status = end.get("status", "?")
    reason = end.get("reason", "?")
    out_dur = end.get("out_dur")
    # fall back to the deepest content position if the file never muxed
    peak = max((s.get("peak") or 0) for s in samples) if samples else 0

    flags = []
    detail = []

    # ---- audio: longest run of content (non-ad) samples reading aud is False ----
    run = worst_run = 0
    for s in samples:
        if s.get("ad"):
            continue
        if s.get("aud") is False:
            run += 1
            worst_run = max(worst_run, run)
        else:
            run = 0
    reasserts = ev_names.count("audio_reassert")
    if worst_run >= MUTE_RUN:
        flags.append("MUTE")
        detail.append(f"silent stretch ~{worst_run} polls (audio_reassert×{reasserts})")
    elif reasserts:
        detail.append(f"audio recovered (reassert×{reasserts})")

    # ---- resolution: did CONTENT ever drop below the best content seen? ----
    # Skip ad samples — ad creatives often come in at a DIFFERENT (sometimes
    # higher) resolution than the show (Pluto: ads 1024x576, content 854x480),
    # which would false-flag the show itself as a drop.
    res_h = []
    for s in samples:
        if s.get("ad"):
            continue
        r = s.get("res")
        if r and "x" in str(r):
            try:
                res_h.append(int(str(r).split("x")[1]))
            except ValueError:
                pass
    if res_h:
        # Baseline is the DOMINANT content res, not max — one stray high frame
        # (an undetected ad edge) must not redefine "best" and turn the whole
        # show into a drop. Flag only if RESDROP_RUN+ samples fall below it.
        baseline = max(set(res_h), key=res_h.count)
        below = [h for h in res_h if h < baseline]
        if len(below) >= RESDROP_RUN:
            flags.append("RESDROP")
            detail.append(f"res {baseline}p → {min(below)}p mid-run ({len(below)} samples)")

    # ---- ad load ----
    ads = end.get("ads_seen", ev_names.count("ad_pause"))
    ad_samples = sum(1 for s in samples if s.get("ad"))
    content_samples = sum(1 for s in samples if not s.get("ad")) or 1
    if ad_samples and ad_samples / (ad_samples + content_samples) > 0.4:
        flags.append("ADSEA")
        detail.append(f"ad-time ~{100*ad_samples//(ad_samples+content_samples)}% of polls")

    # ---- live-TV note: the EPG index missed → clock-named file (still a valid
    # recording, just not auto-named from the guide). Additive flag. ----
    mode = session.get("mode")
    source = session.get("source")
    if mode == "live" and source == "clock":
        flags.append("GUIDE-MISS")
        detail.append("no EPG program resolved — named by wall-clock fallback")

    # ---- primary verdict (worst wins) ----
    dur = out_dur if out_dur else peak
    verdict = "OK"
    if status == "ERROR" or out_dur is None:
        verdict = "ERROR"
        detail.append(f"finalize/out_dur missing (reason={reason})")
    elif reason == "runaway":
        verdict = "RUNAWAY"
        detail.append("runtime guard tripped — boundary never fired")
    elif mode == "live":
        # Live verdicts: the EPG `stop` is authoritative, and a program is often
        # joined mid-way (you press REC partway in), so a SHORT/MERGED ratio test
        # is meaningless. A clean program-boundary cut is OK regardless of length;
        # an overrun well past the boundary still flags LONG.
        if reason == "operator_stop":
            verdict = "CLEAN-OP"
        elif reason == "program_boundary":
            verdict = "OK"
        elif expected and dur and dur > expected * OK_HIGH:
            verdict = "LONG"
            detail.append(f"{int(dur)}s past EPG boundary (expected ~{int(expected)}s)")
    elif expected and dur:
        ratio = dur / expected
        mult = round(ratio)
        if ratio < SHORT_FACTOR:
            verdict = "SHORT"
            detail.append(f"{int(dur)}s vs expected {int(expected)}s (×{ratio:.2f})")
        elif mult >= 2 and abs(ratio - mult) <= MERGE_TOL:
            verdict = "MERGED"
            detail.append(f"{int(dur)}s ≈ {mult}× expected {int(expected)}s — welded episodes")
        elif ratio > OK_HIGH:
            verdict = "LONG"
            detail.append(f"{int(dur)}s vs expected {int(expected)}s (×{ratio:.2f})")
        elif reason == "operator_stop":
            verdict = "CLEAN-OP"
    elif reason == "operator_stop":
        verdict = "CLEAN-OP"

    return {
        "file": Path(path).name,
        "ep": session.get("ep", "?"),
        "show": session.get("show", "?"),
        "verdict": verdict,
        "reason": reason,
        "expected": expected,
        "out_dur": out_dur,
        "peak": round(peak, 1),
        "ads": ads,
        "flags": flags,
        "detail": detail,
        "n_samples": len(samples),
    }


_ICON = {"OK": "✓", "CLEAN-OP": "✓", "MERGED": "✗", "RUNAWAY": "✗",
         "LONG": "⚠", "SHORT": "⚠", "ERROR": "✗"}


def _line(a):
    icon = _ICON.get(a["verdict"], "•")
    dur = f"{int(a['out_dur'])}s" if a["out_dur"] else f"~{int(a['peak'])}s(no-mux)"
    exp = f"/{int(a['expected'])}s" if a["expected"] else ""
    flags = (" [" + ",".join(a["flags"]) + "]") if a["flags"] else ""
    return (f"{icon} {a['verdict']:<8} {a['ep']:<7} {dur}{exp} "
            f"reason={a['reason']} ads={a['ads']}{flags}  {a['file']}")


def _resolve(args):
    """Expand file/dir/glob args into a sorted list of .jsonl paths. No args =
    scan LOGS_DIR/flight."""
    if not args:
        args = [str(Path(cfg.LOGS_DIR) / "flight")]
    out = []
    for a in args:
        p = Path(a)
        if p.is_dir():
            out += sorted(str(x) for x in p.glob("*.jsonl"))
        elif any(c in a for c in "*?["):
            out += sorted(glob.glob(a))
        elif p.exists():
            out.append(str(p))
    return out


def main(argv):
    verbose = False
    files = []
    for a in argv:
        if a in ("-v", "--verbose"):
            verbose = True
        else:
            files.append(a)
    paths = _resolve(files)
    if not paths:
        print("flightcheck: no flight logs found "
              f"(looked in {Path(cfg.LOGS_DIR) / 'flight'}).")
        return 1
    bad = 0
    for p in paths:
        try:
            a = analyze(p)
        except Exception as e:
            print(f"✗ unreadable  {Path(p).name}: {e}")
            bad += 1
            continue
        print(_line(a))
        if a["verdict"] not in ("OK", "CLEAN-OP"):
            bad += 1
        if verbose:
            for d in a["detail"]:
                print(f"      - {d}")
    print(f"\n{len(paths)} log(s), {bad} need attention.")
    return 0 if bad == 0 else 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
