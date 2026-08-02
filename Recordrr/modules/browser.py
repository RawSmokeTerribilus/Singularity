# -*- coding: utf-8 -*-
"""Browser controller for Recordrr.

Playwright driving REAL Google Chrome (channel="chrome") so the Widevine CDM is
present — Playwright's bundled Chromium has no CDM and DRM playback fails there.
Headed, on the Xvfb DISPLAY, with a per-user persistent profile so a one-time
manual login sticks across runs.

The boundary engine reads the page's <video> element rather than watching pixels:
currentTime / duration / ended / paused. That's the primary cut signal; OpenCV is
a documented fallback only.

Run standalone (POC): open a URL and leave Chrome up for manual login/playback:
    DISPLAY=:77 python3 -m Recordrr.modules.browser https://www.pluto.tv/ poc
"""
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

try:
    from Recordrr.config import recordrr_config as cfg
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
    from Recordrr.config import recordrr_config as cfg

# JS that finds the most-likely playback <video> (longest duration / playing) and
# reports its state. Returns null if no usable video element is found.
_VIDEO_STATE_JS = r"""
() => {
  const vids = Array.from(document.querySelectorAll('video'))
    .filter(v => (v.duration || v.currentTime || v.readyState >= 1));
  if (!vids.length) return null;
  // Prefer the one actually playing; else the longest.
  vids.sort((a, b) => (b.duration || 0) - (a.duration || 0));
  const v = vids.find(x => !x.paused && x.currentTime > 0) || vids[0];
  return {
    currentTime: v.currentTime,
    duration: isFinite(v.duration) ? v.duration : null,
    src: v.currentSrc || v.src || '',
    ended: v.ended,
    paused: v.paused,
    readyState: v.readyState,
    width: v.videoWidth,
    height: v.videoHeight,
  };
}
"""


