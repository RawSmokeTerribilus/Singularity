# -*- coding: utf-8 -*-
"""
library -- de qué tipo es cada cosa de un árbol de ficheros.

Existe como módulo aparte, y no metido en `build_recursive_queue()`, porque hay
al menos TRES consumidores y sólo uno es la cola de subida:

  1. `upload.py`  -- construir la cola y avisar si el directorio es una mezcla.
  2. `rawncher.py` -- decirle al operador qué hay ahí dentro ANTES de disparar.
  3. el triaje y el CSI -- que para vídeo ya generan listas `.txt` que luego
     ceban a RawLoadrr, y que para libros y juegos harán lo mismo.

Si la clasificación vive dentro de la cola, el tercero tiene que reimplementarla
y las tres versiones se desincronizan. Por eso `scan()` devuelve el árbol
clasificado en crudo y cada cual hace con él lo suyo.

Ninguna función de aquí toca la red ni abre los ficheros: sólo mira nombres.
"""

import os
import re
import unicodedata

from src import bookinfo
from src import gameinfo

VIDEO_EXTS = ('.mkv', '.mp4', '.avi', '.ts', '.m2ts', '.m4v')

KINDS = ('video', 'audiobook', 'book', 'game')

# Etiquetas para hablarle a una persona.
LABELS = {
    'video': 'vídeo',
    'book': 'e-book',
    'audiobook': 'audiolibro',
    'game': 'juego',
}


def _game_exts(explicit):
    """
    Con `--only game` entran también las ambiguas.

    Fuera de ese caso hay que dejarlas pasar de largo: `.iso` se lo pelea con
    MKVerything, que ripea todo `.iso` de un árbol como disco de vídeo, y
    `.cue` es también el sidecar de un rip de CD de audio.
    """
    return gameinfo.GAME_EXTS if explicit else gameinfo.GAME_EXTS_AUTO


def classify(name, only=None):
    """
    -> 'video' | 'audiobook' | 'book' | 'game' | None

    El orden importa. El audiolibro va ANTES que el e-book y que el audio
    porque un `.m4b` es las tres cosas a la vez y gana quien pregunta primero.
    """
    lower = str(name).lower()
    explicit_game = bool(only and 'game' in only)

    if lower.endswith(bookinfo.AUDIOBOOK_EXTS):
        return 'audiobook'
    if lower.endswith(VIDEO_EXTS):
        return 'video'
    if lower.endswith(bookinfo.EBOOK_EXTS):
        return 'book'
    if lower.endswith(_game_exts(explicit_game)):
        return 'game'

    return None


def scan(root, only=None):
    """
    Recorre un árbol y devuelve `{tipo: [rutas]}`.

    Pensado también para el sistema de listados: quien quiera escribir un
    `.txt` de rutas para cebar a RawLoadrr sólo tiene que volcar la lista del
    tipo que le interese.
    """
    found = {kind: [] for kind in KINDS}

    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            kind = classify(name, only)
            if kind and (not only or kind in only):
                found[kind].append(os.path.join(dirpath, name))

    return {k: v for k, v in found.items() if v}


def counts(found):
    """`{tipo: [rutas]}` -> `[(tipo, n), ...]`, en el orden de KINDS."""
    return [(k, len(found[k])) for k in KINDS if found.get(k)]


def describe(found):
    """"16 de e-book, 5 de juego" -- para hablarle a una persona."""
    return ", ".join(f"{n} de {LABELS[k]}" for k, n in counts(found))


def is_mixed(found):
    """
    ¿Hay más de un tipo?

    Éste es el caso peligroso y el único que justifica parar: una biblioteca
    ordenada es homogénea y nunca lo ve. Una carpeta de descargas, sí.
    """
    return len(counts(found)) > 1


# ─── ¿esto es el nombre de una obra? ─────────────────────────────────────────
#
# La extensión no distingue "Contrato.pdf" de "El Quijote.pdf", así que no es
# ahí donde se puede cribar. Quien sentencia es el proveedor: si Google Books
# no conoce el libro y IGDB no conoce el juego, no hay id y no se sube.
#
# Esto de aquí NO sentencia. Sólo evita gastar una petición en lo que no puede
# ser el título de nada, y permite dar un motivo entendible en vez de un "no
# encontrado" seco. Es a propósito CORTO y conservador: ante la duda, deja
# pasar y que decida el proveedor.

_HEX = re.compile(r'^[0-9a-f]{16,}$')
# "YTMR-YG13-006", "SH3B174A5": bloques de letras y dígitos pegados, sin
# espacios. Ningún título comercial se escribe así.
_SERIAL = re.compile(r'^[a-z0-9]*\d[a-z0-9]*([-_][a-z0-9]*\d[a-z0-9]*)+$')


def _fold(text):
    text = unicodedata.normalize('NFKD', str(text).lower())
    return ''.join(c for c in text if not unicodedata.combining(c))


def looks_like_work(name):
    """
    -> (bool, motivo)

    `False` sólo cuando es IMPOSIBLE que sea el nombre de una obra. Todo lo
    demás devuelve `True` y se lo come el proveedor, que es quien sabe.
    """
    stem = _fold(os.path.splitext(os.path.basename(str(name)))[0]).strip()

    if len(stem) < 3:
        return False, "el nombre no llega a tres caracteres"

    if not any(c.isalpha() for c in stem):
        return False, "el nombre no tiene ni una letra"

    compact = re.sub(r'[\s._-]+', '', stem)

    if _HEX.match(compact):
        return False, "el nombre es un hash, no un título"

    if _SERIAL.match(re.sub(r'[\s.]+', '-', stem)):
        return False, "el nombre es un número de serie, no un título"

    # Un título necesita vocales. "SH3B174A5" no las tiene donde toca.
    letters = [c for c in compact if c.isalpha()]
    if letters and sum(c in 'aeiou' for c in letters) / len(letters) < 0.15:
        return False, "el nombre no tiene vocales suficientes para ser un título"

    return True, ""
