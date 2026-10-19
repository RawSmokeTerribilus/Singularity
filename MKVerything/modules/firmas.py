"""
Firmas spam dentro de los MKV: detección y limpieza.

Un único sitio para todo MKVerything: la auditoría, el rescate, el legacy, la
extracción de ISOs y los modos God/Goddess (y con ellos Singularity) llaman
aquí. Lo que se considera firma vive en data/firmas_spam.txt (de la suite, se
refresca con `make up`) más data/firmas_spam.usuario.txt (del usuario, nunca
se toca). Se leen en cada pasada.

Qué se mira, todo desde la cabecera (sin leer el vídeo):
  - título del contenedor;
  - nombre de cada pista; una pista de subtítulos con firma en el nombre y muy
    pocos eventos es un anuncio («Ripeado y subido por…») y se quita entera;
  - etiquetas globales y de pista (las estadísticas de mkvmerge no);
  - nombre y descripción de los adjuntos (las fuentes de los ASS se quedan).
Los capítulos no se miran: en el barrido del 19-10-2026 ninguno llevaba firma.

Nunca se edita en sitio un fichero que ya existía: puede estar sembrándose y
un cambio de bytes rompe el torrent. Se escribe una copia limpia, que se queda
con el nombre original, y el original pasa a «<nombre>.con-spam» (esa
extensión no la recoge el triaje, ni RawLoadrr, ni los arr). Las rutas sucias
quedan en logs/con-spam-pendientes-<fecha>.txt para que el operador las borre.
Los ficheros recién creados por el rescate o la extracción sí se limpian en
sitio: nadie los está sembrando todavía.
"""

import json
import os
import re
import shutil
import subprocess
import time
import xml.etree.ElementTree as ET

_MKVE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(_MKVE_ROOT, "data")
LOGS_DIR = os.path.join(_MKVE_ROOT, "logs")
LISTA_SUITE = "firmas_spam.txt"
LISTA_USUARIO = "firmas_spam.usuario.txt"
EXT_SUCIO = ".con-spam"
EXT_TMP = ".limpiando"

OPCIONES_DEFECTO = {"titulo": "firma", "margen_gb": "2", "anuncio_max_eventos": "3"}

# Etiquetas que escribe el propio mkvmerge/ffmpeg: no son del ripeador.
_TAGS_TECNICOS = {"DURATION", "BPS", "NUMBER_OF_FRAMES", "NUMBER_OF_BYTES",
                  "_STATISTICS_WRITING_APP", "_STATISTICS_WRITING_DATE_UTC",
                  "_STATISTICS_TAGS", "ENCODER", "ENCODER_OPTIONS", "HANDLER_NAME",
                  "VENDOR_ID", "MAJOR_BRAND", "MINOR_VERSION", "COMPATIBLE_BRANDS"}

LINEA_COMPOSE = "- ./work_data/firmas_spam:/app/MKVerything/data"

# Adjuntos que un MKV lleva de por sí: fuentes de los subtítulos ASS y portadas.
_FUENTES = ("font/", "application/x-truetype-font", "application/vnd.ms-opentype",
            "application/font", "application/x-font")
_ADJUNTOS_NORMALES = _FUENTES + ("image/",)


# =========================================================================
# LA LISTA
# =========================================================================

