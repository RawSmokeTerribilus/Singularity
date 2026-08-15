#!/usr/bin/env python3
"""06_intruso — recupera galerías en torrents de OTROS usuarios.

`05_image_regenerator` sólo alcanza lo que tú siembras: mapea el id del tracker
por el `comment` del .torrent que hay en tu cliente. El barrido de cierre de NOBS
dejó ~1200 páginas rotas de otros usuarios fuera de su alcance.

Intruso trabaja en dos pasadas, y son deliberadamente independientes:

  FASE 1 · limpiar   (minutos, sin descargas)
      Barre el tracker entero, guarda la cola CON LA DESCRIPCIÓN ORIGINAL y
      quita los enlaces muertos de todas las páginas. El spam desaparece hoy.

  FASE 2 · reparar   (horas, reanudable)   [pendiente]
      Trabaja la cola guardada: baja unas ventanas de piezas por libtorrent,
      saca capturas y las devuelve a su sitio.

Por qué la cola se guarda ANTES de limpiar:
  · limpiar destruye el criterio de selección ("tiene un host muerto"),
  · y destruye el punto de inserción donde iba la galería,
  · y una copia de la descripción original es la única vuelta atrás cuando
    estás editando páginas que no son tuyas.

Uso:
    python3 06_intruso.py --limpiar [--real|--dry-run] [--tracker NOBS]
    python3 06_intruso.py --barrer                 # sólo construir la cola
"""

import json
import os
import random
import re
import sys
import time
import importlib.util
from datetime import datetime

DIR = os.path.dirname(os.path.abspath(__file__))
if DIR not in sys.path:
    sys.path.insert(0, DIR)


# ==========================================
# ♻️  REUTILIZACIÓN DE 05
# ==========================================
# 05 es un script, no un paquete, así que se carga por ruta. Al importarlo se
# resuelve la identidad del tracker (--tracker, TRACKER_<ABBREV>_*, el doctor
# del .env…) exactamente igual que en una tirada de 05: una sola forma de
# resolver credenciales para las dos herramientas.
def _cargar_05():
    ruta = os.path.join(DIR, "05_image_regenerator.py")
    if not os.path.exists(ruta):
        print("❌ Falta 05_image_regenerator.py: Intruso reutiliza sus helpers.")
        sys.exit(1)
    spec = importlib.util.spec_from_file_location("regen05", ruta)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


R = _cargar_05()

DEAD_HOSTS   = R.DEAD_HOSTS
SITE_BASE    = None                       # se resuelve en main()
_SUF         = R._SUF
ESTADO       = R.REGEN_STATE_DIR
DELAY_MIN    = R.DELAY_MIN
DELAY_MAX    = R.DELAY_MAX

COLA      = os.path.join(ESTADO, f"intruso_cola_{_SUF}.json")
LIMPIADOS = os.path.join(ESTADO, f"intruso_limpiados_{_SUF}.txt")
MANUAL    = os.path.join(ESTADO, f"intruso_manual_{_SUF}.txt")

_ARGS = set(sys.argv[1:])


def _dry_run():
    if _ARGS & {"--real", "--no-dry-run"}:
        return False
    if _ARGS & {"--dry-run", "--seco", "--simulacro"}:
        return True
    return True                            # por defecto NO se escribe nada


DRY_RUN = _dry_run()


def _limite():
    """--limite N: parar tras N torrents. Para probar en vivo sin comprometerse."""
    args = sys.argv[1:]
    for i, a in enumerate(args):
        if a in ("--limite", "--limit") and i + 1 < len(args):
            try:
                return int(args[i + 1])
            except ValueError:
                pass
        if a.startswith("--limite="):
            try:
                return int(a.split("=", 1)[1])
            except ValueError:
                pass
    return 0


LIMITE = _limite()


