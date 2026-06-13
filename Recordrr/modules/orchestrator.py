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
    from Recordrr.modules.metadata import SonarrClient, RadarrClient, Program
    from Recordrr.modules.flightrecorder import open_recorder, short_src
    from Recordrr.modules.guide import get_guide_client
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
    from Recordrr.config import recordrr_config as cfg
    from Recordrr.modules.browser import RecordrrBrowser
    from Recordrr.modules.capture import get_capturer, ffprobe
    from Recordrr.modules.adapter import Adapter
    from Recordrr.modules.metadata import SonarrClient, RadarrClient, Program
    from Recordrr.modules.flightrecorder import open_recorder, short_src
    from Recordrr.modules.guide import get_guide_client

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
        # boundary backstop: autoplay swaps the <video> src in place, so `ended`
        # never latches and currentTime resets to ~0 before reaching dur-end_pad.
        # A backward jump bigger than this (or a src change) = next episode rolled.
        self.boundary_reset = float(t.get("boundary_reset", 30))
        self.max_factor = float(t.get("max_runtime_factor", 2.2))
        self.play_wait = float(t.get("play_wait", 300))      # per-episode playback wait
        self.login_wait = float(t.get("login_wait", 900))    # first ep: login+nav window
        self.stop = False                                     # set by the 'q' stop key
        self.guide = None                                     # live-TV guide client (set in run_live)

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
        # Adapter opt-out (Prime): requesting player-fullscreen reloads its surface
        # and the per-poll re-assert thrashes it (cover/loading flash every ad_poll).
        # --kiosk already fills the capture display, so skip player-fullscreen here.
        if not self.adapter.player_fullscreen:
            return
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
        self.browser.park_mouse()      # clear stuck tooltips/hover before capture
        time.sleep(self.play_settle)

        # guard rail: expected runtime, else a generous default
        expected = ep.runtime or 3600
        deadline = time.time() + expected * self.max_factor

        self.cap.start(outfile)
        self._verify_audio()    # console warning if the capture is silent
        start_t = time.time()
        ad_seen = 0
        ad_active = False
        untuned_ad_logged = False   # one-shot console/flight note (see ad gate)
        last_ct = 0.0       # last content currentTime, for reset detection
        last_src = None     # last <video> src, for swap detection
        peak_ct = 0.0       # deepest we've reached this episode
        audible = None      # last measured (content polls only)
        fitted = None
        end_reason = "unknown"
        # Flight recorder: passive per-poll timeline → LOGS_DIR/flight/. Always on
        # (RECORDRR_FLIGHT=0 to disable); never throws into this loop. The record
        # of WHY a run went wrong, readable after the fact (E10 had no such trace).
        fr = open_recorder(ep.code, outfile, start_t)
        fr.session(show=self.show, ep=ep.code, title=getattr(ep, "title", ""),
                   expected_runtime=expected, max_factor=self.max_factor,
                   boundary_reset=self.boundary_reset, end_pad=self.end_pad,
                   ad_poll=self.ad_poll, adapter=self.adapter.name,
                   screen=f"{cfg.SCREEN_W}x{cfg.SCREEN_H}",
                   backend=cfg.CAPTURE_BACKEND, outfile=outfile)
        fr.event("rec_start", expected=expected)
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
                    # UNTUNED adapters never pause: a cloned ad_marker false-positive
                    # holds the capture paused for the whole run (Disney 2026-06-10:
                    # [data-testid*='ad'] matched the UI, 76s run → 2.8s of file).
                    # Log the first hit so the flight trail still shows what fired.
                    in_ad = self.adapter.is_ad(page)
                    if in_ad and self.adapter.untuned:
                        if not untuned_ad_logged:
                            untuned_ad_logged = True
                            _log(f"{ep.code} — ad_marker (STUB sin tunear) disparó; "
                                 "IGNORADO — la captura sigue. Tunea el adapter.")
                            fr.event("ad_marker_untuned", secs=secs)
                        in_ad = False
                    if in_ad and not ad_active:
                        ad_active = True
                        ad_seen += 1
                        _log(f"{ep.code} — anuncio detectado; pausando captura")
                        self.cap.pause()
                        fr.event("ad_pause", n=ad_seen, secs=secs)
                    elif not in_ad and ad_active:
                        ad_active = False
                        _log(f"{ep.code} — anuncio terminado; reanudando captura")
                        self.cap.resume()
                        fr.event("ad_resume", n=ad_seen, secs=secs)

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
                            fr.event("audio_reassert", secs=secs)
                            self._ensure_audible()
                            audible = self.browser.is_audible()
                        # frame-fit durability net: fullscreen drops on nav/ad/seek and
                        # the toolbar reappears in the capture. Re-assert (guarded — only
                        # acts when not fitted, so it never exits an already-clean frame).
                        # Skipped entirely for adapters that opt out of player-fullscreen
                        # (Prime: the re-assert thrashes its surface — §20.5n); kiosk fills.
                        if not self.adapter.player_fullscreen:
                            fitted = True
                        else:
                            fitted = self.browser.is_fitted()
                            if not fitted:
                                _log(f"{ep.code} — frame sin fullscreen (barra del navegador visible); reajustando")
                                fr.event("fullscreen_reassert", secs=secs)
                                self._ensure_fitted()
                                fitted = self.browser.is_fitted()
                        self.browser.bar_status("rec", ep.code, secs, "ok" if audible else "mute")
                    # tooltip net: no title attr = no native tooltip (whatever layer
                    # owns it), and re-park clears one already showing + hover chrome.
                    self.browser.strip_titles()
                    if self.browser.maybe_repark():
                        fr.event("mouse_repark", secs=secs)
                    # snapshot the full signal vector once per poll, before the
                    # break checks, so the flight log captures the deciding sample too.
                    vs = self.browser.video_state()
                    ct = vs["currentTime"] if vs else None
                    src = vs.get("src") if vs else None
                    fr.sample(ct=ct, dur=(vs["duration"] if vs else None),
                              end=(vs["ended"] if vs else None),
                              pause=(vs["paused"] if vs else None),
                              src=short_src(src), ad=ad_active, aud=audible, fit=fitted,
                              seg=getattr(self.cap, "_seg_idx", None), peak=round(peak_ct, 1),
                              res=(f"{vs['width']}x{vs['height']}" if vs else None))

                    if keys.get() in ("q", "Q") or self.browser.bar_cmd() == "stop":
                        self.stop = True
                        end_reason = "operator_stop"
                        fr.event("operator_stop", secs=secs)
                        _log(f"{ep.code} — parada por el operador; finalizando archivo.")
                        break
                    # End-of-episode detection only while NOT in an ad: during a Pluto
                    # break the timeline freezes at episode position (and a near-end ad
                    # would false-trigger the end pad), so trust it only on content.
                    if vs and not ad_active:
                        if vs["ended"]:
                            end_reason = "ended"
                            fr.event("ended", ct=ct, secs=secs)
                            break
                        # Autoplay backstop: the player rolls the next episode into
                        # the SAME element, so `ended` may never fire. A src swap, or
                        # a hard backward jump after we'd gotten well into the episode,
                        # means the boundary was crossed — cut here so we don't merge
                        # two episodes (E10 ran to the runaway guard = 99 min once).
                        if peak_ct > 120:
                            if last_src and src and src != last_src:
                                end_reason = "boundary_src"
                                fr.event("boundary_src", secs=secs, peak=round(peak_ct, 1))
                                _log(f"{ep.code} — src del <video> cambió (autoplay); cortando")
                                break
                            if ct < last_ct - self.boundary_reset:
                                end_reason = "boundary_reset"
                                fr.event("boundary_reset", secs=secs, ct=ct,
                                         last_ct=round(last_ct, 1), peak=round(peak_ct, 1))
                                _log(f"{ep.code} — currentTime saltó atrás {int(last_ct-ct)}s (autoplay); cortando")
                                break
                        dur = vs["duration"]
                        if dur and ct >= (dur - self.end_pad):
                            end_reason = "near_end"
                            fr.event("near_end", ct=ct, dur=dur, secs=secs)
                            break
                        last_ct = ct
                        last_src = src
                        peak_ct = max(peak_ct, ct)
                    if time.time() > deadline:
                        end_reason = "runaway"
                        fr.event("runaway", secs=secs, expected=expected, peak=round(peak_ct, 1))
                        _log(f"{ep.code} runaway guard tripped ({int(time.time()-start_t)}s) — stopping")
                        break
        finally:
            self.cap.stop()
            self.browser.bar_status("idle")
        dur_s = int(time.time() - start_t)
        ok = Path(outfile).exists() and Path(outfile).stat().st_size > 0
        out_dur = None
        if ok:
            try:
                for line in ffprobe(outfile).splitlines():
                    if line.startswith("duration="):
                        out_dur = round(float(line.split("=", 1)[1]), 1)
                        break
            except Exception:
                out_dur = None
        fr.event("finalize", ok=ok, out_dur=out_dur)
        fr.close(status="OK" if ok else "ERROR", reason=end_reason,
                 ads_seen=ad_seen, segments=getattr(self.cap, "_seg_idx", 0) + 1,
                 out_dur=out_dur, size_mb=_mb(outfile), wall_secs=dur_s)
        if fr.path:
            _log(f"{ep.code} — flight log: {fr.path}")
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

    # ==== LIVE TV (linear channels) =======================================
    # Reuses the VOD record machinery (capture segment/concat, ad pause/resume,
    # audio + frame durability nets, flight recorder) verbatim. The ONLY swaps for
    # linear: boundary = EPG `stop` WALL-CLOCK (not <video>.ended/duration — on
    # live, duration is the growing DVR buffer, so the VOD near_end check would cut
    # instantly, see asbuilt §20.3); ad gate reads the store `playingState` (DOM
    # adapter.is_ad is the fallback); no _advance() click (the channel auto-runs).
    def _live_ad(self, page) -> bool:
        """Ad gate for live: store signal first (clean), DOM adapter as fallback."""
        if self.guide is not None:
            a = self.guide.is_ad()
            if a is not None:
                return a
        return self.adapter.is_ad(page)

    def _record_live_program(self, channel_name, program, boundary_epoch,
                             override, source, first=False) -> dict:
        page = self.browser.page
        target = cfg.OUTPUT_DIR / program.filename(channel_name, override=override)
        safe = _unique_path(target)
        if safe != target:
            _log(f"⚠ '{target.name}' YA EXISTE — no se sobrescribe; uso '{safe.name}'.")
        outfile = str(safe)
        code = program.code
        _log(f"{code} -> {Path(outfile).name}")
        update_status("RECORDRR", f"{channel_name} {code}", "WORKING",
                      details=Path(outfile).name)

        # The session REC gate already fired in run_live; here just confirm playback.
        st = self.browser.video_state() or self.browser.wait_for_playback(
            timeout=(60 if first else self.play_wait))
        if not st:
            return {"ep": code, "status": "ERROR", "why": "no playback", "reason": "unknown"}

        self.browser.bar_status("rec", code, 0, "ok")
        self._ensure_audible()
        self._ensure_fitted()
        self.browser.park_mouse()      # clear stuck tooltips/hover before capture
        time.sleep(self.play_settle)

        # Runaway guard: EPG program length × factor, else a generous default. This
        # is the SANE bound the livestream itself can't give (duration is the buffer).
        expected = program.runtime or 3600
        hard_deadline = time.time() + expected * self.max_factor

        self.cap.start(outfile)
        self._verify_audio()
        start_t = time.time()
        ad_seen = 0
        ad_active = False
        audible = None
        fitted = None
        end_reason = "unknown"
        fr = open_recorder(code, outfile, start_t)
        fr.session(show=channel_name, ep=code, title=(program.title or program.name),
                   expected_runtime=expected, max_factor=self.max_factor,
                   boundary_reset=0, end_pad=0, ad_poll=self.ad_poll,
                   adapter=self.adapter.name, screen=f"{cfg.SCREEN_W}x{cfg.SCREEN_H}",
                   backend=cfg.CAPTURE_BACKEND, outfile=outfile,
                   mode="live", source=source,
                   boundary_at=(round(boundary_epoch) if boundary_epoch else None))
        fr.event("program_start", code=code, source=source,
                 boundary_in=(round(boundary_epoch - start_t) if boundary_epoch else None))
        _log("⏺ GRABANDO (TV en vivo) — ⏹ STOP en la barra o 'q' para parar (NUNCA Ctrl-C).")
        try:
            with _KeyPoll() as keys:
                while True:
                    time.sleep(self.ad_poll)
                    secs = int(time.time() - start_t)

                    in_ad = self._live_ad(page)
                    if in_ad and not ad_active:
                        ad_active = True; ad_seen += 1
                        _log(f"{code} — anuncio (live); pausando captura")
                        self.cap.pause(); fr.event("ad_pause", n=ad_seen, secs=secs)
                    elif not in_ad and ad_active:
                        ad_active = False
                        _log(f"{code} — anuncio terminado; reanudando captura")
                        self.cap.resume(); fr.event("ad_resume", n=ad_seen, secs=secs)

                    if ad_active:
                        self.browser.bar_status("rec", code, secs, "ad-skip")
                    else:
                        audible = self.browser.is_audible()
                        if not audible:
                            fr.event("audio_reassert", secs=secs)
                            self._ensure_audible(); audible = self.browser.is_audible()
                        if not self.adapter.player_fullscreen:
                            fitted = True            # §20.5n: kiosk fills; skip the thrash
                        else:
                            fitted = self.browser.is_fitted()
                            if not fitted:
                                fr.event("fullscreen_reassert", secs=secs)
                                self._ensure_fitted(); fitted = self.browser.is_fitted()
                        self.browser.bar_status("rec", code, secs, "ok" if audible else "mute")

                    self.browser.strip_titles()
                    if self.browser.maybe_repark():
                        fr.event("mouse_repark", secs=secs)
                    vs = self.browser.video_state()
                    fr.sample(ct=(vs["currentTime"] if vs else None),
                              dur=(vs["duration"] if vs else None),
                              end=(vs["ended"] if vs else None),
                              pause=(vs["paused"] if vs else None),
                              src=short_src(vs.get("src") if vs else None),
                              ad=ad_active, aud=audible, fit=fitted,
                              seg=getattr(self.cap, "_seg_idx", None),
                              res=(f"{vs['width']}x{vs['height']}" if vs else None))

                    if keys.get() in ("q", "Q") or self.browser.bar_cmd() == "stop":
                        self.stop = True; end_reason = "operator_stop"
                        fr.event("operator_stop", secs=secs)
                        _log(f"{code} — parada por el operador; finalizando archivo.")
                        break
                    # BOUNDARY = wall-clock EPG stop, DEFERRED while in an ad (Pluto
                    # freezes the program timeline during a break; an ad straddling
                    # the boundary would otherwise cut mid-ad). No ended/duration on
                    # live. boundary_epoch None = run until the operator stops.
                    if boundary_epoch and not ad_active and time.time() >= boundary_epoch:
                        end_reason = "program_boundary"
                        fr.event("program_boundary", secs=secs)
                        _log(f"{code} — fin de programa (EPG); cortando archivo.")
                        break
                    if time.time() > hard_deadline:
                        end_reason = "runaway"
                        fr.event("runaway", secs=secs, expected=expected)
                        _log(f"{code} runaway guard ({int(time.time()-start_t)}s) — stopping")
                        break
        finally:
            self.cap.stop()
            self.browser.bar_status("idle")

        dur_s = int(time.time() - start_t)
        ok = Path(outfile).exists() and Path(outfile).stat().st_size > 0
        out_dur = None
        if ok:
            try:
                for line in ffprobe(outfile).splitlines():
                    if line.startswith("duration="):
                        out_dur = round(float(line.split("=", 1)[1]), 1); break
            except Exception:
                out_dur = None
        fr.event("finalize", ok=ok, out_dur=out_dur)
        fr.close(status="OK" if ok else "ERROR", reason=end_reason, ads_seen=ad_seen,
                 segments=getattr(self.cap, "_seg_idx", 0) + 1, out_dur=out_dur,
                 size_mb=_mb(outfile), wall_secs=dur_s)
        if fr.path:
            _log(f"{code} — flight log: {fr.path}")
        return {"ep": code, "status": "OK" if ok else "ERROR",
                "file": Path(outfile).name, "seconds": dur_s,
                "ads_seen": ad_seen, "size_mb": _mb(outfile), "reason": end_reason}

    def run_live(self, channel, mode="till", naming="guess", chunk_min=30,
                 override=None):
        """Live capture loop. channel={id,name,...}; mode in {single|clock|till}:
          single — record the current program (to its EPG stop), then stop;
          clock  — record fixed `chunk_min`-minute files, loop until 'q';
          till   — per-program split on the EPG boundary, loop until 'q' (no EPG ⇒
                   one continuous file until 'q').
        naming 'name' uses `override` as the base; 'guess' derives from EPG+TMDB."""
        self.guide = get_guide_client(self.adapter.name, self.browser)
        cn = (channel.get("name") if isinstance(channel, dict) else None) or self.show
        cid = channel.get("id") if isinstance(channel, dict) else None
        results = []
        # ONE session-start REC for the whole run: avoids the pre-roll/nav garbage,
        # then the operator can walk away (continuous archive is unattended).
        _log(f"esperando ⏺ REC en la barra para empezar (hasta {int(self.login_wait)}s)…")
        if not self._wait_for_rec(self.login_wait):
            _log("sin REC / abortado.")
            return results

        first = True
        while True:
            cur, _nxt, gname = self.guide.now_next(cid)
            cn = gname or cn
            source = self.guide.enrich(cur) if cur else "clock"
            if cur is None:
                cur = Program(channel=cn)          # synthetic → clock-named file
            now = time.time()
            if mode == "clock":
                boundary = now + max(1, int(chunk_min)) * 60
            else:                                   # single | till → EPG program end
                boundary = cur.stop_epoch()         # None (no EPG) ⇒ until 'q'
            res = self._record_live_program(
                cn, cur, boundary,
                override if naming == "name" else None, source, first=first)
            results.append(res)
            _log(f"  -> {res['status']} {res.get('size_mb','?')}MB in "
                 f"{res.get('seconds','?')}s ({res.get('reason','?')})"
                 + (f" ads:{res['ads_seen']}" if res.get("ads_seen") else ""))
            first = False
            if self.stop or mode == "single":
                break
            if res["status"] == "ERROR" and res.get("reason") == "unknown":
                _log("sin reproducción detectada; saliendo del bucle live.")
                break
        update_status("RECORDRR", cn, "FINISHED", progress=100,
                      details=f"{len(results)} programas")
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