class Lista:
    def __init__(self):
        self.firmas = []       # [(entrada tal cual, regex compilada)]
        self.tecnicos = []     # [regex compilada]
        self.opciones = dict(OPCIONES_DEFECTO)
        self.fuentes = []      # [(ruta, nº de entradas | None si no existe)]
        self.errores = []      # líneas que no se pudieron leer

    def firma(self, texto):
        """Devuelve el trozo con firma de `texto`, o None si está limpio."""
        if not texto:
            return None
        t = texto
        for rx in self.tecnicos:
            t = rx.sub(" ", t)
        for _entrada, rx in self.firmas:
            m = rx.search(t)
            if m:
                return m.group(0).strip() or _entrada
        return None

    def recortar(self, nombre):
        """Nombre de pista sin la firma. '' = borrar el nombre entero.

        Se parte por [corchetes], «_» y « - », se tiran los trozos con firma y
        el resultado solo vale si queda UN trozo con alguna palabra de verdad
        («AC3 5.1 Castellano [www.newpct.com][toni32]» → «AC3 5.1 Castellano»).
        Si queda más de uno es un nombre de release y se borra entero: la
        pista conserva su idioma, perder el nombre no rompe nada."""
        trozos = [t.strip(" .-|") for t in re.split(r"[\[\]]|_| - ", nombre)]
        quedan = [t for t in trozos if t and not self.firma(t)]
        if len(quedan) != 1:
            return ""
        nuevo = quedan[0]
        if not re.search(r"[^\W\d_]{3,}", nuevo) or self.firma(nuevo):
            return ""
        return nuevo

    @property
    def titulo_siempre(self):
        return self.opciones.get("titulo", "firma").strip().lower() == "siempre"

    def _num(self, clave, tipo):
        try:
            return tipo(self.opciones.get(clave, OPCIONES_DEFECTO[clave]))
        except (TypeError, ValueError):
            return tipo(OPCIONES_DEFECTO[clave])

    @property
    def margen_bytes(self):
        return int(self._num("margen_gb", float) * 1024 ** 3)

    @property
    def anuncio_max_eventos(self):
        return self._num("anuncio_max_eventos", int)


def _leer(ruta, lista):
    if not os.path.isfile(ruta):
        lista.fuentes.append((ruta, None))
        return
    seccion, n = None, 0
    with open(ruta, encoding="utf-8-sig") as f:
        for num, linea in enumerate(f, 1):
            linea = linea.strip()
            if not linea or linea.startswith("#"):
                continue
            if linea.startswith("[") and linea.endswith("]"):
                seccion = linea[1:-1].strip().lower()
                continue
            if seccion == "opciones":
                if "=" in linea:
                    k, v = linea.split("=", 1)
                    lista.opciones[k.strip().lower()] = v.split("#", 1)[0].strip()
                continue
            if seccion not in ("firmas", "tecnicos"):
                continue
            patron = linea[3:] if linea.startswith("re:") else re.escape(linea)
            try:
                rx = re.compile(patron, re.IGNORECASE)
            except re.error as e:
                lista.errores.append(f"{os.path.basename(ruta)}:{num}: «{linea}» ({e})")
                continue
            if seccion == "firmas":
                lista.firmas.append((linea, rx))
            else:
                lista.tecnicos.append(rx)
            n += 1
    lista.fuentes.append((ruta, n))


def cargar_lista(data_dir=DATA_DIR):
    """Suite + usuario, en este orden. Se llama en cada pasada: un cambio en
    el fichero del usuario vale sin reiniciar nada."""
    lista = Lista()
    _leer(os.path.join(data_dir, LISTA_SUITE), lista)
    _leer(os.path.join(data_dir, LISTA_USUARIO), lista)
    return lista


def aviso_montaje(data_dir=DATA_DIR):
    """En Docker, sin la carpeta montada, lo que edite el usuario se pierde al
    recrear el contenedor. Se dice en pantalla, con la línea que falta."""
    if os.path.exists("/.dockerenv") and not os.path.ismount(data_dir):
        return ("⚠️  La lista de firmas no está montada desde work_data: se usa la copia de la imagen y "
                "lo que añadas se perderá al recrear el contenedor.\n"
                f"   Añade a los volumes de tu docker-compose.yml:  {LINEA_COMPOSE}\n"
                "   y ejecuta  make up")
    return None


def texto_lista(lista):
    """Líneas para pantalla: qué listas se usan y cuántas cadenas tienen."""
    lineas = []
    for ruta, n in lista.fuentes:
        estado = "no existe" if n is None else f"{n} cadenas"
        lineas.append(f"   📄 {ruta}  ({estado})")
    if lista.fuentes and lista.fuentes[0][1] is None:
        # Volumen montado pero vacío: un compose nuevo con el makefile o el
        # instalador de antes de la 3.1.6, que no reparten la lista.
        lineas.append("   ❌ Falta la lista de firmas de la suite: así no se limpiará casi nada.\n"
                      "      Baja de nuevo el kit (makefile y final-user-install.sh) y ejecuta  make up")
    for e in lista.errores:
        lineas.append(f"   ⚠️  Línea ignorada, no es una expresión válida: {e}")
    aviso = aviso_montaje()
    if aviso:
        lineas.append(aviso)
    return "\n".join(lineas)