# ==========================================
# 🧹 LIMPIEZA QUIRÚRGICA DE ENLACES MUERTOS
# ==========================================
# Un [url=…] cuyo destino es un host muerto, envuelva o no una imagen. Clicarlo
# lleva igual a la web de cámaras, así que el enlace se cae aunque el texto de
# dentro se quede.
RX_URL_MUERTA = re.compile(r"\[url=(?P<destino>[^\]]*?)\](?P<dentro>.*?)\[/url\]",
                           re.IGNORECASE | re.DOTALL)


def limpiar_descripcion(texto):
    """Quita SÓLO lo que apunta a un host muerto.

    Trailer, firma, banner, mediainfo, sinopsis y envoltorios se quedan byte a
    byte. Devuelve (texto_limpio, cuántas cosas se han quitado).
    """
    quitados = 0

    def _tag_completo(m):
        nonlocal quitados
        if R._es_url_muerta(m.group("web")) or R._es_url_muerta(m.group("raw")):
            quitados += 1
            return ""
        return m.group(0)

    def _img_suelta(m):
        nonlocal quitados
        if R._es_url_muerta(m.group("raw")):
            quitados += 1
            # `cierre` es un [/url] huérfano que colgaba de la etiqueta anterior
            return ""
        return m.group(0)

    def _url_suelta(m):
        nonlocal quitados
        if R._es_url_muerta(m.group("destino")):
            quitados += 1
            dentro = m.group("dentro")
            # Si sólo envolvía imágenes ya borradas no queda nada que salvar;
            # si llevaba texto, el texto se conserva y se va el enlace.
            return dentro if dentro.strip() else ""
        return m.group(0)

    t = R.RX_IMG_TAG.sub(_tag_completo, texto)
    t = R.RX_IMG_SUELTO.sub(_img_suelta, t)
    t = RX_URL_MUERTA.sub(_url_suelta, t)

    # Etiquetas [url=…] ABIERTAS y sin su [/url]. Existen de verdad: el id 5082
    # de NOBS trae '[url=https://imgbox.com/EZKXIs05] \r' sin cerrar, así que la
    # regex de pareja no casa y el enlace sobrevivía a todo lo anterior. Quitar
    # una etiqueta huérfana no puede perder texto visible: es sólo marcado.
    def _url_abierta_huerfana(m):
        nonlocal quitados
        if R._es_url_muerta(m.group(1)):
            quitados += 1
            return ""
        return m.group(0)

    t = re.sub(r"\[url=([^\]]*?)\]", _url_abierta_huerfana, t, flags=re.IGNORECASE)

    # Envoltorios que se han quedado vacíos por el borrado. No se toca ningún
    # otro espacio: sólo se colapsa lo que el propio borrado ha dejado suelto.
    t = re.sub(r"\[center\]\s*\[/center\]", "", t, flags=re.IGNORECASE)
    t = re.sub(r"[ \t]{2,}", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)

    return t.strip(), quitados


# UNIT3D rechaza una descripción vacía ("El campo descripción es obligatorio"),
# y 23 de las 1434 se quedaban en nada al quitar los enlaces: sólo tenían la
# galería muerta. Sin esto, esas páginas conservan el spam — justo lo que no
# puede pasar. Se pone un texto mínimo para que el PATCH entre.
PLACEHOLDER = os.getenv(
    "ME_INTRUSO_PLACEHOLDER",
    "[center][i]Galería pendiente de reconstrucción.[/i][/center]",
).strip()


def quedan_muertos(texto):
    bajo = (texto or "").lower()
    return [d for d in DEAD_HOSTS if d in bajo]


RX_BBCODE = re.compile(r"\[/?[^\]]{0,80}\]")


RX_IMG_ENTERA = re.compile(r"\[img[^\]]*\][^\[]*\[/img\]", re.IGNORECASE)


def _texto_visible(s):
    """Las PALABRAS que ve el usuario, sin bbcode ni espacios de más.

    Las etiquetas de imagen se quitan ENTERAS (con su URL dentro) antes de nada:
    la URL vive ENTRE `[img]` y `[/img]`, así que quitando sólo las etiquetas
    quedaría suelta como si fuera texto, y borrar la imagen parecería una
    pérdida de contenido. Que la imagen viva no se toque lo comprueba
    `_imagenes_vivas`, que para eso está aparte.
    """
    t = RX_IMG_ENTERA.sub(" ", s or "")
    return re.sub(r"\s+", " ", RX_BBCODE.sub(" ", t)).strip()


