# -*- coding: utf-8 -*-
"""Episode metadata for Recordrr.

Source of truth = Sonarr (already running, has the show + TVDB ids). TMDB is a
fallback for runtime/title when a show isn't in Sonarr. Everything used for:
  - per-episode output filenames (recognizable in PARA-IMPORTAR)
  - the runaway guard rail (expected runtime -> abort if wall-clock >> that)

Reuses Singularity's existing Sonarr config (SONARR_URL / SONARR_API_KEY).
"""
import sys
from pathlib import Path

import requests

try:
    from Recordrr.config import recordrr_config as cfg
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
    from Recordrr.config import recordrr_config as cfg


class Episode:
    """One episode's metadata. .runtime is seconds (0 if unknown)."""
    __slots__ = ("season", "number", "title", "runtime", "tvdb_id", "tmdb_id", "has_file")

    def __init__(self, season, number, title="", runtime=0,
                 tvdb_id=None, tmdb_id=None, has_file=False):
        self.season = int(season)
        self.number = int(number)
        self.title = title or ""
        self.runtime = int(runtime or 0)          # seconds
        self.tvdb_id = tvdb_id
        self.tmdb_id = tmdb_id
        self.has_file = bool(has_file)

    @property
    def code(self) -> str:
        return f"S{self.season:02d}E{self.number:02d}"

    def filename(self, show: str, ext: str = None) -> str:
        ext = ext or cfg.CONTAINER_EXT
        safe_show = _sanitize(show)
        safe_title = _sanitize(self.title)
        tag = f" [tmdb-{self.tmdb_id}]" if self.tmdb_id else (
            f" [tvdb-{self.tvdb_id}]" if self.tvdb_id else "")
        title_part = f" - {safe_title}" if safe_title else ""
        return f"{safe_show} - {self.code}{title_part}{tag}.{ext}"

    def __repr__(self):
        return f"<Episode {self.code} {self.title!r} {self.runtime}s>"


def _sanitize(name: str) -> str:
    """Filesystem-safe, Sonarr-import-friendly."""
    bad = '/\\:*?"<>|'
    out = "".join(c for c in (name or "") if c not in bad).strip()
    return out.rstrip(". ")


class SonarrClient:
    def __init__(self, url=None, api_key=None, timeout=15):
        self.url = (url or cfg.SONARR_URL).rstrip("/")
        self.api_key = api_key or cfg.SONARR_API_KEY
        self.timeout = timeout

    def _get(self, path, **params):
        r = requests.get(
            f"{self.url}/api/v3/{path}",
            headers={"X-Api-Key": self.api_key},
            params=params, timeout=self.timeout,
        )
        r.raise_for_status()
        return r.json()

    def find_series(self, query: str):
        """Return (series_id, title, year, tvdb_id, tmdb_id) best-matching query, or None."""
        q = query.strip().lower()
        best = None
        for s in self._get("series"):
            title = s.get("title", "")
            if q in title.lower():
                # prefer exact, else first substring hit
                exact = title.lower() == q
                if exact:
                    return _series_tuple(s)
                if best is None:
                    best = _series_tuple(s)
        return best

    def get_episodes(self, series_id, season=None):
        """All episodes for a series (optionally one season), sorted, as Episode objs."""
        raw = self._get("episode", seriesId=series_id)
        eps = []
        for e in raw:
            if season is not None and e.get("seasonNumber") != season:
                continue
            if e.get("seasonNumber", 0) == 0:        # skip specials by default
                continue
            eps.append(Episode(
                season=e.get("seasonNumber", 0),
                number=e.get("episodeNumber", 0),
                title=e.get("title", ""),
                runtime=int(e.get("runtime", 0)) * 60,   # Sonarr runtime is minutes
                tvdb_id=e.get("tvdbId"),
                has_file=e.get("hasFile", False),
            ))
        eps.sort(key=lambda x: (x.season, x.number))
        return eps


def _series_tuple(s):
    return {
        "id": s.get("id"),
        "title": s.get("title"),
        "year": s.get("year"),
        "tvdb_id": s.get("tvdbId"),
        "tmdb_id": s.get("tmdbId"),
    }


class TmdbClient:
    """Fallback when a show isn't in Sonarr. Needs TMDB_API_KEY."""
    BASE = "https://api.themoviedb.org/3"

    def __init__(self, api_key=None, timeout=15):
        self.api_key = api_key or cfg.TMDB_API_KEY
        self.timeout = timeout

    def season_episodes(self, tmdb_id, season):
        if not self.api_key:
            return []
        r = requests.get(f"{self.BASE}/tv/{tmdb_id}/season/{season}",
                         params={"api_key": self.api_key}, timeout=self.timeout)
        r.raise_for_status()
        eps = []
        for e in r.json().get("episodes", []):
            eps.append(Episode(
                season=e.get("season_number", season),
                number=e.get("episode_number", 0),
                title=e.get("name", ""),
                runtime=int(e.get("runtime") or 0) * 60,
                tmdb_id=tmdb_id,
            ))
        eps.sort(key=lambda x: (x.season, x.number))
        return eps


if __name__ == "__main__":
    # quick smoke: python3 -m Recordrr.modules.metadata "show name" [season]
    import json
    q = sys.argv[1] if len(sys.argv) > 1 else None
    season = int(sys.argv[2]) if len(sys.argv) > 2 else None
    sc = SonarrClient()
    if not q:
        print("usage: metadata.py <show> [season]"); sys.exit(1)
    s = sc.find_series(q)
    print("series:", json.dumps(s, ensure_ascii=False))
    if s:
        for e in sc.get_episodes(s["id"], season):
            print(f"  {e.code}  {e.runtime//60}min  {e.title}")
