"""
Book and audiobook identification for RawLoadrr.

The Python twin of the tracker's app/Services/Books + app/Services/Audiobooks.
Same providers, same thresholds, same verdict vocabulary (high / low / none),
so an upload identified here and the same upload identified by the tracker do
not disagree about what a book is.

Why only Google Books identifies e-books: OpenLibrary was measured against the
live API on 2026-08-20 and does not cover a Spanish catalogue -- 404 by ISBN,
and a title search that returns a different book altogether. Letting it vote
would inject false positives, so it is not consulted here at all.

Audiobooks need two hops because Audnexus is addressable by ASIN and nothing
else: Audible's catalogue turns a title into ASINs, Audnexus turns an ASIN
into a record. Audible's own relevance ordering is not trusted -- measured, it
put the correct recording third -- so every hit is scored.
"""

import re
import unicodedata
from difflib import SequenceMatcher

import requests

TIMEOUT = 12
ATTEMPTS = 3                 # Google Books answers 503 at random; one try loses results
MIN_CANDIDATE_SCORE = 0.50
TRUST_SCORE = 0.90
LEAD_MARGIN = 0.05           # two editions of one book tie exactly; that is a question, not a win

GOOGLE_BOOKS = "https://www.googleapis.com/books/v1/volumes"
AUDNEXUS = "https://api.audnex.us"

# The `imageLinks` block of the API only ever hands back a 128px thumbnail, which
# looks miserable on a torrent page. The content endpoint takes an undocumented
# `zoom`, and measured against the real API it goes up to 2177x2771 for the same
# volume that `imageLinks` renders at 128x170.
#
# Always ask for 6 and never compute anything: the parameter self-limits to
# whatever resolution the publisher actually uploaded, so asking for more than
# exists simply returns the best available. And it is NOT a linear scale --
# zoom=5 gives back the same 128px as zoom=1 -- so there is nothing to interpolate.
GOOGLE_COVER = ("https://books.google.com/books/content"
                "?id={vid}&printsec=frontcover&img=1&zoom=6")

# Fallback only. Measured on the same book, OpenLibrary's large cover is
# 128x164 / 6.4 KiB against Google's 2177x2771 / 539 KiB, so it never goes first.
# `default=false` is not optional: without it OpenLibrary answers 200 with a
# placeholder image instead of 404, and you end up caching filler.
OPENLIBRARY_COVER = "https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg?default=false"
AUDIBLE_DOMAINS = {
    'es': 'api.audible.es', 'us': 'api.audible.com', 'uk': 'api.audible.co.uk',
    'fr': 'api.audible.fr', 'de': 'api.audible.de', 'it': 'api.audible.it',
    'ca': 'api.audible.ca', 'au': 'api.audible.com.au', 'br': 'api.audible.com.br',
    'jp': 'api.audible.co.jp', 'in': 'api.audible.in',
}


# ─── scoring (kept identical to id_resolver so "same title" means one thing) ──
def _norm(s):
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", str(s).lower())
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r"[^0-9a-z]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _title_score(query, candidate):
    q, c = _norm(query), _norm(candidate)
    if not q or not c:
        return 0.0
    if q == c:
        return 1.0
    ratio = SequenceMatcher(None, q, c).ratio()
    qt, ct = set(q.split()), set(c.split())
    if qt and ct and (qt <= ct or ct <= qt):
        ratio = max(ratio, 0.88)
    return ratio


# ─── ISBN ────────────────────────────────────────────────────────────────────
def _isbn_check13(body12):
    total = sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(body12))
    return str((10 - total % 10) % 10)


def to_isbn13(raw):
    """Normalise any ISBN to a valid ISBN-13, or '' when it is neither."""
    s = re.sub(r"[^0-9Xx]", "", str(raw or "")).upper()

    if len(s) == 13:
        return s if s.isdigit() and _isbn_check13(s[:12]) == s[12] else ""

    if len(s) == 10 and re.fullmatch(r"\d{9}[0-9X]", s):
        total = sum((10 if c == "X" else int(c)) * (10 - i) for i, c in enumerate(s))
        if total % 11 == 0:
            body = "978" + s[:9]
            return body + _isbn_check13(body)

    return ""


# ─── Google Books ────────────────────────────────────────────────────────────
def _google_get(params, key, log):
    params = dict(params, key=key)

    for attempt in range(ATTEMPTS):
        try:
            r = requests.get(GOOGLE_BOOKS, params=params, timeout=TIMEOUT)
            r.raise_for_status()
            items = (r.json() or {}).get("items") or []
            if items:
                return items
        except Exception as e:                                  # noqa: BLE001
            log(f"google books failed: {e}")

        if attempt < ATTEMPTS - 1:
            import time
            time.sleep(0.4 * (attempt + 1))

    return []