TEXTO_PREGUNTA = (
    "🧹 ¿Quieres que limpiemos el spam (firmas de ripeadores) de los archivos?\n"
    "   Nota: esto genera un DUPLICADO por cada archivo limpiado; revisa tu espacio en disco.\n"
    "   El limpio se queda con el nombre original y el sucio pasa a «<nombre>.con-spam»;\n"
    "   al final tendrás la lista de sucios para borrarlos.\n"
    "   Si estás sembrando estos archivos en otro sitio, contesta que NO: el limpio cambia\n"
    "   los bytes y ese torrent dejaría de verificar."
)


def preguntar(input_fn=input):
    """La pregunta única del inicio de cada flujo. Por defecto: no."""
    lista = cargar_lista()
    print(f"\n{TEXTO_PREGUNTA}\n   Listas de firmas:\n{texto_lista(lista)}")
    return input_fn("   👉 ¿Limpiar el spam? (s/N): ").strip().lower() == "s"


# =========================================================================
# DETECCIÓN
# =========================================================================

def _mkvmerge_j(ruta):
    try:
        r = subprocess.run(["mkvmerge", "-J", ruta], capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        if r.returncode in (0, 1):
            return json.loads(r.stdout)
    except (OSError, ValueError):
        pass
    return None


def _leer_tags(ruta):
    """[(TrackUID o None si es global, nombre, valor)]. Las etiquetas no vienen
    enteras en `mkvmerge -J` (el v74 de la imagen no ve las que mkvmerge
    escribe al final del fichero, que es donde van las estadísticas): se sacan
    con mkvextract, que las encuentra por el índice sin leer el vídeo."""
    try:
        r = subprocess.run(["mkvextract", ruta, "tags", "-"], capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        texto = r.stdout.lstrip("\ufeff").strip()
        raiz = ET.fromstring(texto) if texto else None
    except (OSError, ET.ParseError):
        return []
    if raiz is None:
        return []
    out = []
    for tag in raiz.iter("Tag"):
        uid = tag.findtext("Targets/TrackUID")
        for simple in tag.iter("Simple"):
            out.append((uid, (simple.findtext("Name") or "").strip(), (simple.findtext("String") or "").strip()))
    return out


def _es_sub_texto(t):
    """Los subtítulos de texto, los mismos que el rescatador conserva."""
    cid = (t.get("properties", {}).get("codec_id") or "").upper()
    return t.get("type") == "subtitles" and cid.startswith("S_TEXT/") and "WEBVTT" not in cid


def inspeccionar(ruta, lista=None):
    """Qué firmas lleva un MKV y qué habría que hacer para quitarlas.

    Devuelve {'ruta', 'sucio', 'hallazgos': [{sitio, texto, firma}], 'plan',
    'j'} o {'ruta', 'error'} si no se puede leer."""
    lista = lista or cargar_lista()
    j = _mkvmerge_j(ruta)
    if not j or not j.get("container", {}).get("recognized", True):
        return {"ruta": ruta, "error": "mkvmerge no puede leerlo"}
    plan = {"titulo": False, "pistas": {}, "quitar_subs": [], "quitar_adjuntos": [],
            "sin_global_tags": False, "sin_track_tags": False}
    hallazgos = []

    titulo = j.get("container", {}).get("properties", {}).get("title") or ""
    f = lista.firma(titulo)
    if f:
        plan["titulo"] = True
        hallazgos.append({"sitio": "título", "texto": titulo, "firma": f})
    elif titulo and lista.titulo_siempre:
        plan["titulo"] = True
        hallazgos.append({"sitio": "título", "texto": titulo, "firma": "(sin título por norma)"})

    tags = _leer_tags(ruta)
    eventos_por_uid = {uid: v for uid, n, v in tags if uid and n.upper() == "NUMBER_OF_FRAMES"}
    uid_a_id = {}
    for t in j.get("tracks", []):
        p = t.get("properties", {})
        if p.get("uid") is not None:
            uid_a_id[str(p["uid"])] = t["id"]
        nombre = p.get("track_name") or ""
        f = lista.firma(nombre)
        if not f:
            continue
        eventos = p.get("tag_number_of_frames") or eventos_por_uid.get(str(p.get("uid")))
        if (t.get("type") == "subtitles" and eventos is not None
                and str(eventos).isdigit() and int(eventos) <= lista.anuncio_max_eventos):
            plan["quitar_subs"].append(t["id"])
            hallazgos.append({"sitio": f"subtítulo-anuncio {t['id']} ({eventos} evento/s)",
                              "texto": nombre, "firma": f})
        else:
            plan["pistas"][t["id"]] = lista.recortar(nombre)
            hallazgos.append({"sitio": f"pista {t['id']} ({t.get('type')})", "texto": nombre, "firma": f})

    avisos = []
    for a in j.get("attachments", []):
        tipo = a.get("content_type") or ""
        if tipo.startswith(_FUENTES):
            continue  # sin sus fuentes, los subtítulos ASS se ven mal: nunca se quitan
        texto = f"{a.get('file_name') or ''} {a.get('description') or ''}".strip()
        f = lista.firma(texto)
        if f:
            plan["quitar_adjuntos"].append(a["id"])
            hallazgos.append({"sitio": f"adjunto {a['id']}", "texto": texto, "firma": f})
        elif not (a.get("content_type") or "").startswith(_ADJUNTOS_NORMALES):
            # Ni fuente ni portada: no es firma, pero no pinta nada en un vídeo.
            avisos.append({"sitio": f"adjunto {a['id']} ({a.get('content_type') or '?'})", "texto": texto,
                           "firma": "revisar a mano"})

    for uid, nombre, valor in tags:
        if nombre.upper() in _TAGS_TECNICOS:
            continue
        f = lista.firma(valor)
        if not f:
            continue
        if uid:
            plan["sin_track_tags"] = True
            donde = f"etiqueta {nombre} (pista {uid_a_id.get(uid, '?')})"
        else:
            plan["sin_global_tags"] = True
            donde = f"etiqueta {nombre}"
        hallazgos.append({"sitio": donde, "texto": valor, "firma": f})

    sucio = bool(hallazgos)
    # Aprovechando el viaje: si el fichero se limpia por otra cosa, el título
    # se va igualmente (la norma es MKV sin título).
    if sucio and titulo:
        plan["titulo"] = True
    return {"ruta": ruta, "sucio": sucio, "hallazgos": hallazgos, "avisos": avisos, "plan": plan, "j": j}


def describir(info, maximo=3):
    """Resumen de una línea: título «wolfmax4k.com», pista 2 (audio) «[www…]»."""
    if info.get("error"):
        return info["error"]
    trozos = [f"{h['sitio']} «{h['texto'][:50]}»" for h in info.get("hallazgos", [])[:maximo]]
    resto = len(info.get("hallazgos", [])) - maximo
    if resto > 0:
        trozos.append(f"y {resto} más")
    return " · ".join(trozos)


# =========================================================================
# LIMPIEZA
# =========================================================================

def _args(info, salida):
    """mkvmerge que reescribe el fichero sin las firmas. Vídeo, audio y
    subtítulos se copian tal cual: solo cambian los metadatos (y las pistas o
    adjuntos-anuncio, que se quedan fuera)."""
    plan = info["plan"]
    args = ["mkvmerge", "-o", salida]
    if plan["titulo"]:
        args += ["--title", ""]
    for tid, nuevo in plan["pistas"].items():
        args += ["--track-name", f"{tid}:{nuevo}"]
    if plan["quitar_subs"]:
        args += ["--subtitle-tracks", "!" + ",".join(str(i) for i in plan["quitar_subs"])]
    if plan["quitar_adjuntos"]:
        args += ["--attachments", "!" + ",".join(str(i) for i in plan["quitar_adjuntos"])]
    if plan["sin_global_tags"]:
        args.append("--no-global-tags")
    if plan["sin_track_tags"]:
        args.append("--no-track-tags")
    return args + [info["ruta"]]


def _contar(j, tipo):
    return sum(1 for t in j.get("tracks", []) if t.get("type") == tipo)


def _verificar(info, salida, lista):
    """La copia ha de ser el mismo vídeo sin las firmas: misma duración (±1 s),
    mismas pistas de vídeo y audio, los subtítulos y adjuntos de antes menos
    los quitados, y ni una firma."""
    antes = info["j"]
    despues = _mkvmerge_j(salida)
    if not despues:
        return "la copia no se puede leer"
    d0 = int(antes.get("container", {}).get("properties", {}).get("duration") or 0)
    d1 = int(despues.get("container", {}).get("properties", {}).get("duration") or 0)
    if d0 and abs(d0 - d1) > 1_000_000_000:
        return f"duración distinta ({d0 / 1e9:.1f}s → {d1 / 1e9:.1f}s)"
    for tipo in ("video", "audio"):
        if _contar(antes, tipo) != _contar(despues, tipo):
            return f"pistas de {tipo}: {_contar(antes, tipo)} → {_contar(despues, tipo)}"
    subs = _contar(antes, "subtitles") - len(info["plan"]["quitar_subs"])
    if _contar(despues, "subtitles") != subs:
        return f"subtítulos: esperaba {subs}, hay {_contar(despues, 'subtitles')}"
    adj = len(antes.get("attachments", [])) - len(info["plan"]["quitar_adjuntos"])
    if len(despues.get("attachments", [])) != adj:
        return f"adjuntos: esperaba {adj}, hay {len(despues.get('attachments', []))}"
    otra = inspeccionar(salida, lista)
    if otra.get("error") or otra.get("sucio"):
        return f"sigue con firma tras limpiar: {describir(otra)}"
    return None


def _mkvmerge(args):
    try:
        r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    except OSError as e:
        return f"mkvmerge: {e}"
    # 0 = bien, 1 = bien con avisos, 2 = error
    if r.returncode not in (0, 1):
        ultima = (r.stdout or r.stderr).strip().splitlines()[-1:]
        return f"mkvmerge: {ultima[0] if ultima else 'falló'}"
    return None


def _borrar(ruta):
    try:
        if os.path.exists(ruta):
            os.remove(ruta)
    except OSError:
        pass


def limpiar_con_copia(ruta, lista=None, info=None, registro=None):
    """Fichero que ya existía: copia limpia con el nombre original y el sucio
    a «<nombre>.con-spam». Si algo falla, el original no se toca.

    Devuelve {'estado': limpio|nada|saltado|fallo, 'motivo', 'info', 'sucio'}."""
    lista = lista or cargar_lista()
    if not ruta.lower().endswith(".mkv"):
        return {"estado": "nada", "motivo": "no es MKV", "info": None}
    info = info or inspeccionar(ruta, lista)
    if info.get("error"):
        return {"estado": "fallo", "motivo": info["error"], "info": info}
    if not info["sucio"]:
        return {"estado": "nada", "motivo": "sin firmas", "info": info}

    carpeta, base = os.path.split(ruta)
    sucio = ruta + EXT_SUCIO
    tmp = os.path.join(carpeta, "." + base + EXT_TMP)
    if os.path.exists(sucio):
        return {"estado": "saltado", "motivo": f"ya existe {os.path.basename(sucio)}: bórralo o revísalo antes",
                "info": info}
    try:
        tam = os.path.getsize(ruta)
        libre = shutil.disk_usage(carpeta).free
    except OSError as e:
        return {"estado": "fallo", "motivo": str(e), "info": info}
    if libre - tam < lista.margen_bytes:
        return {"estado": "saltado", "info": info,
                "motivo": f"sin espacio: hacen falta {tam / 1024**3:.1f} GB + {lista.margen_bytes / 1024**3:.0f} GB de margen "
                          f"y quedan {libre / 1024**3:.1f} GB libres"}

    _borrar(tmp)  # restos de una pasada que se cortó
    error = _mkvmerge(_args(info, tmp)) or _verificar(info, tmp, lista)
    if error:
        _borrar(tmp)
        return {"estado": "fallo", "motivo": error, "info": info}
    try:
        shutil.copystat(ruta, tmp)
    except OSError:
        pass
    try:
        os.replace(ruta, sucio)
    except OSError as e:
        _borrar(tmp)
        return {"estado": "fallo", "motivo": f"no se pudo renombrar el original: {e}", "info": info}
    try:
        os.replace(tmp, ruta)
    except OSError as e:
        os.replace(sucio, ruta)  # el original vuelve a su sitio
        _borrar(tmp)
        return {"estado": "fallo", "motivo": f"no se pudo colocar la copia limpia: {e}", "info": info}
    if registro:
        registro.anotar(sucio, tam)
    return {"estado": "limpio", "motivo": "", "info": info, "sucio": sucio}


def subs_con_firma_de(origen, lista=None):
    """Subtítulos de texto del ORIGINAL con firma en el nombre:
    [(posición entre los subs de texto, eventos o None, hallazgo)] y cuántos
    subs de texto tiene. El rescate borra los nombres de pista
    (-map_metadata -1) y deja el anuncio sin nada que lo delate, pero conserva
    los subs de texto en el mismo orden: la posición lo encuentra en la salida."""
    info = inspeccionar(origen, lista)
    if info.get("error"):
        return [], 0
    textos = [t for t in info["j"].get("tracks", []) if _es_sub_texto(t)]
    por_id = {}
    for h in info["hallazgos"]:
        m = re.match(r"(?:subtítulo-anuncio|pista) (\d+)", h["sitio"])
        if m:
            por_id[int(m.group(1))] = h
    out = []
    for i, t in enumerate(textos):
        if t["id"] in por_id:
            ev = None if t["id"] not in info["plan"]["quitar_subs"] else 0
            out.append((i, ev, por_id[t["id"]]))
    return out, len(textos)


def _contar_eventos(ruta, tid):
    """Eventos de una pista leyendo el fichero entero: solo para salidas
    recién creadas en disco local, nunca para la biblioteca."""
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", str(tid), "-count_packets",
                            "-show_entries", "stream=nb_read_packets", "-of", "csv=p=0", ruta],
                           capture_output=True, text=True, timeout=600)
        return int(r.stdout.strip().splitlines()[0])
    except (OSError, ValueError, IndexError, subprocess.TimeoutExpired):
        return None