def _imagenes_vivas(s):
    """URLs de imagen que NO son de un host muerto, en orden."""
    vivas = []
    for m in R.RX_IMG_TAG.finditer(s or ""):
        if not (R._es_url_muerta(m.group("web")) or R._es_url_muerta(m.group("raw"))):
            vivas.append(m.group("raw").strip())
    for m in R.RX_IMG_SUELTO.finditer(s or ""):
        if not R._es_url_muerta(m.group("raw")):
            vivas.append(m.group("raw").strip())
    return vivas


def comprobar_limpieza(antes, despues):
    """El invariante de ESTA fase. No vale el de 05.

    `_texto_sin_imagenes` (05) trata `[center]` y `[url]` como intocables porque
    allí la sustitución es 1 a 1. Aquí sí desaparecen a propósito: el envoltorio
    que se queda vacío, y el `[url=…]` de un enlace de texto a un host muerto
    (del que se conserva el texto). Con aquel invariante se rechazarían justo las
    limpiezas que se quieren hacer.

    Lo que de verdad no puede cambiar:
      1. ninguna palabra visible se pierde ni aparece,
      2. ninguna imagen VIVA se toca.
    """
    if _texto_visible(antes) != _texto_visible(despues):
        return False, "se perdería o alteraría texto visible"
    if _imagenes_vivas(antes) != _imagenes_vivas(despues):
        return False, "se tocaría alguna imagen que sigue viva"
    return True, ""


# ==========================================
# 🗂️ ESTADO
# ==========================================
def _leer_marcador(ruta):
    if not os.path.exists(ruta):
        return set()
    with open(ruta, "r", encoding="utf-8") as f:
        return {l.split("\t")[0].strip() for l in f if l.strip()}


def _marcar(ruta, tid, extra=""):
    with open(ruta, "a", encoding="utf-8") as f:
        f.write(f"{tid}\t{extra}\n" if extra else f"{tid}\n")


def _anotar_manual(entrada, motivo):
    """La lista que de verdad importa: lo que hay que mirar a mano.

    Dos escenarios previstos, los dos acaban en borrar el torrent tras revisar:
    sin seeds, o el fichero no da capturas aprovechables.
    """
    try:
        nuevo = not os.path.exists(MANUAL)
        with open(MANUAL, "a", encoding="utf-8") as f:
            if nuevo:
                f.write("# id\tseeders\tuploader\tmotivo\tnombre\turl\n")
            f.write("\t".join([
                str(entrada.get("id", "?")),
                str(entrada.get("seeders", "?")),
                str(entrada.get("uploader", "?")),
                motivo,
                str(entrada.get("nombre", ""))[:80],
                f"{SITE_BASE}/torrents/{entrada.get('id')}",
            ]) + "\n")
    except OSError:
        pass


