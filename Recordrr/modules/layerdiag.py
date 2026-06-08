# -*- coding: utf-8 -*-
"""Recordrr layer/ad diagnostic — get DATA on Pluto's aggressive overlays.

Two problems this answers:
  1. WE RECORD ADS. `ad_marker` in the adapter is a guess; to trim (or just log)
     ads we need to see what the ad-break DOM actually looks like — what class /
     testid / countdown element appears, and whether is_ad() fires on it.
  2. PLUTO KIDNAPS THE FRAME. Ad blades / related-videos rails re-render the
     player and used to wipe the control bar. This dumps document.fullscreenElement
     and the live overlay stack each tick so we can watch what changes across an
     ad transition (and confirm the popover bar survives it).

Unlike audiodiag (a fixed step sequence), this is a LIVE MONITOR: it attaches to a
playing page and prints, every few seconds, a layer snapshot. Sit on it through a
whole ad break and an episode-end → related-videos transition; copy the real
class/testid names straight into config/adapters/<svc>.json ad_marker.

Run (live session — navigate + press play in VNC first):
    docker exec -e DISPLAY=:99 -e RECORDRR_DEBUG_PORT=9222 singularity_core \
        python3 -m Recordrr.modules.layerdiag pluto pluto

With RECORDRR_DEBUG_PORT set you can ALSO open http://localhost:9222 in your real
desktop browser for full DevTools on the same page (container is network_mode:host).
Ctrl-C to stop — teardown (browser + display-if-we-raised-it) is owned by main().
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


# Anything whose id / class / aria / testid / text smells like an ad or an overlay
# that could be covering the frame. Deliberately broad — this is discovery; we
# narrow it into a precise ad_marker selector afterwards.
_LAYER_JS = r"""
() => {
  const rx = /(ad-|advert|commercial|sponsor|countdown|adbreak|ad_break|ad break|promo|upsell|overlay|paywall|related|up-?next|recommend)/i;
  const fe = document.fullscreenElement;
  const layers = [];
  document.querySelectorAll('[class],[aria-label],[data-testid],[id]').forEach(e => {
    const blob = [e.id, e.getAttribute('aria-label'), e.getAttribute('data-testid'),
                  (e.className || '').toString(), (e.innerText || '').slice(0, 50)]
                 .filter(Boolean).join(' | ');
    if (!rx.test(blob)) return;
    const r = e.getBoundingClientRect();
    if (r.width === 0 && r.height === 0) return;            // visible only
    layers.push({
      tag: e.tagName.toLowerCase(),
      id: e.id || '',
      aria: e.getAttribute('aria-label') || '',
      testid: e.getAttribute('data-testid') || '',
      cls: (e.className || '').toString().slice(0, 90),
      text: (e.innerText || '').trim().slice(0, 50),
      z: getComputedStyle(e).zIndex,
      box: [r.width | 0, r.height | 0],
    });
  });
  // dedupe + cap: the same blob can match many nested nodes
  return {
    fullscreen: fe ? { tag: fe.tagName.toLowerCase(), id: fe.id || '',
                       cls: (fe.className || '').toString().slice(0, 90) } : null,
    bar_present: !!document.getElementById('rr-bar'),
    bar_open: (() => { const b = document.getElementById('rr-bar');
                       return !!(b && b.matches && b.matches(':popover-open')); })(),
    layers: layers.slice(0, 25),
  };
}
"""


def _snapshot(browser, adapter):
    vs = browser.video_state()
    try:
        layer = browser.page.evaluate(_LAYER_JS)
    except Exception as e:
        layer = {"error": str(e)}
    return {
        "t": time.strftime("%H:%M:%S"),
        "is_ad": adapter.is_ad(browser.page),           # what the CURRENT selector says
        "video": {k: vs[k] for k in ("currentTime", "duration", "paused", "ended",
                                     "width", "height")} if vs else None,
        "fullscreen": layer.get("fullscreen"),
        "bar": {"present": layer.get("bar_present"), "popover_open": layer.get("bar_open")},
        "layers": layer.get("layers", []),
        "layer_error": layer.get("error"),
    }


def _p(snap):
    v = snap["video"]
    vline = (f"t={v['currentTime']:.0f}/{v['duration'] or '?'} "
             f"{'PAUSED' if v and v['paused'] else 'play'} "
             f"{v['width']}x{v['height']}") if v else "no-video"
    fs = snap["fullscreen"]
    fsline = f"FS=<{fs['tag']} cls={fs['cls']!r}>" if fs else "FS=none"
    bar = snap["bar"]
    print(f"\n[{snap['t']}] is_ad={snap['is_ad']}  {vline}  {fsline}  "
          f"bar(present={bar['present']},popover={bar['popover_open']})")
    if snap["layer_error"]:
        print(f"   layer probe error: {snap['layer_error']}")
    for L in snap["layers"]:
        sig = " ".join(f"{k}={L[k]!r}" for k in ("id", "aria", "testid", "text") if L[k])
        print(f"   <{L['tag']}> {sig}  cls={L['cls']!r} z={L['z']} {L['box']}")


def main():
    adapter_name = sys.argv[1] if len(sys.argv) > 1 else "pluto"
    profile = sys.argv[2] if len(sys.argv) > 2 else adapter_name
    interval = float(sys.argv[3]) if len(sys.argv) > 3 else 4.0

    adapter = Adapter.load(adapter_name)

    # OWNER CONTRACT (same as audiodiag/launcher): if WE raise the display, WE tear
    # it down on exit — a left-up :99 opens the netns X11 leak that poisons host
    # Flatpak VLC (recordrr-asbuilt §12.1). `raised` tracks ownership for finally.
    from Recordrr.modules import display
    raised = not display._alive("xvfb")
    if raised:
        info = display.up(with_vnc=True)
        print(f"[layerdiag] raised display: {info}")
    else:
        print("[layerdiag] display already up (left as-is — someone else owns it)")

    browser = RecordrrBrowser(profile)
    try:
        _run(browser, adapter, adapter_name, profile, interval)
    finally:
        try:
            browser.close()
        finally:
            if raised:
                display.down()
                print("[layerdiag] display torn down (netns leak window closed).")
            else:
                print("[layerdiag] display left up (we didn't raise it).")


def _run(browser, adapter, adapter_name, profile, interval):
    browser.open(adapter.url)
    browser.install_bar()   # exercise the popover bar live — watch it survive ads
    if cfg.DEBUG_PORT:
        print(f"[layerdiag] DevTools exposed → http://localhost:{cfg.DEBUG_PORT}")
    print(f"[layerdiag] adapter={adapter_name} profile={profile} on {cfg.DISPLAY}")
    print("[layerdiag] In VNC (127.0.0.1:5900): log in, open a show, PRESS PLAY.")
    print("[layerdiag] Waiting for playback (up to 300s)…")

    st = browser.wait_for_playback(timeout=300)
    if not st:
        print("[layerdiag] no playback detected — aborting. Did you press play in VNC?")
        return
    print(f"[layerdiag] playback detected: {st}")
    print(f"[layerdiag] MONITORING every {interval:.0f}s. Sit through a full ad break "
          "and an episode→related transition. Ctrl-C to stop.")
    print("[layerdiag] Copy real ad class/testid names below into the adapter's "
          "ad_marker. is_ad=True means the CURRENT selector already fires.")

    try:
        while True:
            _p(_snapshot(browser, adapter))
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n[layerdiag] stopped by operator.")


if __name__ == "__main__":
    main()