def limpiar_nuevo(ruta, lista=None, origen=None):
    """Fichero recién creado por MKVerything (rescate, legacy o extracción):
    nadie lo siembra aún, así que se limpia en sitio, sin duplicado.
    `origen` = el fichero del que sale, para cazar el subtítulo-anuncio que
    el rescate ha dejado sin nombre."""
    lista = lista or cargar_lista()
    if not ruta.lower().endswith(".mkv"):
        return {"estado": "nada", "motivo": "no es MKV", "info": None}
    info = inspeccionar(ruta, lista)
    if info.get("error"):
        return {"estado": "fallo", "motivo": info["error"], "info": info}
    if origen and origen.lower().endswith(".mkv"):
        candidatos, n_textos = subs_con_firma_de(origen, lista)
        textos = [t for t in info["j"].get("tracks", []) if _es_sub_texto(t)]
        if candidatos and len(textos) == n_textos:
            for pos, ev, hallazgo in candidatos:
                tid = textos[pos]["id"]
                # ev 0 = el original ya lo sabía anuncio; None = no se sabía
                # (estadísticas perdidas, p. ej. un fichero truncado): se cuentan.
                n = 0 if ev == 0 else _contar_eventos(ruta, tid)
                if n is not None and n <= lista.anuncio_max_eventos:
                    info["plan"]["quitar_subs"].append(tid)
                    info["hallazgos"].append(dict(hallazgo, sitio=f"subtítulo-anuncio {tid} (del original)"))
                    info["sucio"] = True
        elif candidatos and textos:
            info["hallazgos"].append({"sitio": "subtítulo con firma", "texto": "no localizado en la salida",
                                      "firma": "revisar a mano"})
    if not info["sucio"]:
        return {"estado": "nada", "motivo": "sin firmas", "info": info}
    tmp = ruta + EXT_TMP
    _borrar(tmp)
    error = _mkvmerge(_args(info, tmp)) or _verificar(info, tmp, lista)
    if error:
        _borrar(tmp)
        return {"estado": "fallo", "motivo": error, "info": info}
    os.replace(tmp, ruta)
    return {"estado": "limpio", "motivo": "", "info": info}