def _pick_candidate(query, cands, label):
    """Resolve match ambiguity. cands = [(tier, display, obj), ...] best-first.
    Single sharp hit (tier <= 1, no same-tier rival) → silent. Fuzzy + tty →
    numbered pick. Fuzzy + batch → top hit with a warning. None = cancelled."""
    if not cands:
        return None
    if cands[0][0] <= 1 and (len(cands) == 1 or cands[1][0] > 1):
        return cands[0][2]
    if not sys.stdin.isatty():
        _log(f"AVISO: match difuso '{query}' → '{cands[0][1]}' (tier {cands[0][0]})")
        return cands[0][2]
    _log(f"'{query}' no es exacto en {label} — candidatos:")
    show_n = min(len(cands), 5)
    for i, (tier, disp, _) in enumerate(cands[:show_n], 1):
        print(f"  [{i}] {disp}", flush=True)
    try:
        raw = input(f"¿Cuál? [1-{show_n}, 0=cancelar] (1): ").strip()
    except EOFError:
        raw = ""
    if raw == "0":
        _log("cancelado por el operador")
        return None
    idx = int(raw) - 1 if raw.isdigit() and 1 <= int(raw) <= show_n else 0
    return cands[idx][2]


def _resolve_episodes(show, season, start, count):
    sc = SonarrClient()
    cands = []
    for c in sc.search_series(show):
        year = " ({})".format(c["year"]) if c.get("year") else ""
        cands.append((c["tier"], "{}{} [tvdb-{}]".format(c["title"], year, c["tvdb_id"]), c))
    s = _pick_candidate(show, cands, "Sonarr")
    if not s:
        _log(f"'{show}' not found in Sonarr — check the name / SONARR_API_KEY")
        return None, None
    year = " ({})".format(s["year"]) if s.get("year") else ""
    _log(f"serie: {s['title']}{year} [tvdb-{s['tvdb_id']}]")
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


