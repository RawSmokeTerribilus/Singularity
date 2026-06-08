# -*- coding: utf-8 -*-
"""Recordrr orchestrator — season record loop.

v1 flow (semi-auto, the big step up from manual): you log in once and start the
first episode in the VNC view; the orchestrator then records each episode to a
named file, detects end-of-episode from the <video> element, advances via the
adapter's next_episode control (or the service's autoplay), and repeats for the
season — naming + runtime guard rails from Sonarr.

Service navigation (search show -> pick episode) is adapter/service-specific and
deferred; attaching to live playback keeps v1 robust and useful now.

Everything tunable lives in config (env) + the adapter JSON (timing block):
  play_settle, ad_poll, end_pad, max_runtime_factor.

Run:
  python3 -m Recordrr.modules.orchestrator "Show Name" \
      --adapter pluto --season 1 --start 1 --count 5 --profile pluto
"""
import argparse
import os
import select
import sys
import time
from pathlib import Path

try:
    from Recordrr.config import recordrr_config as cfg
    from Recordrr.modules.browser import RecordrrBrowser
    from Recordrr.modules.capture import get_capturer, ffprobe
    from Recordrr.modules.adapter import Adapter
    from Recordrr.modules.metadata import SonarrClient
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
    from Recordrr.config import recordrr_config as cfg
    from Recordrr.modules.browser import RecordrrBrowser
    from Recordrr.modules.capture import get_capturer, ffprobe
    from Recordrr.modules.adapter import Adapter
    from Recordrr.modules.metadata import SonarrClient

try:
    from core.status_manager import update_status
except Exception:
    def update_status(*a, **k):
        pass


def _log(msg):
    print(f"[recordrr] {msg}", flush=True)


class _KeyPoll:
    """Non-blocking single-key reader over a tty, so the operator can stop a
    recording with a keystroke ('q') instead of Ctrl-C — Ctrl-C's SIGINT hits the
    whole Singularity process group and kicks them out of the app entirely.

    No-ops gracefully when stdin is not a tty (piped/no terminal)."""
    def __init__(self):
        self.fd = None
        self._saved = None

    def __enter__(self):
        try:
            import termios, tty
            self.fd = sys.stdin.fileno()
            self._saved = termios.tcgetattr(self.fd)
            tty.setcbreak(self.fd)          # char-at-a-time, no Enter needed
        except Exception:
            self.fd = None                   # not a tty → polling disabled
        return self

    def get(self):
        if self.fd is None:
            return None
        try:
            if select.select([sys.stdin], [], [], 0)[0]:
                return os.read(self.fd, 1).decode(errors="ignore")
        except Exception:
            return None
        return None

    def __exit__(self, *a):
        if self.fd is not None and self._saved is not None:
            try:
                import termios
                termios.tcsetattr(self.fd, termios.TCSADRAIN, self._saved)
            except Exception:
                pass