def _best_image_link(v):
    """The largest thumbnail Google admits to, as a fallback for the cover."""
    links = v.get("imageLinks") or {}
    for size in ("extraLarge", "large", "medium", "small",
                 "thumbnail", "smallThumbnail"):
        if links.get(size):
            # These come back over plain http and with edge curl painted on.
            return links[size].replace("http://", "https://").replace("&edge=curl", "")
    return ""


def _google_candidate(item):
    v = (item or {}).get("volumeInfo") or {}
    if not v.get("title"):
        return None

    # The volume id is a sibling of volumeInfo in the response we already asked
    # for to identify the book, so the cover costs no second request.
    volume_id = (item or {}).get("id") or ""

    isbn13 = isbn10 = ""
    for ident in v.get("industryIdentifiers") or []:
        if ident.get("type") == "ISBN_13":
            isbn13 = to_isbn13(ident.get("identifier"))
        elif ident.get("type") == "ISBN_10":
            isbn10 = re.sub(r"[^0-9Xx]", "", str(ident.get("identifier") or "")).upper()

    if not isbn13 and isbn10:
        isbn13 = to_isbn13(isbn10)

    if not isbn13:
        return None            # nothing to key a row on

    year = None
    m = re.search(r"(\d{4})", str(v.get("publishedDate") or ""))
    if m:
        year = int(m.group(1))

    cover = GOOGLE_COVER.format(vid=volume_id) if volume_id else ""

    return {
        "provider": "google", "title": v["title"], "subtitle": v.get("subtitle", ""),
        "authors": [str(a) for a in (v.get("authors") or [])],
        "year": year, "isbn13": isbn13, "isbn10": isbn10,
        "publisher": v.get("publisher", ""), "page_count": v.get("pageCount"),
        "language": v.get("language", ""), "score": 0.0,
        "volume_id": volume_id,
        "cover_url": cover,
        "cover_fallbacks": [u for u in (_best_image_link(v),
                                        OPENLIBRARY_COVER.format(isbn=isbn13)) if u],
        # Google's own subject headings. Worth keeping: OpenLibrary's `subjects`
        # were measured to return the same concept in five languages plus tags
        # belonging to other works entirely.
        "genres": [str(c) for c in (v.get("categories") or [])],
        "description": v.get("description", "") or "",
    }


def _score_book(cand, title, author, year):
    score = _title_score(title, cand["title"])

    if cand.get("subtitle"):
        score = max(score, _title_score(title, f"{cand['title']} {cand['subtitle']}"))

    if year and cand.get("year"):
        diff = abs(int(year) - int(cand["year"]))
        if diff == 0:
            score += 0.05
        elif diff > 1:
            score -= 0.30

    if author and cand.get("authors"):
        if max(_title_score(author, a) for a in cand["authors"]) >= 0.85:
            score += 0.05

    return max(0.0, min(1.0, score))



# ─── cascada de títulos ──────────────────────────────────────────────────────
_PARENTESIS_FINAL = re.compile(r'\s*[\(\[][^\)\]]*[\)\]]\s*$')
_SEQ_FINAL = re.compile(r'\b\d{1,2}\s*$')


def query_variants(title, author=None):
    """
    Del candidato más fiel al más laxo. Se para en el primero que dé algo.

    Nace de un caso real: el `.m4a` de *El arte de la guerra* traía en las
    etiquetas "Sun Tzu - El Arte de la Guerra (Audiolibro en Castellano)".
    Audible no conoce ningún libro que se llame así, y el nombre del formato
    y del idioma pegados al título son la norma, no la excepción.

    Misma regla dura que en juegos: **nunca se recorta un número final**. "Dune
    2" y "Dune" son libros distintos, y quitar el número fabrica un acierto de
    los que puntúan perfecto y están mal.
    """
    base = str(title or '').strip()
    if not base:
        return []

    lleva_secuencia = bool(_SEQ_FINAL.search(base))
    vistos = []

    def add(texto):
        texto = re.sub(r'\s+', ' ', (texto or '')).strip(' -_,:;.')
        if len(texto) < 3:
            return
        if lleva_secuencia and not _SEQ_FINAL.search(texto):
            return
        if texto.lower() not in [v.lower() for v in vistos]:
            vistos.append(texto)

    add(base)

    # Los paréntesis finales se van de uno en uno: "(Audiolibro) (192kbit_AAC)"
    # son dos, y quitar sólo el último no arregla nada.
    recortado = base
    while _PARENTESIS_FINAL.search(recortado):
        recortado = _PARENTESIS_FINAL.sub('', recortado)
        add(recortado)

    # "Autor - Título" es como nombra medio mundo sus ficheros. Sólo se quita
    # cuando la parte de delante ES el autor que ya conocemos: cortar por el
    # primer guion a ciegas destroza "Cien años - de soledad" y parecidos.
    if author:
        for texto in list(vistos):
            for sep in (' - ', ' – ', ': '):
                if sep in texto:
                    izquierda, derecha = texto.split(sep, 1)
                    if _title_score(author, izquierda) >= 0.80:
                        add(derecha)

    for texto in list(vistos):
        add(re.sub(r'[_\.]+', ' ', texto))

    return vistos


