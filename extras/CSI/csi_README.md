# 🕵️ CSI: Check, Search, Identify
### El Detective Forense para tu Biblioteca Multimedia

**CSI** no es un simple escáner de archivos. Es un motor de diagnóstico forense diseñado para responder a las preguntas críticas de cualquier coleccionista digital:

*   ¿Qué contenido de mi biblioteca **no he subido** todavía al tracker?
*   De lo que he subido, ¿qué archivos **no estoy seedeando**?
*   ¿Tengo **diferentes versiones** (Remux, x265, 1080p, etc.) de una misma película ya subida?
*   ¿Qué parte de mi colección está en codecs modernos (HEVC) y cuál necesita una actualización (H264/Legacy)?

CSI triangula la información entre tu **disco local**, tu **cliente qBittorrent** y el **tracker** para darte una visión 360º del estado real de tu colección.

---

## 🧬 Filosofía: "No Confíes, Verifica"

La piedra angular de CSI es su **Máquina de Estados** y el **Identificador Compuesto Único (ICU)**. No se fía de simples coincidencias de nombres.

### La Máquina de Estados de 5 Niveles
Cada archivo o temporada de tu biblioteca se clasifica en uno de estos cinco estados, que determinan la acción a seguir:

1.  `ESTADO_OK` (Verde): **Todo en orden.** El contenido está en el tracker y se está seedeando activamente en tu cliente. No requiere acción.
2.  `ESTADO_DUPE_POTENCIAL` (Amarillo): **Misma película, diferente versión.** Ya existe una versión de esta película en el tracker (ej. un Remux), pero la que tienes en local es diferente (ej. un x265). CSI te avisa para que decidas si quieres subir esta nueva versión.
3.  `ESTADO_FALTA_CLIENTE` (Naranja): **En el tracker, pero no en qBittorrent.** Subiste este torrent en el pasado, pero por alguna razón ya no está en tu cliente. CSI te lo notifica para que puedas volver a descargarlo y ponerlo en seed.
4.  `ESTADO_NO_SUBIDO` (Rojo): **Candidato a subida.** Este contenido no se ha encontrado en el tracker. Es el principal objetivo de CSI, generando listas limpias para `RawLoadrr`.
5.  `ESTADO_INCIDENCIA` (Gris): **Error de sonda.** Hubo un problema de conexión con el tracker o la API. CSI no puede asegurar el estado, por lo que lo marca para una revisión posterior, evitando falsos negativos.

### ICU (Identificador Compuesto Único)
Para evitar los falsos positivos de comparar únicamente por el ID de TMDB, CSI utiliza un "fingerprint" o huella digital para cada torrent.

**Formato:** `TMDB_ID|RESOLUTION|CODEC|GROUP`
**Ejemplo:** `11|1080P|REMUX|P2P`

Esto permite a CSI distinguir con precisión entre `Star.Wars.1977.1080p.BluRay.REMUX-GRP1` y `Star.Wars.1977.2160p.WEB-DL.x265-GRP2`, aunque ambas compartan el mismo TMDB ID.

---

## 🚀 Características Principales

*   **Motor de Triangulación Híbrido:** Utiliza la API de UNIT3D como fuente primaria, pero puede recurrir a un scraper web (usando tu cookie de sesión) si la API no está disponible o no está configurada. Cruza esta información con tu cliente qBittorrent para una verificación total.
*   **Índice Persistente (`tracker_index.json`):** CSI tiene memoria. Guarda un caché del estado del tracker en `work_data/reports/csi_reports/tracker_index.json`. Los escaneos posteriores son casi instantáneos, a menos que decidas reconstruir el índice desde cero.
*   **Reportes de Diagnóstico Detallados:** Genera múltiples archivos `.txt` en `work_data/reports/csi_reports/` para cada tipo de hallazgo, listos para ser consumidos por otros scripts o para tu revisión manual.
*   **Integración con Sonarr y Radarr:** Utiliza las APIs de Sonarr/Radarr para obtener metadatos fiables (TMDB ID, TVDB ID) directamente desde la ruta de tus archivos, asegurando una identificación precisa.
*   **Detección de Codec Multi-Nivel:** Clasifica el contenido no subido en listas separadas para `HEVC` y `H264/Legacy`, permitiéndote priorizar la subida de material moderno y eficiente.

---

## 🛠️ Modos de Investigación

CSI ofrece dos enfoques principales para analizar tu biblioteca:

1.  **Tracker Investigation (Opción 1):** El modo más completo.
    *   **Sub-modo 'a' (Your Uploads):** Compara tu biblioteca contra el índice cacheado o lo construye desde cero (scrapeando solo tus subidas). Es el modo más rápido y recomendado para el uso diario.
    *   **Sub-modo 'b' (Global Search):** Lento pero exhaustivo. Realiza una consulta a la API/scraper por **cada** ítem de tu biblioteca. Ideal para una primera auditoría completa o si sospechas que el índice está desactualizado.

