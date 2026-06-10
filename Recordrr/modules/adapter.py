# -*- coding: utf-8 -*-
"""Data-driven per-service adapter for Recordrr.

A service (Pluto, Max, Disney+, ...) is described entirely by a JSON file in
config/adapters/<service>.json — NO per-service Python. Each logical control
(play, skip_intro, next_episode, ad_marker, ...) carries an ORDERED list of
locator strategies; first one that resolves wins (self-healing across minor UI
reskins). validate() probes every required control and reports drift instead of
silently mis-recording.

Strategy forms (each a dict, tried in order):
  {"role": "button", "name": "(?i)skip"}   -> page.get_by_role(role, name=regex)
  {"text": "(?i)next episode"}             -> page.get_by_text(regex)
  {"label": "(?i)play"}                    -> page.get_by_label(regex)
  {"testid": "skip-intro"}                 -> page.get_by_test_id(...)
  {"css": "[class*=skip]"}                 -> page.locator(css)

Adding/repairing selectors = editing JSON (a volume mount), not code.
"""
import json
import re
import sys
from pathlib import Path

try:
    from Recordrr.config import recordrr_config as cfg
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
    from Recordrr.config import recordrr_config as cfg

# Controls every adapter SHOULD define; validate() flags missing/broken ones.
REQUIRED_CONTROLS = ["play", "next_episode"]
OPTIONAL_CONTROLS = ["skip_intro", "ad_marker", "fullscreen", "episode_list"]


def _rx(s):
    return re.compile(s) if isinstance(s, str) else s