class Orchestrator:
    def __init__(self, show, episodes, adapter, browser, profile="default"):
        self.show = show
        self.episodes = episodes          # list[metadata.Episode]
        self.adapter = adapter
        self.browser = browser
        self.profile = profile
        self.cap = get_capturer()
        t = adapter.timing
        self.play_settle = float(t.get("play_settle", 8))
        self.ad_poll = float(t.get("ad_poll", 3))
        self.end_pad = float(t.get("end_pad", 2))
        self.max_factor = float(t.get("max_runtime_factor", 2.2))
        self.play_wait = float(t.get("play_wait", 300))      # per-episode playback wait
        self.login_wait = float(t.get("login_wait", 900))    # first ep: login+nav window
        self.stop = False                                     # set by the 'q' stop key

    # ---- start gate ------------------------------------------------------
    def _wait_for_rec(self, timeout) -> bool:
        """Block until the operator clicks ⏺ REC on the in-page bar (or 'q' to
        abort). This — not playback auto-detect — is the start signal: it stops
        Recordrr from grabbing the landing-page promo/autoplay that plays while
        the operator is still dismissing cookies and navigating."""
        self.browser.bar_status("idle")
        deadline = time.time() + timeout
        with _KeyPoll() as keys:
            while time.time() < deadline:
                if self.browser.bar_cmd() == "rec":
                    return True
                if keys.get() in ("q", "Q"):
                    self.stop = True
                    return False
                time.sleep(0.4)
        return False

    # ---- audio guarantee -------------------------------------------------
    def _blur_active(self):
        """Drop focus off any bar button so a player keybind ('m'/'f') lands on
        the PLAYER, not our injected control (a focused REC button swallowed the
        'm' press → auto-unmute silently no-op'd)."""
        try:
            self.browser.page.evaluate(
                "() => { const a=document.activeElement;"
                " if(a && a!==document.body && a.blur) a.blur(); }")
        except Exception:
            pass

    def _ensure_audible(self):
        """Guarantee audio AND keep it durable. Two coupled layers:
          (a) ELEMENT property — `video.muted=false; volume=1` opens audio to the
              Pulse sink right now (this is what actually records sound);
          (b) the player's REAL control — drive the player's own mute state (the
              on-screen icon) so UI and element AGREE. A decoupled state (element
              unmuted, player thinks muted) is fragile: the player can re-sync its
              stale 'muted' state onto the element on an ad/seek/episode change and
              silently kill audio mid-record.

        We read the player's real state via `adapter.mute_state()` and only press
        the mute keybind while it's actually muted — a blind press would re-mute an
        audible stream. When the player exposes no readable mute control we fall
        back to the element-level `is_audible()` check. Pulse-sink unmute happens
        separately in `cap.start()`."""
        page = self.browser.page
        self._blur_active()
        self.browser.unmute()                       # (a) element: records now
        for _ in range(3):
            ui = self.adapter.mute_state(page)      # (b) player's REAL state
            if ui is False:                         # player says unmuted → agree
                self.browser.unmute()               # belt: keep element open too
                return
            if ui is None and self.browser.is_audible():
                return                              # no UI signal; element audible
            self.browser.press(self.adapter.mute_key)   # 'm' trusted → flip real control
            time.sleep(0.5)
            self.browser.unmute()                        # re-assert element each pass
        # last resort: click the control directly, then re-open the element
        if self.adapter.mute_state(page) is not False and not self.browser.is_audible():
            self.adapter.click(page, "unmute")
            self.browser.unmute()

    def _ensure_fitted(self):
        """Guarantee a CLEAN capture frame = the player in the browser Fullscreen
        state (Chrome's toolbar hidden, video filling). On this WM-less display
        --kiosk can't hide the chrome, so without this the url bar bakes into the
        file and the operator has to hit F11 by hand — and fullscreen DROPS on
        navigation / episode-change / some ads, so it must be re-asserted.

        Mirrors _ensure_audible: read state first, act ONLY when not fitted. A
        blind fullscreen toggle would EXIT an already-clean frame (same trap as a
        blind mute press). Trusted gesture only — 'f' (most HTML5 players, Pluto
        included), then the adapter's own fullscreen button as a fallback. F11 is
        left entirely to the operator; this just means they never NEED it."""
        if self.browser.is_fitted():
            return
        self._blur_active()                  # so 'f' reaches the player, not our bar
        self.browser.fullscreen_video()      # 'f' trusted gesture (+ requestFullscreen belt)
        time.sleep(0.5)
        if not self.browser.is_fitted():
            self.adapter.click(self.browser.page, "fullscreen")   # click Pluto's button

    def _verify_audio(self):
        """Shout in the CONSOLE if the recording is muted. VNC has no audio and
        usually isn't fullscreen, so the operator never notices a silent capture
        otherwise — the console is the only channel that reaches them."""
        dom = self.browser.audio_status()
        routed = self.cap.audio_routed()
        silent = (dom and (dom["muted"] or (dom["volume"] or 0) == 0)) or routed == 0
        if silent:
            _log("⚠⚠⚠ AUDIO MUDO — la grabación saldrá SILENCIOSA ⚠⚠⚠")
            _log(f"    dom={dom}  sink_inputs={routed}  "
                 "→ en VNC, quita el mute del reproductor y reinicia el episodio.")
            update_status("RECORDRR", self.show, "WARN", details="audio mudo")
        else:
            _log(f"    audio OK (vol={dom['volume'] if dom else '?'}, streams={routed})")

    # ---- per-episode -----------------------------------------------------
    def _record_one(self, ep, first=False) -> dict:
        page = self.browser.page
        target = cfg.OUTPUT_DIR / ep.filename(self.show)
        safe = _unique_path(target)
        if safe != target:
            _log(f"⚠ '{target.name}' YA EXISTE — no se sobrescribe; uso '{safe.name}'.")
        outfile = str(safe)
        _log(f"{ep.code} -> {Path(outfile).name}")
        update_status("RECORDRR", f"{self.show} {ep.code}", "WORKING",
                      details=Path(outfile).name)

        if first:
            # First episode: the operator drives (login/nav/play) and presses
            # ⏺ REC on the in-page bar. No console trek, no false-start on promos.
            _log(f"esperando ⏺ REC en la barra (hasta {int(self.login_wait)}s)…")
            if not self._wait_for_rec(self.login_wait):
                return {"ep": ep.code, "status": "ABORTED", "why": "sin REC / abortado"}
            # confirm something is actually playing; give it a moment if needed
            st = self.browser.video_state() or self.browser.wait_for_playback(timeout=30)
        else:
            # Subsequent episodes: the player auto-advanced; attach to playback.
            st = self.browser.wait_for_playback(timeout=self.play_wait)
        if not st:
            return {"ep": ep.code, "status": "ERROR", "why": "no playback detected"}

        # flag 'rec' now so the bar starts its idle-fade during the settle and is
        # already hidden by the time capture rolls (keeps it out of the frame).
        self.browser.bar_status("rec", ep.code, 0, "ok")
        # prep: unmute (safe, no blind toggle), fit the frame (fullscreen, no blind
        # toggle), skip intro, settle
        self._ensure_audible()
        self._ensure_fitted()
        self.adapter.skip_intro(page)
        time.sleep(self.play_settle)

        # guard rail: expected runtime, else a generous default
        expected = ep.runtime or 3600
        deadline = time.time() + expected * self.max_factor

        self.cap.start(outfile)
        self._verify_audio()    # console warning if the capture is silent
        start_t = time.time()
        ad_seen = 0
        ad_active = False
        _log("⏺ GRABANDO — ⏹ STOP en la barra o tecla 'q' para parar (NUNCA Ctrl-C).")
        # try/finally so STOP / 'q' / any error still finalizes + remuxes the file.
        try:
            with _KeyPoll() as keys:
                while True:
                    time.sleep(self.ad_poll)
                    secs = int(time.time() - start_t)

                    # ── ad gate: pause the capture across the break, resume after.
                    # Edge-triggered so pause()/resume() fire once per transition.
                    # The segment is dropped from the file; stop() concats the rest.
                    in_ad = self.adapter.is_ad(page)
                    if in_ad and not ad_active:
                        ad_active = True
                        ad_seen += 1
                        _log(f"{ep.code} — anuncio detectado; pausando captura")
                        self.cap.pause()
                    elif not in_ad and ad_active:
                        ad_active = False
                        _log(f"{ep.code} — anuncio terminado; reanudando captura")
                        self.cap.resume()

                    if ad_active:
                        # paused: skip the audio/frame durability nets (they'd fight
                        # the ad UI and warn falsely) and just flag the bar.
                        self.browser.bar_status("rec", ep.code, secs, "ad-skip")
                    else:
                        audible = self.browser.is_audible()
                        if not audible:
                            # durability net (§6): the player may have re-synced its UI
                            # mute state onto the element mid-record. Re-open the element,
                            # drive the real control if that's what muted, then re-check.
                            _log(f"{ep.code} — audio silenciado en grabación; reasserting unmute")
                            self._ensure_audible()
                            audible = self.browser.is_audible()
                        # frame-fit durability net: fullscreen drops on nav/ad/seek and
                        # the toolbar reappears in the capture. Re-assert (guarded — only
                        # acts when not fitted, so it never exits an already-clean frame).
                        if not self.browser.is_fitted():
                            _log(f"{ep.code} — frame sin fullscreen (barra del navegador visible); reajustando")
                            self._ensure_fitted()
                        self.browser.bar_status("rec", ep.code, secs, "ok" if audible else "mute")
                    if keys.get() in ("q", "Q") or self.browser.bar_cmd() == "stop":
                        self.stop = True
                        _log(f"{ep.code} — parada por el operador; finalizando archivo.")
                        break
                    # End-of-episode detection only while NOT in an ad: during a Pluto
                    # break the timeline freezes at episode position (and a near-end ad
                    # would false-trigger the end pad), so trust it only on content.
                    vs = self.browser.video_state()
                    if vs and not ad_active:
                        if vs["ended"]:
                            break
                        dur = vs["duration"]
                        if dur and vs["currentTime"] >= (dur - self.end_pad):
                            break
                    if time.time() > deadline:
                        _log(f"{ep.code} runaway guard tripped ({int(time.time()-start_t)}s) — stopping")
                        break
        finally:
            self.cap.stop()
            self.browser.bar_status("idle")
        dur_s = int(time.time() - start_t)
        ok = Path(outfile).exists() and Path(outfile).stat().st_size > 0
        return {
            "ep": ep.code, "status": "OK" if ok else "ERROR",
            "file": Path(outfile).name, "seconds": dur_s,
            "ads_seen": ad_seen, "size_mb": _mb(outfile),
        }

    def _advance(self) -> bool:
        """Move to the next episode: click next_episode, else trust autoplay."""
        page = self.browser.page
        clicked = self.adapter.next_episode(page)
        _log("next episode: " + ("clicked" if clicked else "autoplay/awaiting"))
        # give the player a moment to switch
        time.sleep(self.play_settle)
        return True

    # ---- season run ------------------------------------------------------
    def run(self):
        results = []
        total = len(self.episodes)
        for i, ep in enumerate(self.episodes):
            res = self._record_one(ep, first=(i == 0))
            results.append(res)
            _log(f"  -> {res['status']} {res.get('size_mb','?')}MB in {res.get('seconds','?')}s"
                 + (f" (ads:{res['ads_seen']})" if res.get("ads_seen") else ""))
            if self.stop:
                _log("temporada detenida por el operador.")
                break
            if i < total - 1:
                self._advance()
        update_status("RECORDRR", self.show, "FINISHED",
                      progress=100, details=f"{len(results)} eps")
        return results


