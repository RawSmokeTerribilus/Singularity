# -*- coding: utf-8 -*-
"""Recordrr live-TV guide — the "no-arr index" for Pluto linear channels.

VOD has Sonarr/Radarr as its index. Linear channels are in NO arr, so the index
comes from the streaming app itself. On Pluto that is the React/Redux store at
`window.appStore` — read from the app's OWN in-memory state (no backend call; same
legal posture as reading the painted DOM, just structured). Recon 2026-06-09 proved
it carries a full EPG plus the live player signals — see recordrr-asbuilt §20.

This client is the cascade the user asked for:
  store (primary)  ->  TMDB (confirm/enrich)  ->  wall-clock (fallback that never
  fails to name).

What the store gives us (PlutoGuideClient reads these via page.evaluate):
  data.liveTV.list        - the channel catalogue ({id,name,number,slug,...})
  data.liveTV.timelines   - the EPG, a dict keyed by PROGRAM id; each entry has
                            {start, stop, duration, channelID, data:{name,
                            episodeName, season, number, type(tv|film|live),
                            seriesSlug,...}}. now-playing = filter by channelID +
                            start<=now<stop.
  videoPlayer.ui          - live signals: playingState ('ad'|'content'),
                            volumeState ('muted'|...), state ('fullscreen'|...).
  videoPlayer.content.ID  - the channel currently on screen.

DOM selectors stay as a FALLBACK (adapter.is_ad etc.) for when the store path is
unavailable (store shape change, or a non-Pluto provider before it has its own
guide client).
"""
import sys
from pathlib import Path

try:
    from Recordrr.config import recordrr_config as cfg
    from Recordrr.modules.metadata import Program, TmdbClient
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
    from Recordrr.config import recordrr_config as cfg
    from Recordrr.modules.metadata import Program, TmdbClient


# JS read of the Redux store. Returns null if the store isn't present (non-Pluto
# page, or shape changed) so the caller can fall back. All read-only.
_NOW_NEXT_JS = r"""
(cid) => {
  try {
    const st = window.appStore && window.appStore.getState
      ? window.appStore.getState() : null;
    if (!st || !st.data || !st.data.liveTV) return null;
    const lt = st.data.liveTV;
    cid = cid || (st.videoPlayer && st.videoPlayer.content && st.videoPlayer.content.ID);
    if (!cid) return null;
    // channel name: the guide `list` is only hydrated on the guide grid, NOT when
    // Pluto redirects straight into a channel player — fall back to the `channels`
    // dict (keyed by id), which stays populated for the playing channel.
    const chDict = lt.channels || {};
    const chan = (lt.list || []).find(c => (c.id || c._id) === cid)
      || chDict[cid] || {};
    const tl = lt.timelines || {};
    const now = Date.now();
    const mine = Object.values(tl)
      .filter(t => t && t.channelID === cid && t.start && t.stop)
      .sort((a, b) => new Date(a.start) - new Date(b.start));
    const pack = t => t ? {
      start: t.start, stop: t.stop,
      name: t.data && t.data.name, ptype: t.data && t.data.type,
      season: t.data && t.data.season, number: t.data && t.data.number,
      epName: t.data && t.data.episodeName, seriesSlug: t.data && t.data.seriesSlug
    } : null;
    let ci = -1;
    for (let i = 0; i < mine.length; i++) {
      if (new Date(mine[i].start) <= now && now < new Date(mine[i].stop)) { ci = i; break; }
    }
    return {
      channelID: cid, channelName: chan.name || '', channelNumber: chan.number || null,
      channelSlug: chan.slug || '',
      current: ci >= 0 ? pack(mine[ci]) : null,
      next: ci >= 0 && mine[ci + 1] ? pack(mine[ci + 1]) : null,
      count: mine.length
    };
  } catch (e) { return { err: String(e) }; }
}
"""

_SIGNALS_JS = r"""
() => {
  try {
    const st = window.appStore && window.appStore.getState
      ? window.appStore.getState() : null;
    if (!st || !st.videoPlayer) return null;
    const vp = st.videoPlayer, ui = vp.ui || {};
    return {
      channelID: vp.content && vp.content.ID,
      playingState: ui.playingState,   // 'ad' | 'content'
      volumeState: ui.volumeState,     // 'muted' | ...
      uiState: ui.state,               // 'fullscreen' | ...
      adTotal: ui.adTotal, adIndex: ui.adCurrentIndex
    };
  } catch (e) { return null; }
}
"""

_CHANNELS_JS = r"""
() => {
  try {
    const lt = window.appStore.getState().data.liveTV;
    // Union of the guide `list` (grid view) and the `channels` dict (always has
    // the loaded channels) so picking works whether or not the full grid loaded.
    const seen = {}, out = [];
    const add = c => {
      if (!c) return;
      const id = c.id || c._id;
      if (!id || !c.name || seen[id]) return;
      seen[id] = 1;
      out.push({ id, name: c.name, number: c.number, slug: c.slug });
    };
    (lt.list || []).forEach(add);
    Object.values(lt.channels || {}).forEach(add);
    return out;
  } catch (e) { return []; }
}
"""


