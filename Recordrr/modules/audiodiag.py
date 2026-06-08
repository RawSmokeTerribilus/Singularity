# -*- coding: utf-8 -*-
"""Recordrr audio diagnostic — get DATA on the 'icon stays red' unmute problem.

The question this answers: WHY does `<video>.muted=false` record sound while the
player's mute icon stays red, and WHICH action (if any) actually flips the
player's real state? F12 inside the container's Xvfb Chrome is useless; we instead
drive the live page through Playwright (we own it) and dump the real DOM around the
mute control before/after each unmute strategy.

It runs a fixed sequence against a LIVE, PLAYING page and prints, at each step:
  - element audio state  (video.muted / volume)         ← does the element open?
  - the resolved `unmute` control's full DOM signature   ← what IS the red icon?
    (aria-pressed / class / svg path / computed fill+color)
  - mute_state() interpretation (muted/unmuted/unknown)

Steps: baseline → element unmute → press 'm' → click `unmute` control. Watch which
step changes aria_pressed / svg fill / class — that's the action that drives the
player's REAL state (= what (b) must use). If the `unmute` control never matches
(`matched: False`), the selector is wrong and that's the whole bug.

Run (live session, navigate + press play in VNC first):
    docker exec -e DISPLAY=:99 -e RECORDRR_DEBUG_PORT=9222 singularity_core \
        python3 -m Recordrr.modules.audiodiag pluto pluto

With RECORDRR_DEBUG_PORT set you can ALSO open http://localhost:9222 in your real
desktop browser for full DevTools on the same page (container is network_mode:host).
"""
import json
import sys
import time
from pathlib import Path

try:
    from Recordrr.config import recordrr_config as cfg
    from Recordrr.modules.browser import RecordrrBrowser
    from Recordrr.modules.adapter import Adapter
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
    from Recordrr.config import recordrr_config as cfg
    from Recordrr.modules.browser import RecordrrBrowser
    from Recordrr.modules.adapter import Adapter


def _p(label, obj):
    print(f"\n--- {label} ---")
    print(json.dumps(obj, indent=2, ensure_ascii=False, default=str))


def _snapshot(browser, adapter):
    """Everything we care about at one instant."""
    return {
        "element_audio": browser.audio_status(),       # video.muted / volume
        "is_audible": browser.is_audible(),             # element unmuted + vol>0
        "mute_state": adapter.mute_state(browser.page), # player REAL state (our read)
        "mute_signature": adapter.mute_signature(browser.page),  # the control's DOM
    }


def _volume_candidates(page):
    """Discovery: every control whose aria/class/title mentions mute/volume/sound.
    If our `unmute` selector misses, the real button is somewhere in here."""
    js = r"""
    () => {
      const hit = [];
      const els = document.querySelectorAll('button,[role=button],[aria-label],[data-testid],[title]');
      const rx = /(mute|volume|sound|audio)/i;
      els.forEach(e => {
        const blob = [e.getAttribute('aria-label'), e.getAttribute('title'),
                      e.getAttribute('data-testid'), (e.className||'').toString()]
                     .filter(Boolean).join(' ');
        if (!rx.test(blob)) return;
        const r = e.getBoundingClientRect();
        hit.push({
          aria: e.getAttribute('aria-label') || '',
          pressed: e.getAttribute('aria-pressed') || '',
          title: e.getAttribute('title') || '',
          testid: e.getAttribute('data-testid') || '',
          cls: (e.className||'').toString().slice(0,80),
          visible: !(r.width===0 && r.height===0),
        });
      });
      return hit;
    }"""
    try:
        return page.evaluate(js)
    except Exception as e:
        return [{"error": str(e)}]


