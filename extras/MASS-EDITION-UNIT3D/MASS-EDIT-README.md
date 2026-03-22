# 🚀 UNIT3D Mass Edition Suite

Un conjunto de herramientas en Python diseñadas para la **curación y mantenimiento masivo** de tus torrents en trackers basados en **UNIT3D**.

Su misión es automatizar tareas de edición tediosas, como restaurar metadatos perdidos, inyectar banners, arreglar errores de "Info Providers" (TMDB/IMDB) y, sobre todo, **resucitar imágenes rotas** en las descripciones. Todo ello de forma automática y respetuosa con los límites del servidor.

---

## 🧬 Filosofía: El Pipeline de 4 Fases

La suite funciona como una cadena de montaje. Cada script realiza una tarea específica y prepara el terreno para el siguiente, asegurando un proceso ordenado y robusto.

1.  **`01_scraper.py` (El Cosechador):**
    *   **Misión:** Navega por tu perfil en el tracker y extrae los IDs numéricos de todos los torrents que has subido.
    *   **Resultado:** Genera un archivo `ids.txt`, que es la lista de objetivos para el resto del pipeline.

2.  **`02_indexer.py` (El Archivista):**
    *   **Misión:** Lee el `ids.txt` y, por cada ID, consulta al tracker para obtener el nombre exacto del torrent. Luego, busca en tu carpeta temporal (`TMP_ROOT`) el archivo `meta.json` que corresponde a esa subida.
    *   **Resultado:** Crea `mapeo_maestro.json`, un "mapa" que vincula cada ID de torrent con la ruta absoluta a su `meta.json` local. Este mapa es crucial para que los siguientes scripts sepan de dónde sacar la información original.

3.  **`03_mass_updater.py` (El Cirujano de Metadatos):**
    *   **Misión:** Usando el `mapeo_maestro.json`, recorre cada torrent y realiza una edición "quirúrgica". Inyecta banners, limpia firmas antiguas de la descripción y, lo más importante, fuerza la reinserción de los metadatos correctos (IMDb ID, TMDb ID, etc.) desde el `meta.json` local. Esto es ideal para arreglar torrents que se quedaron sin metadatos por un fallo del tracker.
    *   **Resultado:** Torrents en el tracker con descripciones y metadatos actualizados. Genera `completados.txt` para poder reanudar el proceso si se interrumpe.

4.  **`04_image_resurrector.py` (El Resucitador de Imágenes):**
    *   **Misión:** La fase final de embellecimiento y saneamiento. No solo arregla imágenes, **reconstruye** el post entero.
        1.  **Limpieza de Firmas:** Detecta y elimina bloques de texto obsoletos (ej. "PLEASE SEED", firmas de grupos antiguos) y banners viejos definidos en `FIRMAS_VIEJAS`.
        2.  **Purga de Hosts Muertos:** Elimina específicamente rastros de hostings caídos o problemáticos (como `pixhost.to`) mediante expresiones regulares.
        3.  **Upload Fresco:** Toma las imágenes `.jpg`/`.png` originales de tu carpeta local y las sube de nuevo a hostings fiables (ImgBB, PtScreens), generando URLs nuevas y permanentes.
        4.  **Reestructuración:** Reordena el contenido en un formato estándar: **Trailer → Galería Nueva → Banner Nuevo → Sinopsis Limpia**.
    *   **Resultado:** Una descripción visualmente perfecta, sincronizada tanto en el tracker como en tu archivo local `[MILNU]DESCRIPTION.txt`.

---

## 🚀 Flujo de Trabajo (Workflow)

Existen dos maneras de ejecutar la suite:

### A. Modo Orquestador (Recomendado vía `singularity.py`)

Esta es la forma más sencilla y segura.

1.  Lanza `singularity.py` desde la raíz del proyecto.
2.  Selecciona la opción **`[3] UNIT3D Edition (Orquestador 01-04)`**.
3.  La interfaz te guiará para configurar el **banner**, el **ID de inicio** y el **ID de fin**.
4.  Singularity se encargará de ejecutar los cuatro scripts en el orden correcto, utilizando las credenciales (`COOKIE`, `API_KEYS`) definidas en tu archivo `.env` principal. No necesitas configurar nada más.

### B. Modo Manual (Standalone)

Útil para ejecuciones aisladas o si no estás usando el lanzador principal.

1.  **Configuración:**
    *   Crea un archivo `config.py` en este mismo directorio (`extras/MASS-EDITION-UNIT3D/`).
    *   Rellena las siguientes variables:
        ```python
        # -- Credenciales del Tracker --
        BASE_URL = "https://tu-tracker.org"
        USERNAME = "TuUsuario"
        # Extrae tu cookie de sesión desde las DevTools del navegador (F12 -> Application -> Cookies)
        COOKIE_VALUE = "tu_cookie_de_sesion"

        # -- Rutas y Metadatos --
        # Ruta a la carpeta que contiene los meta.json de tus subidas
        TMP_ROOT = "/ruta/absoluta/a/tu/tmp"
        # Banner a inyectar en las descripciones
        MSG_NUEVO = "[center][img]https://i.imgur.com/banner.png[/img][/center]"

        # -- APIs para Resurrección de Imágenes --
        IMGBB_API = "tu_api_key_de_imgbb"
        PTSCREENS_API = "tu_api_key_de_ptscreens" # Opcional
        ```

2.  **Ejecución (en orden estricto):**
    *   Define el rango de IDs a procesar como variables de entorno:
        ```bash
        export ID_START=100
        export ID_END=500
        ```
    *   Ejecuta cada script uno por uno:
        ```bash
        python3 01_scraper.py
        python3 02_indexer.py
        python3 03_mass_updater.py
        python3 04_image_resurrector.py
        ```

---

## 📦 Dependencias

Las dependencias se instalan con el `requirements.txt` principal de `RaW_Suite`.

*   **`requests`**: Para realizar todas las comunicaciones HTTP (GET/PATCH) con la interfaz web del tracker.
*   **`beautifulsoup4`**: Para "parsear" el HTML de las páginas del tracker, esencial en el `scraper` para encontrar los IDs de los torrents y en el `resurrector` para analizar las descripciones.

---

## ⚠️ Disclaimer

*   **Seguridad:** Esta herramienta interactúa directamente con la interfaz web del tracker enviando peticiones `PATCH` autenticadas con tu cookie de sesión. Trata tu cookie como una contraseña.
*   **Uso Responsable:** Los scripts incluyen un retraso variable (`Jitter`) por defecto para simular comportamiento humano y evitar ser bloqueado por protecciones como Cloudflare. No modifiques estos valores a la ligera.
*   **Resiliencia:** Si el proceso se interrumpe (Ctrl+C, error de red), puedes volver a ejecutar el script `03_mass_updater.py` o `04_image_resurrector.py`. Gracias al archivo de control `completados.txt`, continuarán exactamente donde lo dejaron.