def _resolve_movie(query):
    """Resolve a movie title via Radarr → (display_title, [Movie]). Single asset,
    so the 'season' is a one-item list the run loop walks once (no autoplay-next,
    no _advance)."""
    rc = RadarrClient()
    cands = []
    for tier, m in rc.search_movies(query):
        year = " ({})".format(m.year) if m.year else ""
        cands.append((tier, f"{m.title}{year}", m))
    m = _pick_candidate(query, cands, "Radarr")
    if not m:
        _log(f"'{query}' not found in Radarr — check the name / RADARR_API_KEY")
        return None, None
    disp = f"{m.title}{f' ({m.year})' if m.year else ''}"
    _log(f"película: {disp}" + (f" [tmdb-{m.tmdb_id}]" if m.tmdb_id else ""))
    return disp, [m]


def _run_live(args):
    """Live-TV flow: open the provider's live guide, resolve the channel from the
    in-page store, navigate to it, then run the linear capture loop."""
    adapter = Adapter.load(args.adapter)
    live = (adapter.spec.get("live", {}) or {})
    live_url = live.get("url") or "https://pluto.tv/en/live-tv"
    browser = RecordrrBrowser(args.profile)
    browser.open(live_url)
    browser.install_bar()
    guide = get_guide_client(adapter.name, browser)

    # Channel select is BEST-EFFORT: Pluto's channel `list` only hydrates on the
    # guide grid, not when it redirects into a player, so find_channel can miss.
    # When it does (or no channel was given) we just record whatever the operator
    # tunes to in VNC — now_next(None) reads the PLAYING channel from the store.
    # This mirrors VOD: manual navigation, auto-nav deferred.
    query = (args.show or "").strip()
    ch = None
    if query and query.lower() not in ("auto", "-", "."):
        _log(f"buscando canal '{query}' en la guía…")
        for _ in range(12):                  # store loads async after navigation
            ch = guide.find_channel(query)
            if ch:
                break
            time.sleep(1)
        if ch:
            _log(f"canal: {ch['name']} (#{ch.get('number')})")
            browser.page.goto(guide.channel_url(ch), wait_until="domcontentloaded")
        else:
            _log(f"canal '{query}' no encontrado en la guía (lista no cargada).")
            _log("→ sintoniza el canal A MANO en VNC; grabaré el que esté en marcha.")
    else:
        _log("sin canal explícito → grabaré el canal que sintonices en VNC.")
    if ch is None:
        ch = {"id": None, "name": query or ""}   # record the playing channel
    _log(f"modo={args.mode} naming={args.naming}")

    orch = Orchestrator(ch.get("name") or "LiveTV", [], adapter, browser,
                        profile=args.profile)
    lt = live.get("timing", {}) or {}
    orch.ad_poll = float(lt.get("ad_poll", orch.ad_poll))
    orch.play_settle = float(lt.get("play_settle", orch.play_settle))
    orch.max_factor = float(lt.get("max_runtime_factor", orch.max_factor))
    orch.login_wait = float(lt.get("login_wait", orch.login_wait))

    if not args.no_wait:
        _log("VNC (127.0.0.1:5900): login si hace falta, espera a que cargue el canal,")
        _log("y pulsa ⏺ REC en la barra para empezar (una sola vez por sesión).")
    try:
        results = orch.run_live(ch, mode=args.mode, naming=args.naming,
                                chunk_min=args.chunk, override=args.override)
    finally:
        browser.close()
    _log("=== live report ===")
    for r in results:
        _log(f"  {r['ep']}: {r['status']}  {r.get('size_mb','?')}MB  "
             f"{r.get('seconds','?')}s  {r.get('file','')}")