class Adapter:
    def __init__(self, name: str, spec: dict):
        self.name = name
        self.spec = spec
        self.url = spec.get("url", "")
        self.controls = spec.get("controls", {})
        # per-control settle/poll knobs, all overridable in the JSON
        self.timing = spec.get("timing", {})
        # human label for the menu; falls back to the prettified file stem
        self.display = spec.get("display", name.replace("_", " ").title())
        # stub adapters (cloned selectors, never live-tuned) flag themselves here
        self.untuned = bool(spec.get("_untuned", False))
        # player keybind to toggle mute (trusted gesture). Most HTML5 players = 'm'.
        self.mute_key = spec.get("mute_key", "m")
        # Whether to drive the player into element-fullscreen ('f'/requestFullscreen)
        # AND re-assert it every poll. Default True (Pluto/RTVE/etc need it to hide
        # the URL bar). Prime sets it FALSE: requesting fullscreen on its <video>
        # makes the player reload its surface (cover/loading flash) and fullscreen
        # drops, so the per-poll re-assert THRASHES it every ad_poll seconds. With
        # --kiosk the window already fills the capture display, so player-fullscreen
        # is redundant there anyway. (asbuilt §20.5n)
        self.player_fullscreen = bool(spec.get("player_fullscreen", True))

    # ---- loading -------------------------------------------------------
    @classmethod
    def load(cls, name: str):
        path = cfg.ADAPTERS_DIR / f"{name}.json"
        if not path.exists():
            raise FileNotFoundError(f"adapter '{name}' not found at {path}")
        spec = json.loads(path.read_text(encoding="utf-8"))
        return cls(name, spec)

    @classmethod
    def available(cls):
        if not cfg.ADAPTERS_DIR.exists():
            return []
        return sorted(p.stem for p in cfg.ADAPTERS_DIR.glob("*.json"))

    # ---- locator resolution -------------------------------------------
    def _locator(self, page, strategy: dict):
        """Build a Playwright Locator from one strategy dict (not yet evaluated)."""
        if "role" in strategy:
            kw = {}
            if strategy.get("name"):
                kw["name"] = _rx(strategy["name"])
            return page.get_by_role(strategy["role"], **kw)
        if "text" in strategy:
            return page.get_by_text(_rx(strategy["text"]))
        if "label" in strategy:
            return page.get_by_label(_rx(strategy["label"]))
        if "testid" in strategy:
            return page.get_by_test_id(strategy["testid"])
        if "css" in strategy:
            return page.locator(strategy["css"])
        return None

    def resolve(self, page, control: str):
        """First strategy whose locator matches >=1 element. Returns Locator or None."""
        for strat in self.controls.get(control, []):
            try:
                loc = self._locator(page, strat)
                if loc is not None and loc.count() > 0:
                    return loc.first
            except Exception:
                continue
        return None

    def click(self, page, control: str, timeout=3000) -> bool:
        loc = self.resolve(page, control)
        if loc is None:
            return False
        try:
            loc.click(timeout=timeout)
            return True
        except Exception:
            return False

    def present(self, page, control: str) -> bool:
        return self.resolve(page, control) is not None

    # ---- semantic helpers ---------------------------------------------
    def mute_state(self, page):
        """The player's REAL mute UI state (the on-screen icon), read from the
        mute/unmute control's ARIA — decoupled from <video>.muted. Returns
        True=muted, False=unmuted, None=unknown.

        Why this exists: writing <video>.muted=false opens audio to the Pulse sink
        and records sound, but the player's own state (React/Redux) is never told,
        so its icon keeps lying AND it can re-sync that stale 'muted' state back
        onto the element on an ad/seek/episode-change → silent frames mid-record.
        To keep audio DURABLE we must drive the player's real control, and to do
        that safely we first have to read which state it's actually in."""
        loc = self.resolve(page, "unmute")
        if loc is None:
            return None
        try:
            label = (loc.get_attribute("aria-label")
                     or loc.get_attribute("title") or "").lower()
            pressed = loc.get_attribute("aria-pressed")
        except Exception:
            return None
        # aria-label is the most reliable signal. A toggle whose action reads
        # "Unmute" is currently MUTED; one reading "Mute" is currently UNMUTED.
        # Strip separators first — Pluto labels it "Un-mute Volume" and the hyphen
        # otherwise hides "unmute" from the substring test (cost us the whole (b)
        # path: mute_state wrongly read 'unmuted', so 'm' was never pressed and the
        # icon stayed red). Check 'unmute' first — it contains 'mute' as a substring.
        norm = re.sub(r"[^a-z]", "", label)        # "un-mute volume" -> "unmutevolume"
        if "unmute" in norm:
            return True
        if "mute" in norm:
            return False
        # aria-pressed fallback (semantics vary by player; pressed==muted is the
        # common toggle convention). None when the control exposes neither.
        if pressed == "true":
            return True
        if pressed == "false":
            return False
        return None

    def is_ad(self, page) -> bool:
        return self.present(page, "ad_marker")

    def skip_intro(self, page) -> bool:
        return self.click(page, "skip_intro")

    def next_episode(self, page) -> bool:
        return self.click(page, "next_episode")

    def mute_signature(self, page):
        """Dump the FULL DOM signature of the resolved `unmute` control so we can
        see what the player's mute state actually looks like in the DOM (is 'red'
        an aria-pressed flag? a class? a different <svg> path/fill?). Returns a dict
        (or {'matched': False} if the selector finds nothing — which itself is the
        finding: our unmute strategy isn't hitting the real button)."""
        loc = self.resolve(page, "unmute")
        if loc is None:
            return {"matched": False}
        try:
            return loc.evaluate(r"""
            (el) => {
              const svg = el.querySelector('svg');
              const path = el.querySelector('path');
              return {
                matched: true,
                tag: el.tagName.toLowerCase(),
                aria_label: el.getAttribute('aria-label'),
                aria_pressed: el.getAttribute('aria-pressed'),
                title: el.getAttribute('title'),
                testid: el.getAttribute('data-testid'),
                cls: (el.className || '').toString(),
                svg_cls: svg ? (svg.getAttribute('class') || '') : null,
                path_d: path ? (path.getAttribute('d') || '').slice(0, 60) : null,
                fill: svg ? getComputedStyle(svg).fill : null,
                color: getComputedStyle(el).color,
                outer: el.outerHTML.slice(0, 240),
              };
            }""")
        except Exception as e:
            return {"matched": True, "error": str(e)}

    # ---- live selector discovery --------------------------------------
    def probe(self, page):
        """Discovery aid for LIVE selector tuning. Dumps the visible interactive
        elements (role / aria-label / title / text / testid / class) from the real
        player DOM so strategies can be authored from what's actually there instead
        of guessed. Run from inside a playing episode (the player chrome must be
        on-screen — Pluto hides controls until mouse-move, so wiggle first).
        Returns a list of dicts; empty on failure."""
        js = r"""
        () => {
          const out = [];
          const els = document.querySelectorAll(
            'button,[role=button],[aria-label],[data-testid],[title]');
          els.forEach(e => {
            const r = e.getBoundingClientRect();
            if (r.width === 0 && r.height === 0) return;   // skip hidden
            out.push({
              tag: e.tagName.toLowerCase(),
              role: e.getAttribute('role') || '',
              aria: e.getAttribute('aria-label') || '',
              title: e.getAttribute('title') || '',
              testid: e.getAttribute('data-testid') || '',
              pressed: e.getAttribute('aria-pressed') || '',
              text: (e.innerText || '').trim().slice(0, 40),
              cls: (e.className || '').toString().slice(0, 70),
            });
          });
          return out;
        }"""
        try:
            return page.evaluate(js)
        except Exception:
            return []

    # ---- drift self-check ---------------------------------------------
    def validate(self, page) -> dict:
        """Probe every defined control. Returns {control: bool}. Required misses
        are the drift signal the orchestrator/TUI surfaces."""
        report = {}
        for control in list(self.controls.keys()):
            report[control] = self.present(page, control)
        return report

    def drift(self, page):
        """Return list of REQUIRED controls that no longer resolve (empty = healthy)."""
        rep = self.validate(page)
        return [c for c in REQUIRED_CONTROLS if c in self.controls and not rep.get(c)]


if __name__ == "__main__":
    # list adapters / dump one: python3 -m Recordrr.modules.adapter [name]
    if len(sys.argv) > 1:
        a = Adapter.load(sys.argv[1])
        print(f"adapter {a.name}: url={a.url}")
        for c, strats in a.controls.items():
            print(f"  {c}: {len(strats)} strategies")
    else:
        print("available adapters:", Adapter.available() or "(none — add config/adapters/*.json)")