# ==========================================
# 🔭 BARRIDO DEL TRACKER
# ==========================================
def barrer(session):
    """Todas las páginas con hosts muertos, con su descripción original.

    `/api/torrents` pagina por CURSOR y no avanza (repite la misma página en
    bucle): hay que usar `/api/torrents/filter`, que va por `page`. Contesta 429
    cada ~30 páginas y pide hasta ~43 s de espera.
    """
    cola, vistos, pagina = [], set(), 1
    print("🔭 Barriendo el tracker (esto tarda unos minutos)…", flush=True)

    while pagina <= 500:
        r = session.get(
            f"{SITE_BASE}/api/torrents/filter",
            params={"perPage": 100, "page": pagina, "api_token": R.TRACKER_API_KEY},
            headers={"Accept": "application/json", "User-Agent": R.CUSTOM_USER_AGENT},
            timeout=60,
        )
        if r.status_code == 429:
            espera = int(r.headers.get("Retry-After", 30) or 30) + 2
            print(f"   ⏳ 429 en la página {pagina}: espero {espera}s", flush=True)
            time.sleep(espera)
            continue
        if r.status_code != 200:
            print(f"   ⚠️  corte en HTTP {r.status_code} (página {pagina})")
            break

        datos = r.json().get("data", [])
        if not datos:
            break

        for t in datos:
            a = t.get("attributes", {}) or {}
            tid = str(t.get("id") or a.get("id") or "")
            if not tid or tid in vistos:
                continue
            vistos.add(tid)
            desc = a.get("description") or ""
            muertos = quedan_muertos(desc)
            if not muertos:
                continue
            cola.append({
                "id": tid,
                "nombre": a.get("name", ""),
                "uploader": a.get("uploader", "(anónimo)"),
                "seeders": a.get("seeders") or 0,
                "hosts_muertos": muertos,
                # La copia de seguridad: sin esto no hay marcha atrás, ni se
                # sabe dónde iba la galería cuando toque reponerla.
                "descripcion_original": desc,
            })

        if pagina % 10 == 0:
            print(f"   página {pagina}: {len(vistos)} vistos, {len(cola)} rotos", flush=True)
        pagina += 1
        time.sleep(0.25)

    print(f"✅ Barrido: {len(vistos)} torrents, {len(cola)} con enlaces muertos")
    return cola, len(vistos)


def guardar_cola(cola, total_vistos):
    # Primero lo fácil: si se para a media tirada, queda arreglado lo más
    # rentable. `seeders` viene del barrido, así que el triaje sale gratis.
    cola.sort(key=lambda e: (-int(e.get("seeders") or 0), int(e["id"])))
    R._guardar_json(COLA, {
        "tracker": _SUF,
        "creada": datetime.now().isoformat(timespec="seconds"),
        "total_en_tracker": total_vistos,
        "entradas": cola,
    })
    print(f"💾 Cola guardada: {COLA}")


# ==========================================
# 🧼 FASE 1 — LIMPIAR
# ==========================================
def limpiar_uno(session, entrada):
    tid = entrada["id"]

    form, soup, edit_url, err = R.leer_formulario(session, SITE_BASE, tid)
    if err:
        return False, err

    desc_actual, err = R.leer_descripcion(session, SITE_BASE, tid, soup)
    if err:
        return False, err

    if not quedan_muertos(desc_actual):
        return True, "ya estaba limpia"

    nueva, quitados = limpiar_descripcion(desc_actual)
    if not quitados:
        return False, "hay hosts muertos pero ningún patrón conocido casó"

    # La descripción era SÓLO la galería muerta. Vacía no se puede publicar.
    vaciada = not nueva.strip()
    if vaciada:
        nueva = PLACEHOLDER

    restos = quedan_muertos(nueva)
    if restos:
        return False, f"tras limpiar seguirían enlaces a {', '.join(restos)}"

    # Con placeholder el texto visible cambia a propósito (antes no había nada
    # que no fuera la galería), así que ese invariante no aplica; lo que sí se
    # exige igual es que no quede ningún enlace muerto.
    if not vaciada:
        seguro, motivo = comprobar_limpieza(desc_actual, nueva)
        if not seguro:
            return False, f"abortado: {motivo}"

    if DRY_RUN:
        return True, f"SIMULACRO: se quitarían {quitados} enlace(s) muerto(s)"

    payload = R.construir_payload(form, nueva)
    ok, msg = R.enviar(session, form, payload, SITE_BASE, edit_url)
    if not ok:
        return False, msg

    publicada, err = R.leer_descripcion(session, SITE_BASE, tid,
                                        __import__("bs4").BeautifulSoup("", "html.parser"))
    if err:
        return False, f"no se pudo releer para verificar: {err}"
    restos = quedan_muertos(publicada)
    if restos:
        return False, f"tras publicar siguen enlaces a {', '.join(restos)}"

    if vaciada:
        return True, f"{quitados} enlace(s) fuera — sólo había galería, queda el aviso"
    return True, f"{quitados} enlace(s) muerto(s) fuera"