def main():
    adapter_name = sys.argv[1] if len(sys.argv) > 1 else "pluto"
    profile = sys.argv[2] if len(sys.argv) > 2 else adapter_name

    adapter = Adapter.load(adapter_name)

    # Self-raise the virtual display + VNC if it isn't up. A manually-started
    # Xvfb gets reaped when its `docker exec` session ends, so the diag owns it
    # here instead of depending on a separate `display up` that may have died.
    # OWNER CONTRACT (same as the launcher): if WE raise it, WE tear it down on
    # exit — leaving :99 up opens the netns X11 leak that poisons host Flatpak VLC
    # (see recordrr-asbuilt §12.1). `raised` tracks ownership for the finally.
    from Recordrr.modules import display
    raised = not display._alive("xvfb")
    if raised:
        info = display.up(with_vnc=True)
        print(f"[audiodiag] raised display: {info}")
    else:
        print("[audiodiag] display already up (left as-is — someone else owns it)")

    browser = RecordrrBrowser(profile)
    try:
        _run(browser, adapter, adapter_name, profile)
    finally:
        try:
            browser.close()
        finally:
            if raised:
                display.down()
                print("[audiodiag] display torn down (netns leak window closed).")
            else:
                print("[audiodiag] display left up (we didn't raise it).")


def _run(browser, adapter, adapter_name, profile):
    browser.open(adapter.url)
    if cfg.DEBUG_PORT:
        print(f"[audiodiag] DevTools exposed → http://localhost:{cfg.DEBUG_PORT} "
              "(open in your real browser for full F12)")
    print(f"[audiodiag] adapter={adapter_name} profile={profile} on {cfg.DISPLAY}")
    print("[audiodiag] In VNC (127.0.0.1:5900): log in if needed, open a show, PRESS PLAY.")
    print("[audiodiag] Waiting for playback (up to 300s)…")

    st = browser.wait_for_playback(timeout=300)
    if not st:
        print("[audiodiag] no playback detected — aborting. Did you press play in VNC?")
        return    # main()'s finally closes the browser + tears the display down
    print(f"[audiodiag] playback detected: {st}")

    # Discovery first: what mute/volume controls actually exist in the DOM?
    _p("volume/mute candidates in DOM (wiggle mouse in VNC if empty — Pluto hides controls)",
       _volume_candidates(browser.page))

    _p("STEP 0  baseline (untouched)", _snapshot(browser, adapter))

    # (a) element-level unmute — should open audio; does it touch the icon?
    browser.unmute()
    time.sleep(1.0)
    _p("STEP 1  after browser.unmute()  [element video.muted=false]",
       _snapshot(browser, adapter))

    # (b) the player's real keybind — drop focus first so 'm' reaches the player
    try:
        browser.page.evaluate("() => { const a=document.activeElement;"
                              " if(a&&a!==document.body&&a.blur) a.blur(); }")
    except Exception:
        pass
    browser.press(adapter.mute_key)
    time.sleep(1.0)
    _p(f"STEP 2  after press '{adapter.mute_key}'  [player keybind]",
       _snapshot(browser, adapter))

    # If that muted it (toggle), press again to land unmuted for the click test.
    if adapter.mute_state(browser.page) is True:
        print(f"\n[audiodiag] '{adapter.mute_key}' left it MUTED → pressing again to toggle back")
        browser.press(adapter.mute_key)
        time.sleep(1.0)
        _p(f"STEP 2b after second '{adapter.mute_key}'", _snapshot(browser, adapter))

    # (c) clicking the resolved control directly
    clicked = adapter.click(browser.page, "unmute")
    time.sleep(1.0)
    _p(f"STEP 3  after adapter.click('unmute')  [matched={clicked}]",
       _snapshot(browser, adapter))

    print("\n[audiodiag] DONE. Read which STEP flipped aria_pressed / svg fill / class.")
    print("[audiodiag] Also confirm the recorded sink picks it up:")
    print("[audiodiag]   docker exec singularity_core pactl list short sink-inputs")
    print("[audiodiag] Leaving Chrome up for manual DevTools inspection; Ctrl-C to close.")
    # Block until Ctrl-C. All teardown (browser close + display-down-if-raised) is
    # owned by main()'s finally — don't close here or it double-closes.
    try:
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
