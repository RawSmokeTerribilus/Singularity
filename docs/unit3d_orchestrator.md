# UNIT3D Mass-Edition Suite

> **"Restauración masiva. Inteligencia colectiva."**

La suite de **Mass-Edition** (ubicada en `extras/MASS-EDITION-UNIT3D/`) es una herramienta de administración avanzada diseñada para corregir, mejorar o restaurar cientos de torrents en trackers UNIT3D de forma automática. 

Ideal para cuando un tracker cambia su política de banners, se pierden imágenes o necesitas inyectar metadatos (IMDb/TMDb) que faltaban en el momento de la subida.

---

## 🛠️ El Workflow de 4 Pasos

El proceso se divide en cuatro scripts que deben ejecutarse en orden para garantizar la integridad de los datos.

### 🕵️ Paso 1: Scraper (`01_scraper.py`)
**Propósito:** Cosechar los IDs de todos los torrents que has subido.
- Se conecta a tu perfil de usuario en el tracker.
- Recorre todas las páginas de tus subidas.
- Genera un archivo `ids.txt` con la lista de IDs únicos encontrados.
- **Requiere:** Una `COOKIE_VALUE` válida en el `.env`.

### 🔍 Paso 2: Indexer (`02_indexer.py`)
**Propósito:** Crear un puente entre los IDs del tracker y tus archivos locales.
- Escanea tu directorio temporal (`TMP_ROOT`) donde RawLoadrr guardó los metadatos (`meta.json`) de tus subidas.
- Crea un archivo `mapeo_maestro.json` que asocia el nombre exacto del torrent en el tracker con su carpeta local.
- Este paso es crucial para que el actualizador sepa qué información inyectar en cada ID.

### 🚀 Paso 3: Mass Updater (`03_mass_updater.py`)
**Propósito:** La ejecución del cambio masivo.
- Lee `ids.txt` y para cada ID:
    1. Entra en el modo "Edit" del tracker.
    2. Identifica el torrent y busca su información local en el `mapeo_maestro.json`.
    3. Reemplaza banners viejos por el nuevo configurado (`BANNER_NUEVO`).
    4. Inyecta metadatos faltantes (IMDb, TMDb Movie/TV, TVDb).
    5. Limpia la descripción de firmas obsoletas.
- **Resiliencia:** Incluye manejo de Rate Limits (429) y errores de Cloudflare, pausando el proceso automáticamente.

### 🖼️ Paso 4: Image Resurrector (`04_image_resurrector.py`)
**Propósito:** Recuperar imágenes rotas o perdidas.
- Si tus capturas originales en Pixhost u otros servidores han caído, este script las "resucita".
- Toma las imágenes originales de tu carpeta local.
- Las sube a un nuevo host (ImgBB o PtScreens) con **fallback automático** (si uno falla, usa el otro).
- Actualiza el BBCode en el tracker con las nuevas URLs.
- Reorganiza la descripción para que el bloque de fotos quede perfectamente centrado y profesional.

---

## ⚙️ Configuración Crítica

Para que la suite funcione, debes configurar estos valores en tu `.env`:

```ini
# La URL base del tracker (ej: https://milnueve.neklair.es)
BASE_URL=https://tu-tracker.com

# Tu cookie de sesión (inspecciona el navegador -> Application -> Cookies)
COOKIE_VALUE=eyJpdiI6... (valor muy largo)

# Rango de IDs para el scraper (opcional si ya tienes ids.txt)
ID_START=1
ID_END=5000

# API Keys para resubida de imágenes
IMGBB_API=tu_key
PTSCREENS_API=tu_key
```

---

## ⚠️ Advertencias de Seguridad

*   **Human Behavior:** El sistema incluye retrasos aleatorios (jitter) entre 4.5 y 7.5 segundos para evitar ser detectado como un bot agresivo. **No reduzcas estos tiempos.**
*   **Cookie Expiration:** Si el script empieza a reportar errores 422 o redirecciones al login, tu `COOKIE_VALUE` ha caducado. Actualízala y reinicia el script (el sistema tiene checkpoints y no repetirá lo ya hecho).
*   **Rate Limits:** Si el tracker detecta demasiadas peticiones, el script pausará 30 segundos automáticamente. Déjalo trabajar, la paciencia es la clave de la restauración masiva.

**Made by the scene, for the scene. P2P Power.**