class RecordrrBrowser:
    def __init__(self, profile: str = "default"):
        os.environ.setdefault("DISPLAY", cfg.DISPLAY)
        # :99 is now auth'd (Xvfb -auth, not -ac). Chrome — launched by Playwright
        # as a child inheriting this env — needs the cookie to connect, else it'd
        # hit "Missing X server". setdefault: don't clobber an explicit override.
        os.environ.setdefault("XAUTHORITY", cfg.XAUTHORITY)
        self.profile_dir = cfg.PROFILES_DIR / profile
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        self._pw = None
        self._browser = None
        self._chrome = None
        self.ctx = None
        self.page = None

    def _clear_stale_singleton(self):
        """Chrome drops SingletonLock/Socket/Cookie symlinks in the profile. A
        crash or a hard exit (ctrl-C / ctrl-Z killing the python while Chrome
        lingers) leaves them behind, and the next launch dies with 'Opening in
        existing browser session'. Remove them, but ONLY when no live process
        owns the profile — the SingletonLock target is '<host>-<pid>'."""
        lock = self.profile_dir / "SingletonLock"
        try:
            pid = int(os.readlink(lock).rsplit("-", 1)[1])
            os.kill(pid, 0)        # raises OSError if that pid is gone
            return                 # a real instance owns the profile — leave it
        except (OSError, ValueError, IndexError):
            pass                   # dangling / dead / unparsable -> stale
        for name in ("SingletonLock", "SingletonSocket", "SingletonCookie"):
            try:
                (self.profile_dir / name).unlink()
            except OSError:
                pass

    def open(self, url: str = None):
        from playwright.sync_api import sync_playwright
        self._clear_stale_singleton()
        # Launch Chrome OURSELVES and attach Playwright over a CDP *port*.
        # Playwright's launch_persistent_context talks --remote-debugging-pipe,
        # and pipe-mode silently degrades --kiosk to a normal toolbar'd window
        # (1919x1079 WITH the url bar baked into every capture — that's why the
        # operator had to F11 before each record). Bisected: no ignorable
        # default arg is responsible; --kiosk survives into the cmdline and is
        # still ignored. A plain launch with --remote-debugging-port keeps the
        # true 1920x1080 chromeless kiosk window, and connect_over_cdp drives
        # it with the same Playwright API (add_init_script proven working).
        port = cfg.DEBUG_PORT or 9222
        args = list(cfg.CHROME_ARGS)
        if not any(a.startswith("--remote-debugging-port") for a in args):
            args.append(f"--remote-debugging-port={port}")
        else:                          # RECORDRR_DEBUG_PORT env owns the port
            port = cfg.DEBUG_PORT
        binary = shutil.which("google-chrome") or "google-chrome"
        cmd = [binary, "--no-first-run", "--no-default-browser-check",
               f"--user-data-dir={self.profile_dir}", *args,
               url or "about:blank"]
        self._chrome = subprocess.Popen(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        endpoint = f"http://127.0.0.1:{port}"
        for _ in range(100):           # wait for the CDP endpoint (~20s cap)
            try:
                urllib.request.urlopen(f"{endpoint}/json/version", timeout=1)
                break
            except Exception:
                if self._chrome.poll() is not None:
                    raise RuntimeError(
                        f"Chrome exited rc={self._chrome.returncode} before "
                        f"CDP came up — check DISPLAY/profile lock")
                time.sleep(0.2)
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.connect_over_cdp(endpoint)
        self.ctx = self._browser.contexts[0]
        self.page = self.ctx.pages[0] if self.ctx.pages else self.ctx.new_page()
        if url:
            self.page.goto(url, wait_until="domcontentloaded")
        return self.page

    def video_state(self):
        """Return the playback <video> state dict, or None if not found yet."""
        try:
            return self.page.evaluate(_VIDEO_STATE_JS)
        except Exception:
            return None

    def wait_for_playback(self, timeout: float = 300.0):
        """Block until a video is actually playing (currentTime advancing)."""
        deadline = time.time() + timeout
        last = -1.0
        while time.time() < deadline:
            st = self.video_state()
            if st and not st["paused"] and st["currentTime"] > last and st["currentTime"] > 0:
                return st
            if st:
                last = st["currentTime"]
            time.sleep(1.0)
        return None

    def fullscreen_video(self) -> bool:
        """Best-effort: push the player into fullscreen so it decodes at max res.

        'f' is a trusted key gesture (satisfies requestFullscreen's user-gesture
        requirement); most web players bind it. In --kiosk the window already fills
        the display, so even if this no-ops the frame is clean and full-width.
        """
        try:
            self.page.keyboard.press("f")
        except Exception:
            pass
        try:
            # Fullscreen the player CONTAINER, never the bare <video>: when the
            # <video> itself is the fullscreenElement, the in-page bar gets
            # appended INSIDE it (placeBar fullscreen mode) and video elements
            # never render children — bar invisible/unclickable (Disney bug).
            # The parent container hides the toolbar just the same and can host
            # the bar.
            return bool(self.page.evaluate(
                "() => { const v=document.querySelector('video');"
                " if(v&&!document.fullscreenElement){ const t=v.parentElement||v;"
                " (t.requestFullscreen||t.webkitRequestFullscreen||(()=>{})).call(t); }"
                " return true; }"
            ))
        except Exception:
            return False

    def park_mouse(self):
        """Synthetic pointer to the mid-left edge. Chrome's hover/tooltip state
        follows the LAST input event, so this dismisses a native title-attr
        tooltip left under the operator's parked VNC cursor (RTVE's 'Reproducir
        vídeo' baked into a full record) and un-hovers provider chrome. Mid-left,
        not a bottom corner: bottom edges host control bars that pin visible
        under hover. Call before the settle so triggered chrome fades pre-capture."""
        try:
            self.page.mouse.move(2, cfg.SCREEN_H // 2)
            self._parked_ms = time.time() * 1000
        except Exception:
            pass

    def last_mouse_move(self):
        """Epoch ms of the last REAL pointer movement the bar saw (localStorage
        mirror, survives navigation), or None."""
        try:
            v = self.page.evaluate(
                "() => { try { return localStorage.getItem('recordrrLastMove'); }"
                " catch(e) { return null; } }")
            return int(v) if v else None
        except Exception:
            return None

    def strip_titles(self):
        """Remove title attributes page-wide (Recordrr bar excluded — it manages
        its own). Native tooltips are OS-drawn and x11grab captures them; the
        owner can be ANY hit-testable layer (player chrome, a hidden ad slot
        behind the video, RTVE's mini-player) — no attribute, no tooltip,
        regardless of which layer theory is right. Per-poll call: SPAs re-add
        attributes on every re-render."""
        try:
            self.page.evaluate(
                "() => { for (const el of document.querySelectorAll('[title]'))"
                " if (!el.closest('#rr-bar')) el.removeAttribute('title'); }")
        except Exception:
            pass

    def maybe_repark(self) -> bool:
        """Re-park after the operator moved the pointer and went idle. The VNC
        viewer's close button sits past the player's top-right chrome, so the
        exit path ALWAYS re-hovers a titled control as the session's final input
        — the record-start park can't cover it. park_mouse() itself fires a
        synthetic mousemove the bar records, so only movement NEWER than the
        last park (+slack) counts; 3s idle keeps hover chrome from flapping
        while the operator is actively driving. Returns True when it parked."""
        lm = self.last_mouse_move()
        if not lm:
            return False
        now = time.time() * 1000
        if lm > getattr(self, "_parked_ms", 0) + 1500 and (now - lm) > 3000:
            self.park_mouse()
            return True
        return False

    def is_fitted(self) -> bool:
        """True when the player is in the browser Fullscreen state. The display now
        runs the openbox WM (display.py start_wm, baked d143e70), so --kiosk genuinely
        fills the screen WITHOUT a toolbar — but the Fullscreen API is still the
        signal we trust: it hides Chrome's chrome regardless, exactly like a manual
        F11, and the same check guards the safe 'f' toggle below. (History: pre-WM,
        kiosk degraded to a toolbar'd window and the url bar baked into the file.)

        Signal = `document.fullscreenElement != null`, nothing more. This is also
        the SAFE toggle guard: 'f' enters fullscreen only when there's none, so we
        must NOT report false while a fullscreen element exists — an ad can letterbox
        the <video> smaller mid-break while still fullscreen, and a 'video-fills'
        test would then read 'not fitted' → press 'f' → EXIT fullscreen (the same
        blind-toggle trap the mute fix taught us). Toolbar-hidden is what matters."""
        try:
            return bool(self.page.evaluate("() => !!document.fullscreenElement"))
        except Exception:
            return False

    def install_bar(self):
        """Inject the in-page control bar (assets/recordrr_bar.js). add_init_script
        re-runs it on every navigation; evaluate() covers the already-open page.
        No proxy — the bar talks to the orchestrator through window.__recordrr."""
        js = (Path(__file__).resolve().parent.parent / "assets" / "recordrr_bar.js").read_text(encoding="utf-8")
        try:
            self.ctx.add_init_script(script=js)
        except Exception:
            pass
        try:
            self.page.evaluate(js)
        except Exception:
            pass
        # Clear any stale durable-channel keys left by a prior/crashed session
        # (localStorage is per-origin and outlives a process) so a leftover 'stop'
        # or 'rec' can't false-trigger this session's REC gate.
        try:
            self.page.evaluate(
                "() => { try { localStorage.removeItem('recordrrCmd');"
                " localStorage.removeItem('recordrrStatus');"
                " localStorage.removeItem('recordrrLastMove'); } catch(e){} }")
        except Exception:
            pass

    def seek_to_start(self, land: float = 3.0) -> bool:
        """PAUSE the playback <video> and rewind it to t≈0 — leaving it paused on
        frame 0 so the caller can cap.start() and only THEN resume_play(): capture
        rolls before a single frame of content advances = zero loss. (The earlier
        version seeked-then-waited-for-resume, which let 0→~2s play during the wait
        and got recorded as 'started 2s in' — §20.5v.) The prep/settle window + the
        autoplay transition gap are why episodes opened mid-action otherwise.
        VOD-only by construction: bails when non-seekable or duration non-finite (a
        live/linear <video> — RTVE/Pluto live — has a rolling buffer, no real 0), so
        it's a no-op even if mistakenly enabled there. Polls until the seek lands
        (currentTime≈0); SAFE to poll because the element is paused — nothing plays
        while we wait. Returns True only when it paused+seeked."""
        try:
            ok = self.page.evaluate(
                "() => { const vs=[...document.querySelectorAll('video')];"
                " const v=vs.find(x=>!x.paused && x.currentTime>0)||vs[0];"
                " if(!v||!isFinite(v.duration)||!v.seekable||v.seekable.length===0) return false;"
                " try{ v.pause(); v.currentTime=0; }catch(e){ return false; }"
                " return true; }")
        except Exception:
            return False
        if not ok:
            return False
        end = time.time() + land
        while time.time() < end:
            st = self.video_state()
            if st and (st.get("currentTime") or 0) < 0.5:
                break
            time.sleep(0.2)
        return True

    def resume_play(self) -> bool:
        """Resume the playback <video> after a seek_to_start() pause. Used so capture
        starts on a paused frame 0 and content only moves once ffmpeg is already
        rolling (zero-loss start). play() is allowed: Chrome runs
        --autoplay-policy=no-user-gesture-required and the operator already started
        playback once (the gesture is spent)."""
        try:
            return bool(self.page.evaluate(
                "() => { const vs=[...document.querySelectorAll('video')];"
                " const v=vs.find(x=>x.currentTime<2)||vs[0];"
                " if(!v) return false; try{ const p=v.play(); if(p) p.catch(()=>{}); }"
                " catch(e){ return false; } return true; }"))
        except Exception:
            return False

    def apply_hide_css(self, selectors):
        """Hide adapter-named overlay elements from the CAPTURE by killing their
        paint — Chrome never composites `display:none`, so x11grab can't bake them.
        A persistent <style id=rr-hide> rule (NOT per-poll JS) auto-covers the
        element however many times the SPA remounts it; that's why Plex's loading
        Spinner — orphaned on the autoplay episode transition (§20.5u) — stays gone
        for the rest of the run after one call. add_init_script re-applies the rule
        after a navigation; evaluate() covers the page already open. Stall/boundary
        logic reads <video> state, never the spinner, so hiding it blinds nothing.
        No-op when the adapter sets no selectors. Call ONCE per session: repeated
        add_init_script calls STACK (like install_bar)."""
        sels = [s for s in (selectors or []) if s]
        if not sels:
            return
        rule = ",".join(sels) + "{display:none!important}"
        js = ("() => { let s=document.getElementById('rr-hide');"
              " if(!s){ s=document.createElement('style'); s.id='rr-hide';"
              " (document.head||document.documentElement).appendChild(s); }"
              " s.textContent=" + repr(rule) + "; }")
        try:
            self.ctx.add_init_script(script="(" + js + ")()")
        except Exception:
            pass
        try:
            self.page.evaluate(js)
        except Exception:
            pass

    def bar_cmd(self):
        """Read AND clear the pending command set by a bar button ('rec'|'stop'|…).
        Reads the durable localStorage channel FIRST (survives a page navigation —
        Prime reloads the document on player<->home, which wipes window.__recordrr),
        then falls back to the same-document window global. Clears both."""
        try:
            return self.page.evaluate(
                "() => { let c=null;"
                " try { c=localStorage.getItem('recordrrCmd'); if(c) localStorage.removeItem('recordrrCmd'); } catch(e){}"
                " const n=window.__recordrr; if(!c && n && n.cmd) c=n.cmd;"
                " if(n) n.cmd=null;"
                " return c || null; }")
        except Exception:
            return None

    def bar_status(self, state, ep="", secs=None, audio="ok"):
        """Push status to the bar so it can show REC ● / elapsed / mute icon. Writes
        the durable localStorage channel (the bar reads it after a reload) AND the
        window global (same-document fast path)."""
        s = {"state": state, "ep": ep, "secs": secs, "audio": audio}
        try:
            self.page.evaluate(
                "(s) => { window.__recordrr = window.__recordrr || {cmd:null};"
                " window.__recordrr.status = s;"
                " try { localStorage.setItem('recordrrStatus', JSON.stringify(s)); } catch(e){} }",
                s)
        except Exception:
            pass

    def press(self, key: str) -> bool:
        """Send a trusted keyboard gesture to the player (e.g. 'm' to toggle mute,
        'f' fullscreen). Trusted gestures satisfy the player's own key handlers
        when a JS property write (video.muted=false) gets re-applied by the UI."""
        try:
            self.page.keyboard.press(key)
            return True
        except Exception:
            return False

    def unmute(self) -> bool:
        """Force every <video> unmuted at full volume. Pluto (and others) default
        to muted; cookie persistence is unreliable, so we unmute every run."""
        try:
            return bool(self.page.evaluate(
                "() => { const vs=[...document.querySelectorAll('video')];"
                " vs.forEach(v=>{ v.muted=false; try{v.volume=1.0;}catch(e){} });"
                " return vs.length>0; }"
            ))
        except Exception:
            return False

    def audio_status(self):
        """Mute/volume of the playback <video>. The ONLY pre-record audio signal:
        VNC carries no sound, so a silently-muted recording is invisible to the
        operator until import. Caller warns loudly in the console if muted.
        Returns {muted, volume, videos} or None if no video yet."""
        try:
            return self.page.evaluate(
                "() => { const vs=[...document.querySelectorAll('video')]"
                ".filter(v=>v.readyState>=1||v.currentTime>0);"
                " if(!vs.length) return null;"
                " const v=vs.find(x=>!x.paused&&x.currentTime>0)||vs[0];"
                " return {muted:v.muted, volume:v.volume, videos:vs.length}; }"
            )
        except Exception:
            return None

    def is_audible(self) -> bool:
        """True only if the playback <video> is unmuted AND volume>0."""
        st = self.audio_status()
        return bool(st and not st["muted"] and (st["volume"] or 0) > 0)

    def wait_until_ended(self, poll: float = 2.0, end_pad: float = 1.0):
        """Block until the current episode ends (ended flag or currentTime≈duration)."""
        while True:
            st = self.video_state()
            if st:
                if st["ended"]:
                    return "ended"
                dur = st["duration"]
                if dur and st["currentTime"] >= (dur - end_pad):
                    return "near_end"
            time.sleep(poll)

    def close(self):
        try:
            if self._browser:
                self._browser.close()      # disconnect CDP, Chrome stays ours
        finally:
            if self._pw:
                self._pw.stop()
            if self._chrome:
                self._chrome.terminate()   # we launched it, we kill it
                try:
                    self._chrome.wait(timeout=10)
                except Exception:
                    self._chrome.kill()
            self.ctx = self.page = self._pw = None
            self._browser = self._chrome = None


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "https://www.pluto.tv/"
    profile = sys.argv[2] if len(sys.argv) > 2 else "poc"
    b = RecordrrBrowser(profile)
    b.open(url)
    print(f"[recordrr] Chrome up on {cfg.DISPLAY} (profile '{profile}') -> {url}")
    print("[recordrr] VNC in, log in, start an episode. Polling <video> state...")
    # Opt-in live selector discovery: RECORDRR_PROBE=<adapter> dumps the player's
    # real interactive DOM once playback is rolling — turns blind selector tuning
    # into a copy-from-reality job. Wiggle the mouse in VNC first (Pluto hides its
    # controls until mouse-move), then watch this console.
    _probe_name = os.environ.get("RECORDRR_PROBE")
    _probed = False
    _fs_done = False
    try:
        while True:
            st = b.video_state()
            print("   video_state:", st)
            # Once playback is actually rolling, push fullscreen once for max res.
            if st and not _fs_done and not st["paused"] and st["currentTime"] > 1:
                b.unmute()
                b.fullscreen_video()
                _fs_done = True
                print("   [recordrr] unmute + fullscreen requested")
            if _probe_name and not _probed and st and st["currentTime"] > 1:
                try:
                    from Recordrr.modules.adapter import Adapter
                    cands = Adapter.load(_probe_name).probe(b.page)
                    print(f"\n   [probe] {_probe_name}: {len(cands)} visible controls")
                    for c in cands:
                        sig = " ".join(f"{k}={c[k]!r}" for k in
                                       ("role", "aria", "title", "testid", "pressed", "text")
                                       if c[k])
                        print(f"     <{c['tag']}> {sig}  cls={c['cls']!r}")
                    _probed = True
                except Exception as e:
                    print(f"   [probe] failed: {e}")
            time.sleep(3)
    except KeyboardInterrupt:
        b.close()
        print("\n[recordrr] closed.")
