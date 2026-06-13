# -*- coding: utf-8 -*-
"""Episode metadata for Recordrr.

Source of truth = Sonarr (already running, has the show + TVDB ids). TMDB is a
fallback for runtime/title when a show isn't in Sonarr. Everything used for:
  - per-episode output filenames (recognizable in PARA-IMPORTAR)
  - the runaway guard rail (expected runtime -> abort if wall-clock >> that)

Reuses Singularity's existing Sonarr config (SONARR_URL / SONARR_API_KEY).
"""
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

import requests


def _parse_iso(s):
    """Parse an ISO8601 string (Pluto uses '…Z') to an aware datetime, or None."""
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except Exception:
        return None

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


_ARTICLES = ("the ", "a ", "an ", "el ", "la ", "los ", "las ", "un ", "una ")


def _norm_title(s: str) -> str:
    """Matching-normalized title: casefold, accents stripped, punctuation out,
    whitespace collapsed. 'Dinosaurs: The True Story' == 'dinosaurs the true story'."""
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c)).casefold()
    s = re.sub(r"[:;,.!?'\"()\[\]&\-_]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _strip_article(s: str) -> str:
    for a in _ARTICLES:
        if s.startswith(a):
            return s[len(a):]
    return s


def _parse_year(query: str):
    """Split an optional year out of a query ('Conan 2011', 'From (2022)').
    Returns (title_part, year_or_None)."""
    q = (query or "").strip()
    ym = re.search(r"\b(?:19|20)\d{2}\b", q)
    year = int(ym.group()) if ym else None
    qt = (q.replace(ym.group(), "") if ym else q).strip(" ()[]-.").strip()
    return qt, year


def _match_tier(nq: str, ntitle: str) -> int:
    """Rank how well a normalized query matches a normalized title.
    0 exact / 1 exact-sans-article / 2 prefix / 3 whole-word / 4 substring / -1 miss."""
    if nq == ntitle:
        return 0
    if _strip_article(nq) == _strip_article(ntitle):
        return 1
    if ntitle.startswith(nq):
        return 2
    if re.search(rf"\b{re.escape(nq)}\b", ntitle):
        return 3
    if nq in ntitle:
        return 4
    return -1


class Movie:
    """One movie's metadata. Mirrors the Episode surface the orchestrator's
    record engine consumes (.code / .runtime / .title / .filename) so movie mode
    reuses the SAME single-asset record path with no episode-specific branching.
    .runtime is seconds (0 if unknown)."""
    __slots__ = ("title", "year", "runtime", "tmdb_id", "imdb_id", "has_file")

    def __init__(self, title, year=None, runtime=0, tmdb_id=None,
                 imdb_id=None, has_file=False):
        self.title = title or ""
        self.year = int(year) if year else None
        self.runtime = int(runtime or 0)          # seconds
        self.tmdb_id = tmdb_id
        self.imdb_id = imdb_id
        self.has_file = bool(has_file)

    @property
    def code(self) -> str:
        # Flight-log / status tag. Not S00E00 — a movie has no episode coords.
        return "MOVIE"

    def filename(self, show=None, ext: str = None) -> str:
        # Radarr-import-friendly: "Title (Year) [tmdb-N].ext". The `show` arg is
        # ignored (kept for call-signature parity with Episode.filename); the
        # movie title is authoritative.
        ext = ext or cfg.CONTAINER_EXT
        safe = _sanitize(self.title)
        yr = f" ({self.year})" if self.year else ""
        tag = f" [tmdb-{self.tmdb_id}]" if self.tmdb_id else (
            f" [imdb-{self.imdb_id}]" if self.imdb_id else "")
        return f"{safe}{yr}{tag}.{ext}"

    def __repr__(self):
        return f"<Movie {self.title!r} ({self.year}) {self.runtime}s>"


def _humanize_slug(slug: str) -> str:
    """'forensic-files-es' -> 'Forensic Files'. Drops a trailing locale token."""
    if not slug:
        return ""
    parts = [p for p in str(slug).replace("_", "-").split("-") if p]
    if parts and len(parts[-1]) == 2 and parts[-1].isalpha():   # 'es'/'en' locale tail
        parts = parts[:-1]
    return " ".join(w.capitalize() for w in parts)


class Program:
    """One linear-TV program from a provider's EPG (Pluto's in-page store timeline).

    Mirrors the Episode/Movie surface the orchestrator's record engine consumes
    (.code / .runtime / .title / .filename) so LIVE mode reuses the SAME capture +
    finalize machinery with no episode-specific branching — exactly how Movie mode
    was bolted on.

    Crucial difference from VOD: the boundary is WALL-CLOCK (.start/.stop from the
    EPG), NOT <video>.duration. On a live channel `<video>.duration` is the growing
    HLS/DVR buffer, not the program length, so .runtime here comes from stop-start
    (for the runaway guard) and the real cut is `now >= stop` in the orchestrator.

    Fields come from the store as a CANDIDATE; the TMDB confirm layer
    (guide.enrich) may correct season/number/title and fill tmdb_id (Pluto's ep
    numbers are dirty — composite/absolute on some channels)."""
    __slots__ = ("channel", "name", "ptype", "season", "number", "ep_name",
                 "series_slug", "start", "stop", "tmdb_id",
                 "confirmed_series", "confirmed_title", "year")

    def __init__(self, channel="", *, name="", ptype="", season=None, number=None,
                 ep_name="", series_slug="", start=None, stop=None, tmdb_id=None,
                 year=None):
        self.channel = channel or ""
        self.name = name or ""
        self.ptype = (ptype or "").lower()              # tv | film | live
        self.season = int(season) if season not in (None, "") else None
        self.number = int(number) if number not in (None, "") else None
        self.ep_name = ep_name or ""
        self.series_slug = series_slug or ""
        self.start = start if isinstance(start, datetime) else _parse_iso(start)
        self.stop = stop if isinstance(stop, datetime) else _parse_iso(stop)
        self.tmdb_id = tmdb_id
        self.year = int(year) if year else None
        self.confirmed_series = ""        # set by the TMDB confirm layer
        self.confirmed_title = ""

    @property
    def is_series(self) -> bool:
        return self.season is not None and self.number is not None

    @property
    def title(self) -> str:
        return self.confirmed_title or self.ep_name

    @property
    def series_display(self) -> str:
        if self.confirmed_series:
            return self.confirmed_series
        # store 'name' is often "Channel/Series: Episode Title" — take the head
        if ":" in self.name:
            return self.name.split(":", 1)[0].strip()
        return _humanize_slug(self.series_slug) or self.name or self.channel

    @property
    def code(self) -> str:
        """Flight/status tag. SxxEyy for series, else 'LIVE'."""
        return f"S{self.season:02d}E{self.number:02d}" if self.is_series else "LIVE"

    @property
    def runtime(self) -> int:
        """Seconds from the EPG window (stop-start); feeds the runaway guard."""
        if self.start and self.stop:
            return max(0, int((self.stop - self.start).total_seconds()))
        return 0

    def stop_epoch(self):
        """Wall-clock cut point as a POSIX timestamp, or None (no EPG)."""
        return self.stop.timestamp() if self.stop else None

    def _disc(self, when=None) -> str:
        """Per-file discriminator so continuous-archive files never collide."""
        if self.is_series:
            return self.code
        base = self.start or when or datetime.now()
        try:
            return base.astimezone().strftime("%Y-%m-%d %H-%M")
        except Exception:
            return base.strftime("%Y-%m-%d %H-%M")

    def filename(self, channel=None, override=None, ext=None, when=None) -> str:
        """Build the output filename.

        override (name-it mode): "<base> - <disc>[ - <title>][ tag].ext".
        guessit mode: series -> "<Series> - SxxEyy - <Title> [tmdb-N].ext";
        film -> "<Name> (Year) [tmdb-N].ext"; otherwise the clock fallback
        "<Channel> - <YYYY-MM-DD HH-MM>.ext" (naming NEVER fails)."""
        ext = ext or cfg.CONTAINER_EXT
        ch = _sanitize(channel or self.channel) or "LiveTV"
        disc = self._disc(when)
        tag = f" [tmdb-{self.tmdb_id}]" if self.tmdb_id else ""
        if override:
            t = f" - {_sanitize(self.title)}" if self.title else ""
            return f"{_sanitize(override)} - {disc}{t}{tag}.{ext}"
        if self.is_series:
            t = f" - {_sanitize(self.title)}" if self.title else ""
            return f"{_sanitize(self.series_display)} - {self.code}{t}{tag}.{ext}"
        if self.ptype == "film" and self.name:
            yr = f" ({self.year})" if self.year else ""
            return f"{_sanitize(self.confirmed_title or self.name)}{yr}{tag}.{ext}"
        return f"{ch} - {disc}{tag}.{ext}"

    def __repr__(self):
        return f"<Program {self.channel!r} {self.code} {self.title or self.name!r} {self.runtime}s>"


class RadarrClient:
    """Source of truth for movie naming + the runtime guard rail. Reuses
    Singularity's existing Radarr config (RADARR_URL / RADARR_API_KEY)."""
    def __init__(self, url=None, api_key=None, timeout=15):
        self.url = (url or cfg.RADARR_URL).rstrip("/")
        self.api_key = api_key or cfg.RADARR_API_KEY
        self.timeout = timeout

    def _get(self, path, **params):
        r = requests.get(
            f"{self.url}/api/v3/{path}",
            headers={"X-Api-Key": self.api_key},
            params=params, timeout=self.timeout,
        )
        r.raise_for_status()
        return r.json()

    def search_movies(self, query: str):
        """Ranked LIBRARY Movie candidates for a title query. Reads the local
        Radarr DB (/api/v3/movie) — works with NO internet / metadata server down;
        only ADDING a movie needs the external lookup.

        Matching is normalized (case/accents/punctuation/articles) and tiered —
        see _match_tier. Understands a year in the query ('Conan 2011',
        'Conan (2011)') to disambiguate same-name films; when a year is given it
        WON'T fall back to a wrong-year match — better to return nothing and let
        the operator retry than silently record the wrong film.

        Returns [(tier, Movie), ...] sorted best-first."""
        qt, year = _parse_year(query)
        nq = _norm_title(qt)
        if not nq:
            return []
        hits = []
        for m in self._get("movie"):
            tier = _match_tier(nq, _norm_title(m.get("title", "")))
            if tier < 0:
                continue
            if year is not None and m.get("year") != year:
                continue                                # year given: ignore other years
            hits.append((tier, m))
        hits.sort(key=lambda t: (t[0], abs(len(_norm_title(t[1].get("title", ""))) - len(nq)),
                                 t[1].get("title", "")))
        return [(tier, _movie_obj(m)) for tier, m in hits]

    def find_movie(self, query: str):
        """Best-matching LIBRARY Movie for a title query, or None."""
        hits = self.search_movies(query)
        return hits[0][1] if hits else None


def _movie_obj(m):
    return Movie(
        title=m.get("title", ""),
        year=m.get("year"),
        runtime=int(m.get("runtime", 0)) * 60,    # Radarr runtime is minutes
        tmdb_id=m.get("tmdbId"),
        imdb_id=m.get("imdbId"),
        has_file=m.get("hasFile", False),
    )


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

    def search_series(self, query: str):
        """Ranked library candidates for a series query. Normalized + tiered
        matching (see _match_tier) with optional year disambiguation
        ('From 2022') — year given but absent in the library ranks nothing,
        same no-silent-wrong-year policy as Radarr.

        Returns [{... _series_tuple keys ..., 'tier': N}, ...] best-first."""
        qt, year = _parse_year(query)
        nq = _norm_title(qt)
        if not nq:
            return []
        hits = []
        for s in self._get("series"):
            tier = _match_tier(nq, _norm_title(s.get("title", "")))
            if tier < 0:
                continue
            if year is not None and s.get("year") != year:
                continue
            hits.append((tier, s))
        hits.sort(key=lambda t: (t[0], abs(len(_norm_title(t[1].get("title", ""))) - len(nq)),
                                 t[1].get("title", "")))
        return [dict(_series_tuple(s), tier=tier) for tier, s in hits]

    def find_series(self, query: str):
        """Best-matching {id, title, year, tvdb_id, tmdb_id} for query, or None."""
        hits = self.search_series(query)
        return hits[0] if hits else None

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

    def search_tv(self, name):
        """Best TV match for a name → {tmdb_id, name, year} or None. The confirm
        layer for live series naming (Pluto's seriesSlug/name → canonical title)."""
        if not self.api_key or not name:
            return None
        try:
            r = requests.get(f"{self.BASE}/search/tv",
                             params={"api_key": self.api_key, "query": name},
                             timeout=self.timeout)
            r.raise_for_status()
            res = r.json().get("results") or []
            if not res:
                return None
            top = res[0]
            yr = (top.get("first_air_date") or "")[:4]
            return {"tmdb_id": top.get("id"), "name": top.get("name", name),
                    "year": int(yr) if yr.isdigit() else None}
        except Exception:
            return None

    def tv_episode(self, tmdb_id, season, number):
        """One episode's {title, runtime_s} from TMDB, or None. Used to correct a
        dirty store episode title/number on a live series channel."""
        if not self.api_key or tmdb_id is None:
            return None
        try:
            r = requests.get(f"{self.BASE}/tv/{tmdb_id}/season/{season}/episode/{number}",
                             params={"api_key": self.api_key}, timeout=self.timeout)
            r.raise_for_status()
            e = r.json()
            return {"title": e.get("name", ""),
                    "runtime_s": int(e.get("runtime") or 0) * 60}
        except Exception:
            return None

    def search_movie(self, name):
        """Best movie match → {tmdb_id, title, year} or None (live film naming)."""
        if not self.api_key or not name:
            return None
        try:
            r = requests.get(f"{self.BASE}/search/movie",
                             params={"api_key": self.api_key, "query": name},
                             timeout=self.timeout)
            r.raise_for_status()
            res = r.json().get("results") or []
            if not res:
                return None
            top = res[0]
            yr = (top.get("release_date") or "")[:4]
            return {"tmdb_id": top.get("id"), "title": top.get("title", name),
                    "year": int(yr) if yr.isdigit() else None}
        except Exception:
            return None

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