# =========================================================================
# REGISTRO Y PANTALLA
# =========================================================================

class Registro:
    """Cuenta lo hecho y apunta los sucios en logs/con-spam-pendientes-<fecha>.txt."""

    def __init__(self, logs_dir=LOGS_DIR):
        os.makedirs(logs_dir, exist_ok=True)
        self.ruta = os.path.join(logs_dir, f"con-spam-pendientes-{time.strftime('%d-%m-%y')}.txt")
        self.cuentas = {"limpio": 0, "nada": 0, "saltado": 0, "fallo": 0}
        self.duplicado = 0

    def anotar(self, sucio, tam):
        self.duplicado += tam
        with open(self.ruta, "a", encoding="utf-8") as f:
            f.write(sucio + "\n")

    def contar(self, resultado):
        self.cuentas[resultado["estado"]] = self.cuentas.get(resultado["estado"], 0) + 1

    def resumen(self):
        c = self.cuentas
        lineas = [f"🧹 Spam — limpiados: {c['limpio']} | saltados: {c['saltado']} | fallidos: {c['fallo']}"]
        if self.duplicado:
            gb = self.duplicado / 1024 ** 3
            tam = f"{gb:.1f} GB" if gb >= 1 else f"{self.duplicado / 1024 ** 2:.0f} MB"
            lineas.append(f"   💾 Espacio duplicado: {tam} (los .con-spam)")
        if self.duplicado:
            lineas.append(f"   🗑️  Sucios para revisar y borrar: {self.ruta}")
            if os.path.exists("/.dockerenv"):
                lineas.append(f"      (en el host: work_data/logs/mkverything/{os.path.basename(self.ruta)})")
        return "\n".join(lineas)