2.  **Local Investigation (Opción 2):** No se conecta al tracker. Compara tu biblioteca **únicamente** contra los torrents activos en tu cliente qBittorrent. Es perfecto para encontrar contenido que tienes en disco pero que no estás seedeando.

---

## ⚙️ Configuración

CSI está diseñado para una integración "plug-and-play" con `RaW_Suite`. Hereda su configuración del archivo `.env` principal.

Las variables de entorno más importantes son:

*   `CSI_LIBRARY_PATH`: **(Obligatoria)** La ruta a la carpeta raíz de tu biblioteca multimedia que quieres escanear.
*   `TRACKER_DEFAULT`: Abreviatura del tracker a investigar (ej. `MILNU`).
*   `TRACKER_BASE_URL`: URL base del tracker (ej. `https://mitracker.org`).
*   `TRACKER_API_KEY`: Tu token de la API de UNIT3D.
*   `TRACKER_COOKIE_VALUE`: Tu cookie de sesión del tracker (necesaria para el scraper si la API falla).
*   `TRACKER_USERNAME`: Tu nombre de usuario en el tracker.
*   `QBIT_URL`, `QBIT_USER`, `QBIT_PASS`: Credenciales de tu cliente qBittorrent.
*   `SONARR_URL`, `RADARR_URL` (y sus API keys): Para la obtención de metadatos.

Puedes ajustar estos valores a través del menú **Settings (3)** dentro de CSI.

---

## 🔗 Integración en el Ecosistema RaW_Suite

CSI es el cerebro de diagnóstico que alimenta al motor de subidas `RawLoadrr`. El flujo de trabajo recomendado es:

1.  **Lanzar CSI:** Desde el menú principal de `singularity.py`, selecciona `Extras (4)` y luego `CSI (4.5)`.
2.  **Ejecutar una Investigación:** Elige el modo `Tracker Investigation (1)`. CSI analizará tu biblioteca y generará los reportes.
3.  **Inyección Directa (Feed Singularity):** Al finalizar el escaneo, si CSI detecta candidatos para subir, te mostrará las listas generadas y te preguntará: `Feed Singularity for upload?`.
    *   Si respondes **Sí (y)**, podrás seleccionar el número del reporte (ej. `1` para HEVC Movies). CSI lanzará automáticamente `auto-upload.py` con esa lista y la configuración de tu tracker, sin necesidad de copiar rutas manualmente.
4.  **Método Manual (Alternativo):** Si prefieres no usar la automatización, copia la ruta del reporte generado que se muestra en pantalla (ej. `.../csi_reports/...txt`), ve al menú de `RawLoadrr (2)` y usa la opción de subir desde lista existente.

De esta forma, te aseguras de que `RawLoadrr` solo intente subir contenido que ha sido verificado previamente por CSI como "no subido".

---

## 📦 Dependencias

### Python (Librerías del Core)
Estas librerías son esenciales para el funcionamiento lógico de CSI:

*   **`requests`**: El motor de comunicaciones. Se usa para consultar la API de UNIT3D, conectar con Sonarr/Radarr para obtener IDs y realizar scraping web (con cookies) cuando la API falla.
*   **`beautifulsoup4`**: El "traductor" de HTML. Necesario en el modo "Scraper" (fallback) para leer las tablas de torrents del tracker y extraer IDs/nombres cuando la API no está disponible.
*   **`qbittorrent-api`**: El puente con tu cliente. Permite a CSI obtener los hash y rutas de tus torrents activos para verificar qué estás seedeando realmente (Estado OK vs Falta Cliente).
*   **`python-dotenv`**: Gestión de seguridad. Carga tus claves de API y configuración sensible desde el archivo `.env` sin exponerlas en el código.
*   **`rich`**: La interfaz visual. Genera los paneles, tablas, colores y barras de progreso que hacen la herramienta legible en la terminal.

### Herramientas del Sistema (Externas)
*   **`mediainfo`**: **Crítica.** CSI invoca esta herramienta para analizar cada archivo de vídeo local.
    *   *Función:* Extrae la resolución exacta (para el ICU) y el codec (HEVC vs H264).
    *   *Uso:* Sin ella, CSI no puede generar reportes separados por codec ni detectar diferencias de resolución (Dupe Potencial).

### Integraciones Opcionales (Recomendadas)
*   **Sonarr & Radarr**: **Identificación Precisa.**
    *   *Función:* Traducen tus nombres de carpeta locales a IDs universales (TMDB/TVDB).
    *   *Uso:* Permite a CSI buscar en el tracker por ID exacto en lugar de por nombre, evitando falsos positivos y encontrando coincidencias aunque el nombre del archivo sea diferente.