def _unique_path(p: Path) -> Path:
    """Never clobber an existing recording (preservation is the whole point).
    If the target exists, fall back to '<name> (recN).<ext>' and let the operator
    sort it out — losing a capture to a rename collision is unacceptable."""
    if not p.exists():
        return p
    n = 2
    while True:
        cand = p.with_name(f"{p.stem} (rec{n}){p.suffix}")
        if not cand.exists():
            return cand
        n += 1


def _mb(path):
    try:
        return round(Path(path).stat().st_size / (1024 * 1024), 1)
    except OSError:
        return 0


def _resolve_episodes(show, season, start, count):
    sc = SonarrClient()
    s = sc.find_series(show)
    if not s:
        _log(f"'{show}' not found in Sonarr — check the name / SONARR_API_KEY")
        return None, None
    eps = sc.get_episodes(s["id"], season=season)   # sorted by (season, number)
    if start and start > 0 and eps:
        # start = episode NUMBER. Anchor it to the chosen season, or — if none was
        # given — to the first season present. (season, number) tuple compare so it
        # honours start even with season blank (the old `or season is None` clause
        # silently dropped the filter → recorded/overwrote E01. Cost us a file.)
        base = season if season is not None else eps[0].season
        eps = [e for e in eps if (e.season, e.number) >= (base, start)]
    if count:
        eps = eps[:count]
    return s["title"], eps