def linea_resultado(res, ruta):
    """Una línea por fichero para la pantalla."""
    nombre = os.path.basename(ruta)
    est = res["estado"]
    if est == "limpio":
        extra = f"sucio: {os.path.basename(res['sucio'])} · " if res.get("sucio") else ""
        return f"   🧹 LIMPIO → {nombre}  ({extra}{describir(res['info'])})"
    if est == "saltado":
        return f"   ⏭️  Spam sin limpiar en {nombre}: {res['motivo']}"
    if est == "fallo":
        return f"   ❌ Limpieza fallida en {nombre}: {res['motivo']} — original intacto"
    return None


# =========================================================================
# LÍNEA DE ÓRDENES: probar la lista o mirar ficheros sueltos
# =========================================================================

def _prueba(lista, ruta_casos=os.path.join(DATA_DIR, "firmas_spam_casos.txt")):
    fallos = total = 0
    with open(ruta_casos, encoding="utf-8") as f:
        for linea in f:
            linea = linea.rstrip("\n")
            if not linea.strip() or linea.startswith("#"):
                continue
            campos = linea.split("\t")
            tipo, texto = campos[0], campos[1] if len(campos) > 1 else ""
            total += 1
            if tipo == "recorte":
                esperado = campos[2] if len(campos) > 2 else ""
                obtenido = lista.recortar(texto)
                if obtenido != esperado:
                    fallos += 1
                    print(f"❌ recorte «{texto}» → «{obtenido}» (esperaba «{esperado}»)")
            else:
                f_ = lista.firma(texto)
                if bool(f_) != (tipo == "si"):
                    fallos += 1
                    print(f"❌ {tipo}: «{texto}»" + (f"  (caza «{f_}»)" if f_ else "  (no caza nada)"))
    print(f"{'✅' if not fallos else '❌'} {total - fallos}/{total} casos")
    return fallos


if __name__ == "__main__":
    import sys
    lista = cargar_lista()
    print(texto_lista(lista))
    if "--prueba" in sys.argv[1:]:
        sys.exit(1 if _prueba(lista) else 0)
    for ruta in [a for a in sys.argv[1:] if not a.startswith("--")]:
        info = inspeccionar(ruta, lista)
        estado = "❓" if info.get("error") else ("🏷️ " if info["sucio"] else "✅")
        print(f"{estado} {ruta}\n   {describir(info, maximo=20) or 'sin firmas'}")
        for a in info.get("avisos", []):
            print(f"   ⚠️  {a['sitio']} «{a['texto']}»: {a['firma']}")
