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
import sys
import time
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
        self._pw = sync_playwright().start()
        self.ctx = self._pw.chromium.launch_persistent_context(
            user_data_dir=str(self.profile_dir),
            channel=cfg.CHROME_CHANNEL,
            headless=False,
            args=cfg.CHROME_ARGS,
            viewport={"width": cfg.SCREEN_W, "height": cfg.SCREEN_H},
            ignore_default_args=["--enable-automation"],  # less detectable
        )
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
            return bool(self.page.evaluate(
                "() => { const v=document.querySelector('video');"
                " if(v&&!document.fullscreenElement){ (v.requestFullscreen||"
                "v.webkitRequestFullscreen||(()=>{})).call(v); } return true; }"
            ))
        except Exception:
            return False

    def is_fitted(self) -> bool:
        """True when the player is in the browser Fullscreen state — the ONLY clean
        capture frame on this WM-less display. With no window manager, Chrome
        --kiosk degrades to a normal window WITH a toolbar (the url bar bakes into
        the file); the Fullscreen API hides Chrome's chrome WM-independently, which
        is exactly what a manual F11 does.

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

    def bar_cmd(self):
        """Read AND clear the pending command set by a bar button ('rec'|'stop'|…)."""
        try:
            return self.page.evaluate(
                "() => { const n=window.__recordrr; if(!n||!n.cmd) return null;"
                " const c=n.cmd; n.cmd=null; return c; }")
        except Exception:
            return None

    def bar_status(self, state, ep="", secs=None, audio="ok"):
        """Push status to the bar so it can show REC ● / elapsed / mute icon."""
        try:
            self.page.evaluate(
                "(s) => { window.__recordrr = window.__recordrr || {cmd:null};"
                " window.__recordrr.status = s; }",
                {"state": state, "ep": ep, "secs": secs, "audio": audio})
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
            if self.ctx:
                self.ctx.close()
        finally:
            if self._pw:
                self._pw.stop()
            self.ctx = self.page = self._pw = None


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