class PlutoGuideClient:
    """Reads the Pluto live guide + signals off the page's own store."""

    LIVE_URL = "https://pluto.tv/en/live-tv"

    def __init__(self, browser, tmdb=None):
        self.browser = browser
        self.tmdb = tmdb if tmdb is not None else TmdbClient()

    # ---- raw store reads (best-effort, never raise) ----------------------
    def _eval(self, js, *args):
        try:
            return self.browser.page.evaluate(js, *args)
        except Exception:
            return None

    def channels(self):
        """All live channels [{id,name,number,slug}], sorted by channel number."""
        rows = self._eval(_CHANNELS_JS) or []
        return sorted(rows, key=lambda c: (c.get("number") or 9999, c.get("name") or ""))

    def find_channel(self, query):
        """Resolve a channel by number (digits) or name/slug substring → row|None."""
        q = (query or "").strip().lower()
        if not q:
            return None
        rows = self.channels()
        if q.isdigit():
            n = int(q)
            for c in rows:
                if c.get("number") == n:
                    return c
        exact = next((c for c in rows if (c.get("name") or "").lower() == q), None)
        if exact:
            return exact
        return next((c for c in rows
                     if q in (c.get("name") or "").lower()
                     or q in (c.get("slug") or "").lower()), None)

    def channel_url(self, channel) -> str:
        cid = channel.get("id") if isinstance(channel, dict) else channel
        return f"{self.LIVE_URL}/{cid}"

    def live_signals(self):
        """{playingState, volumeState, uiState, adTotal, channelID} or None."""
        return self._eval(_SIGNALS_JS)

    def is_ad(self):
        """Store-driven ad gate for live (clean — no DOM ad_marker guessing).
        Returns True/False, or None when the store signal is unavailable so the
        caller can fall back to the DOM adapter.is_ad()."""
        sig = self.live_signals()
        if not sig or sig.get("playingState") is None:
            return None
        return sig.get("playingState") == "ad"

    # ---- the EPG (the no-arr index) --------------------------------------
    def _build(self, channel_name, raw):
        if not raw:
            return None
        return Program(
            channel=channel_name,
            name=raw.get("name") or "",
            ptype=raw.get("ptype") or "",
            season=raw.get("season"),
            number=raw.get("number"),
            ep_name=raw.get("epName") or "",
            series_slug=raw.get("seriesSlug") or "",
            start=raw.get("start"),
            stop=raw.get("stop"),
        )

    def now_next(self, channel_id=None):
        """(current Program|None, next Program|None, channel_name). Resolves the
        playing channel from the store if channel_id is omitted."""
        data = self._eval(_NOW_NEXT_JS, channel_id)
        if not data or data.get("err"):
            return None, None, ""
        cn = data.get("channelName") or ""
        return (self._build(cn, data.get("current")),
                self._build(cn, data.get("next")), cn)

    def current_program(self, channel_id=None):
        cur, _, _ = self.now_next(channel_id)
        return cur

    # ---- cascade layer 2: TMDB confirm/enrich ----------------------------
    def enrich(self, program) -> str:
        """Confirm/correct a store program against TMDB (best-effort, never
        raises). Returns the cascade source actually used: 'store+tmdb' | 'store'
        | 'clock'. Fills program.tmdb_id / confirmed_series / confirmed_title /
        year when TMDB agrees. Pluto's store ep-numbers are dirty, so this is
        where a wrong S/E title gets the real one."""
        if program is None:
            return "clock"
        if not getattr(self.tmdb, "api_key", ""):
            return "store" if program.name else "clock"
        try:
            if program.is_series:
                key = program.series_display or program.name
                hit = self.tmdb.search_tv(key)
                if hit:
                    program.tmdb_id = hit["tmdb_id"]
                    program.confirmed_series = hit["name"]
                    ep = self.tmdb.tv_episode(hit["tmdb_id"], program.season,
                                              program.number)
                    if ep and ep.get("title"):
                        program.confirmed_title = ep["title"]
                    return "store+tmdb"
            elif program.ptype == "film" and program.name:
                # store 'name' may be "Channel: Title" — try the tail too
                cand = program.name.split(":", 1)[-1].strip()
                hit = self.tmdb.search_movie(cand) or self.tmdb.search_movie(program.name)
                if hit:
                    program.tmdb_id = hit["tmdb_id"]
                    program.confirmed_title = hit["title"]
                    program.year = hit.get("year")
                    return "store+tmdb"
        except Exception:
            pass
        return "store" if program.name else "clock"


def get_guide_client(provider, browser, tmdb=None):
    """Factory: a provider's live-guide client. Only Pluto exists today; others
    fall back to DOM adapters until they get their own client."""
    if (provider or "").lower() == "pluto":
        return PlutoGuideClient(browser, tmdb=tmdb)
    return PlutoGuideClient(browser, tmdb=tmdb)   # default: try the Pluto store shape


if __name__ == "__main__":
    # Smoke (needs a live display + a Pluto page already open under CDP). Prints
    # the resolved now/next + signals for the playing channel.
    import json
    from Recordrr.modules.browser import RecordrrBrowser
    prof = sys.argv[1] if len(sys.argv) > 1 else "pluto"
    b = RecordrrBrowser(prof)
    b.open(PlutoGuideClient.LIVE_URL)
    g = PlutoGuideClient(b)
    cur, nxt, cn = g.now_next()
    print("channel:", cn)
    print("signals:", json.dumps(g.live_signals(), ensure_ascii=False))
    print("current:", repr(cur), "->", cur.filename(cn) if cur else None)
    print("next:   ", repr(nxt))
    b.close()
