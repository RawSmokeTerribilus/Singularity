import requests
import os
import sys
import logging
from pathlib import Path

# id_resolver lives in the sibling RawLoadrr project. Reuse its multi-provider
# cross-reference consensus instead of this module's old blind behaviour of
# taking TMDB search.results[0] -- that mis-identified releases whose entry
# was missing or out-ranked on TMDB (regional licensing, renamed titles...).
_RL = Path(__file__).resolve().parent.parent.parent / "RawLoadrr"
if str(_RL) not in sys.path:
    sys.path.insert(0, str(_RL))
try:
    from src import id_resolver as _idr
except Exception:                                              # noqa: BLE001
    _idr = None
try:
    from data.config import config as _rl_config
except Exception:                                              # noqa: BLE001
    _rl_config = None


class MetadataProvider:
    def __init__(self):
        self.api_key = os.getenv("TMDB_API_KEY", "")
        self.base_url = "https://api.themoviedb.org/3"

    def _config(self):
        """Config for id_resolver: RawLoadrr's if importable, else from env."""
        if _rl_config:
            return _rl_config
        return {"DEFAULT": {"tmdb_api": self.api_key,
                            "imdb_api": os.getenv("IMDB_API_KEY", "")}}

    def get_best_match(self, name, year=None, category="TV"):
        """
        Resolve a title to a metadata id via cross-provider consensus.
        Returns {id, clean_name, year, type} only on a confirmed match
        (>=2 providers agree); returns None otherwise -- never a blind guess.
        """
        if _idr is not None:
            try:
                res = _idr.resolve(name, year, category, self._config(),
                                   mal_hint=False,
                                   log=lambda m: logging.debug(m))
                if res["confidence"] == "high" and res["tmdb"]:
                    return {
                        "id": res["tmdb"],
                        "clean_name": res["title"] or name,
                        "year": str(res["year"] or year or "0000")[:4],
                        "type": "tv" if res["category"] == "TV" else "movie",
                    }
                logging.warning(f"No confident match for '{name}' "
                                f"(confidence={res['confidence']})")
                return None
            except Exception as e:                              # noqa: BLE001
                logging.error(f"id_resolver failed for '{name}': {e}")
                # fall through to the legacy direct TMDB search

        return self._legacy_tmdb(name, year)

    def _legacy_tmdb(self, name, year=None):
        """Direct TMDB multi-search. Fallback only -- id_resolver unavailable."""
        search_url = f"{self.base_url}/search/multi"
        params = {"api_key": self.api_key, "query": name, "language": "es-ES"}
        if year:
            params["year"] = year
            params["first_air_date_year"] = year
        try:
            response = requests.get(search_url, params=params, timeout=10)
            data = response.json()
            results = data.get("results", [])
            if not results:
                logging.warning(f"No se encontraron resultados para: {name}")
                return None
            first = results[0]
            return {
                "id": first.get("id"),
                "clean_name": first.get("title") or first.get("name"),
                "year": (first.get("release_date")
                         or first.get("first_air_date") or "0000")[:4],
                "type": "tv" if first.get("media_type") == "tv" else "movie",
            }
        except Exception as e:
            logging.error(f"Error en la consulta a TMDB: {e}")
            return None