def fase_limpiar(session, cola):
    hechos = _leer_marcador(LIMPIADOS)
    pend = [e for e in cola if e["id"] not in hechos]
    if LIMITE:
        pend = pend[:LIMITE]
        print(f"   (--limite {LIMITE}: sólo los {len(pend)} primeros)")
    print(f"\n🧼 Fase 1 · limpiar — {len(pend)} pendientes de {len(cola)}"
          f"   (ya hechos: {len(hechos)})")
    print(f"   Modo: {'SIMULACRO (no se escribe nada)' if DRY_RUN else 'REAL'}\n")

    ok_n = fail_n = 0
    for i, e in enumerate(pend, 1):
        print(f"[{i}/{len(pend)}] ID {e['id']}  ({e['uploader']}, seeds={e['seeders']})",
              flush=True)
        try:
            ok, msg = limpiar_uno(session, e)
        except Exception as ex:
            ok, msg = False, f"excepción: {ex}"

        if ok:
            ok_n += 1
            print(f"    ✨ {msg}", flush=True)
            if not DRY_RUN:
                _marcar(LIMPIADOS, e["id"])
        else:
            fail_n += 1
            print(f"    ❌ {msg}", flush=True)
            _anotar_manual(e, f"limpieza: {msg}"[:120])
            if "sesión caducada" in msg:
                print("\n🛑 Sesión caducada. Paro; al relanzar continúa por donde iba.")
                break

        if i < len(pend):
            time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))

    print(f"\n✅ Limpiados: {ok_n}   ❌ Fallos: {fail_n}")
    if not DRY_RUN:
        print(f"   Reanudable : {LIMPIADOS}")
    if fail_n:
        print(f"   Para revisar a mano: {MANUAL}")
    return ok_n, fail_n


# ==========================================
# 🎬 MAIN
# ==========================================
def main():
    global SITE_BASE

    rl = R._cargar_rawloadrr()
    SITE_BASE = R._resolver_site_base(rl)
    if not SITE_BASE:
        print("❌ No hay URL de tracker configurada.")
        return 1
    if not R.TRACKER_API_KEY:
        print("❌ Falta la API key del tracker: el barrido la necesita.")
        return 1

    print(f"🌐 Tracker : {SITE_BASE}  [{_SUF}]")
    print(f"☠️  Muertos : {', '.join(DEAD_HOSTS)}")
    print(f"⚙️  Modo    : {'SIMULACRO' if DRY_RUN else 'REAL — se editará el tracker'}")

    session = R._sesion()
    ok, err = R.comprobar_sesion(session, SITE_BASE)
    if not ok:
        print(f"❌ {err}")
        return 1
    print("🔓 Sesión válida.")

    # La cola se reutiliza si ya existe: rebarrer después de limpiar daría cero,
    # porque limpiar destruye justo el criterio de búsqueda.
    guardada = R._cargar_json(COLA)
    if guardada.get("entradas"):
        cola = guardada["entradas"]
        print(f"\n📋 Cola existente de {guardada.get('creada', '?')}: "
              f"{len(cola)} entradas (no se rebarre).")
    else:
        cola, total = barrer(session)
        if not cola:
            print("✨ Nada con enlaces muertos. No hay trabajo.")
            return 0
        guardar_cola(cola, total)

    sin_seeds = [e for e in cola if not int(e.get("seeders") or 0)]
    if sin_seeds:
        print(f"\n⚠️  {len(sin_seeds)} sin seeds: se limpian igual, pero no se podrán "
              f"reponer capturas. Van a {os.path.basename(MANUAL)}.")
        for e in sin_seeds:
            _anotar_manual(e, "sin seeds: no se podrán regenerar capturas")

    if "--barrer" in _ARGS:
        print("\n(--barrer: sólo se ha construido la cola, no se ha tocado nada)")
        return 0

    fase_limpiar(session, cola)
    return 0


if __name__ == "__main__":
    sys.exit(main())
