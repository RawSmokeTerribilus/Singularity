# 🚀 UNIT3D Mass Edition Suite

Un conjunto de herramientas en Python diseñadas para la gestión y edición masiva de torrents en trackers basados en **UNIT3D**. 

Ideal para restaurar metadatos perdidos, inyectar nuevos banners/textos en descripciones antiguas, y arreglar errores de "Info Providers" (TMDB/IMDB/MAL/TVDB) de forma automática y respetuosa con los límites del servidor (Cloudflare Bypass & Rate Limiting).

## ✨ Características

* 🕵️ **Scraper Integrado**: Extrae automáticamente todos tus IDs de torrent subidos.
* 🗂️ **Indexación Local**: Vincula los nombres de los torrents en el tracker con tus archivos `meta.json` locales de subida.
* 💉 **Inyección Quirúrgica**: Restaura metadatos perdidos sorteando los estrictos errores 422 de Laravel/UNIT3D.
* 🛡️ **Safe-Mode**: Soporte para reanudación (`completados.txt`), retraso variable (Jitter) y tolerancia a errores 502/429.

## 🛠️ Requisitos

```bash
pip install requests beautifulsoup4
```
* Necesitas los archivos `meta.json` e (idealmente) el `[MILNU]DESCRIPTION.txt` generados por scripts de subida (como Uploadrr) en tu directorio temporal para restaurar las descripciones íntegras.

## ⚙️ Configuración Inicial (`config.py`)

1. Clona el repositorio y renombra los scripts si no lo has hecho (01, 02, 03).
2. Crea un archivo `config.py` en la raíz y rellena tus datos:
   - `BASE_URL` y `USERNAME`.
   - `COOKIE_VALUE`: Extrae tu cookie de sesión (`laravel_session` o el nombre del tracker) desde las DevTools (F12 -> Application -> Cookies) de tu navegador.
   - `TMP_ROOT`: Ruta absoluta a la carpeta que contiene los metadatos de tus subidas.
   - Define los textos/banners a reemplazar en las variables `MSG_VIEJO`, `MSG_NUEVO`, etc.

## 🔄 Flujo de Trabajo (Workflow)

Ejecuta los scripts en este orden estricto:

### Paso 1: Cosechar los IDs
```bash
python3 01_scraper.py
```
*Visita tu perfil en el tracker y guarda todos los IDs de tus torrents en un archivo `ids.txt`.*

### Paso 2: Generar el Índice Local
```bash
python3 02_indexer.py
```
*Escanea tu `TMP_ROOT` y crea `mapeo_maestro.json`, vinculando el Título exacto del Tracker con su ruta local absoluta.*

### Paso 3: Lanzar el Inyector Maestro
```bash
python3 03_mass_updater.py
```
*El bot comenzará a editar los torrents uno por uno. Añadirá los banners, reescribirá la descripción limpiando firmas antiguas y forzará los metadatos correctos desde el `meta.json`. Si se interrumpe (Ctrl+C o error de red), puedes volver a ejecutarlo y continuará exactamente donde lo dejó gracias al archivo de control `completados.txt`.*

## ⚠️ Disclaimer
Esta herramienta interactúa directamente con la API de edición de la interfaz web del tracker enviando peticiones `PATCH`. Úsala de forma responsable. El rate-limit (Jitter) está configurado por defecto para simular comportamiento humano y evitar baneos por parte de Cloudflare.