def main():
    ap = argparse.ArgumentParser(prog="recordrr-orchestrator")
    ap.add_argument("show")
    ap.add_argument("--adapter", default="pluto")
    ap.add_argument("--season", type=int, default=None)
    ap.add_argument("--start", type=int, default=1, help="first episode number")
    ap.add_argument("--count", type=int, default=0, help="0 = all from --start")
    ap.add_argument("--profile", default="pluto")
    ap.add_argument("--no-wait", action="store_true",
                    help="don't pause for manual login/first-play")
    args = ap.parse_args()

    cfg.ensure_dirs()
    title, eps = _resolve_episodes(args.show, args.season, args.start,
                                   args.count or None)
    if not eps:
        _log("no episodes resolved — aborting")
        sys.exit(1)
    _log(f"show: {title}  episodes: {', '.join(e.code for e in eps)}")

    adapter = Adapter.load(args.adapter)
    browser = RecordrrBrowser(args.profile)
    browser.open(adapter.url)
    browser.install_bar()   # in-page control bar (REC/STOP) — no console needed

    if not args.no_wait:
        _log("VNC in (127.0.0.1:5900): loguéate si hace falta, navega al episodio,")
        _log("dale PLAY y pulsa ⏺ REC en la barra de Recordrr (arrástrala donde quieras).")

    orch = Orchestrator(title, eps, adapter, browser, profile=args.profile)
    try:
        results = orch.run()
    finally:
        browser.close()

    _log("=== season report ===")
    for r in results:
        _log(f"  {r['ep']}: {r['status']}  {r.get('size_mb','?')}MB  "
             f"{r.get('seconds','?')}s  {r.get('file','')}")


if __name__ == "__main__":
    main()