def main():
    ap = argparse.ArgumentParser(prog="recordrr-orchestrator")
    ap.add_argument("show")
    ap.add_argument("--adapter", default="pluto")
    ap.add_argument("--movie", action="store_true",
                    help="movie mode: resolve via Radarr, record one asset")
    ap.add_argument("--season", type=int, default=None)
    ap.add_argument("--start", type=int, default=1, help="first episode number")
    ap.add_argument("--count", type=int, default=0, help="0 = all from --start")
    ap.add_argument("--profile", default="pluto")
    ap.add_argument("--no-wait", action="store_true",
                    help="don't pause for manual login/first-play")
    ap.add_argument("--live", action="store_true",
                    help="live-TV mode: linear channel, EPG wall-clock boundaries")
    ap.add_argument("--mode", default="till", choices=["single", "clock", "till"],
                    help="live: single program | clock chunks | till-I-return")
    ap.add_argument("--naming", default="guess", choices=["guess", "name"],
                    help="live: derive name from EPG+TMDB, or use --override base")
    ap.add_argument("--override", default=None, help="live --naming name: base name")
    ap.add_argument("--chunk", type=int, default=30,
                    help="live --mode clock: minutes per file")
    args = ap.parse_args()

    cfg.ensure_dirs()
    if args.live:
        _run_live(args)
        return
    if args.movie:
        title, eps = _resolve_movie(args.show)
        if not eps:
            _log("no movie resolved — aborting")
            sys.exit(1)
        _log(f"movie: {title}  runtime: {eps[0].runtime // 60}min  -> {eps[0].filename()}")
    else:
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