def resolve_book(title, author=None, year=None, isbn_hint=None, config=None, log=None):
    """
    -> {'confidence': high|low|none, 'isbn13': str, 'score': float,
        'record': dict|None, 'reason': str}
    """
    log = log or (lambda m: None)
    key = ((config or {}).get("DEFAULT", {}) or {}).get("google_books_api") or ""

    hint = to_isbn13(isbn_hint or "")
    if hint:
        for item in _google_get({"q": f"isbn:{hint}", "maxResults": 5}, key, log):
            cand = _google_candidate(item)
            if cand and cand["isbn13"] == hint:
                log(f"isbn hint {hint} confirmed by google books")
                return _verdict("high", 1.0, cand, "isbn supplied by uploader")

        log(f"isbn hint {hint} not found upstream")

    if not key:
        return _verdict("none", 0.0, None, "no google books api key configured")

    cands = []
    for variante in query_variants(title, author):
        q = f"intitle:{variante}"
        if author:
            q += f" inauthor:{author}"      # a literal space; a '+' is sent as %2B and 503s

        for item in _google_get({"q": q, "maxResults": 10,
                                 "langRestrict": "es", "country": "ES"}, key, log):
            cand = _google_candidate(item)
            if cand:
                # Se puntúa contra la variante QUE SE CONSULTÓ, no contra el
                # título original: si se limpió "(Audiolibro en Castellano)"
                # es porque sobraba, y penalizar al candidato por no traerlo
                # sería castigarle por acertar.
                cand["score"] = _score_book(cand, variante, author, year)
                if cand["score"] >= MIN_CANDIDATE_SCORE:
                    cands.append(cand)

        if cands:
            if variante != title:
                log(f"variante '{variante}' dio {len(cands)} candidatos")
            break

    if not cands:
        log(f"no book candidate above threshold for '{title}'")
        return _verdict("none", 0.0, None, "no candidate scored high enough")

    cands.sort(key=lambda c: -c["score"])
    best = cands[0]
    lead = best["score"] - cands[1]["score"] if len(cands) > 1 else 1.0

    if best["score"] >= TRUST_SCORE and lead >= LEAD_MARGIN:
        conf, reason = "high", "clear single match"
    else:
        conf = "low"
        reason = ("best candidate below trust score" if best["score"] < TRUST_SCORE
                  else "several editions score the same; a human picks the edition")

    log(f"resolved book '{title}' -> {conf} isbn13={best['isbn13']} "
        f"score={best['score']:.3f} lead={lead:.3f} ({reason})")

    return _verdict(conf, best["score"], best, reason)


# ─── Audible + Audnexus ──────────────────────────────────────────────────────
def _audible_search(title, author, region, log):
    domain = AUDIBLE_DOMAINS.get((region or "es").lower())
    if not domain:
        return []

    params = {
        "title": title, "num_results": 10, "products_sort_by": "Relevance",
        # Without this every product comes back with a null title.
        "response_groups": "product_desc,contributors,product_attrs",
    }
    if author:
        params["author"] = author

    try:
        r = requests.get(f"https://{domain}/1.0/catalog/products", params=params, timeout=TIMEOUT)
        r.raise_for_status()
        products = (r.json() or {}).get("products") or []
    except Exception as e:                                      # noqa: BLE001
        log(f"audible search failed: {e}")
        return []

    def names(people):
        return [p["name"] for p in (people or []) if isinstance(p, dict) and p.get("name")]

    return [{
        "asin": p.get("asin", ""), "title": p.get("title") or "",
        "subtitle": p.get("subtitle") or "",
        "authors": names(p.get("authors")), "narrators": names(p.get("narrators")),
    } for p in products if p.get("asin")]


def audnexus_book(asin, region="es", log=None):
    log = log or (lambda m: None)
    try:
        r = requests.get(f"{AUDNEXUS}/books/{asin}", params={"region": region}, timeout=TIMEOUT)
        if r.status_code == 404:
            return None
        r.raise_for_status()
        d = r.json() or {}
    except Exception as e:                                      # noqa: BLE001
        log(f"audnexus failed: {e}")
        return None

    if not d.get("title"):
        return None

    def names(items):
        return [i["name"] if isinstance(i, dict) else str(i)
                for i in (items or []) if i]

    return {
        "asin": d.get("asin", asin), "title": d["title"], "subtitle": d.get("subtitle", ""),
        "authors": names(d.get("authors")), "narrators": names(d.get("narrators")),
        "series": (d.get("seriesPrimary") or {}).get("name", ""),
        "runtime_min": d.get("runtimeLengthMin"),
        "release_date": (d.get("releaseDate") or "")[:10],
        "publisher": d.get("publisherName", ""), "language": d.get("language", ""),
        "genres": names(d.get("genres")), "isbn13": to_isbn13(d.get("isbn") or ""),
        "cover_url": d.get("image", ""),
        "description": re.sub(r"<[^>]+>", "", str(d.get("summary") or d.get("description") or "")).strip(),
    }


def resolve_audiobook(title, author=None, region="es", asin_hint=None, log=None):
    log = log or (lambda m: None)

    hint = (asin_hint or "").strip().upper()
    if hint:
        rec = audnexus_book(hint, region, log)
        if rec:
            log(f"asin hint {hint} confirmed by audnexus")
            return _verdict("high", 1.0, rec, "asin supplied by uploader", asin=hint)

        log(f"asin hint {hint} unknown to audnexus in region {region}")

    # Misma cascada que en resolve_book, y por el mismo motivo: las etiquetas
    # de un audiolibro traen el idioma y el bitrate pegados al título, y
    # Audible no conoce ningún libro llamado "... (Audiolibro en Castellano)".
    scored = []
    consultado = title

    for variante in query_variants(title, author):
        products = _audible_search(variante, author, region, log)
        if not products:
            continue

        for p in products:
            score = _title_score(variante, p["title"])
            if p["subtitle"]:
                score = max(score, _title_score(variante, f"{p['title']} {p['subtitle']}"))
            if author and p["authors"] and max(_title_score(author, a) for a in p["authors"]) >= 0.85:
                score += 0.05
            score = max(0.0, min(1.0, score))
            if score >= MIN_CANDIDATE_SCORE:
                scored.append(dict(p, score=score))

        if scored:
            consultado = variante
            if variante != title:
                log(f"variante '{variante}' dio {len(scored)} candidatos en audible")
            break

    if not scored:
        log(f"no audiobook candidate above threshold for '{title}'")
        return _verdict("none", 0.0, None, "no candidate scored high enough")

    scored.sort(key=lambda c: -c["score"])
    best = scored[0]
    lead = best["score"] - scored[1]["score"] if len(scored) > 1 else 1.0

    rec = audnexus_book(best["asin"], region, log)          # only the winner costs a second hop
    if not rec:
        return _verdict("none", best["score"], None,
                        "audnexus has no record for the best match", asin=best["asin"])

    if best["score"] >= TRUST_SCORE and lead >= LEAD_MARGIN:
        conf, reason = "high", "clear single match"
    else:
        conf = "low"
        reason = ("best candidate below trust score" if best["score"] < TRUST_SCORE
                  else "several recordings score the same; a human picks the narrator")

    log(f"resolved audiobook '{title}' -> {conf} asin={best['asin']} "
        f"score={best['score']:.3f} lead={lead:.3f} ({reason})")

    return _verdict(conf, best["score"], rec, reason, asin=best["asin"])


def _verdict(confidence, score, record, reason, asin=None):
    return {
        "confidence": confidence,
        "score": round(float(score), 3),
        "isbn13": (record or {}).get("isbn13", "") if record else "",
        "asin": asin or (record or {}).get("asin", "") if record else "",
        "record": record,
        "reason": reason,
    }


if __name__ == "__main__":
    import os
    import sys
    import json

    # Run either as `python3 src/book_resolver.py` from RawLoadrr/ or directly
    # from inside src/; the config lives one level up from this file either way.
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from data.config import config as _cfg

    kind = sys.argv[1] if len(sys.argv) > 1 else "book"
    _title = sys.argv[2] if len(sys.argv) > 2 else "El nombre del viento"
    _author = sys.argv[3] if len(sys.argv) > 3 else None

    fn = resolve_book if kind == "book" else resolve_audiobook
    out = fn(_title, _author, config=_cfg, log=print) if kind == "book" \
        else fn(_title, _author, log=print)
    print(json.dumps({k: v for k, v in out.items() if k != "record"}, indent=2, ensure_ascii=False))
