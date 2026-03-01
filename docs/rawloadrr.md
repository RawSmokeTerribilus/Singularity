# RawLoadrr — El Motor de Inyección

> **"Subida masiva. Metadatos perfectos."**

**RawLoadrr** es el brazo de distribución de Singularity Core. Está diseñado para tomar tu biblioteca limpia (procesada por MKVerything) e inyectarla masivamente en trackers privados basados en UNIT3D con el mínimo esfuerzo manual.

---

## 🎯 ¿Para qué sirve?

*   **Prepara** los archivos para subida: extrae mediainfo, genera capturas de pantalla, busca IDs en TMDb/IMDb.
*   **Automatiza** el proceso de subida masiva a más de 50 trackers configurados.
*   **Clasifica** mediante el motor de **Triage**, permitiendo subir primero lo más eficiente (HEVC).
*   **Garantiza** la ausencia de duplicados antes de intentar cualquier subida.

---

## 🛠️ ¿Cómo usarlo?

1.  **Desde el menú Singularity:** Pulsa `2` para lanzar el Launcher de RawLoadrr (`rawncher.py`).
2.  **Operaciones comunes:**
    *   **Opción [1] Subir contenido:** Elige un tracker y una carpeta para iniciar el proceso.
    *   **Opción [3] Triage:** Escanea una biblioteca y genera listas de subida priorizadas por codec.
    *   **Opción [5] Debug:** Prueba una subida completa sin llegar a publicarla en el tracker.

---

## 📖 Referencia de Argumentos (CLI)

Si prefieres usar `upload.py` directamente, aquí tienes la artillería pesada. Basado en el motor original de Uploadrr pero vitaminado.

### 🎥 Metadatos y IDs
| Argumento | Alias | Descripción |
| :--- | :--- | :--- |
| `--tmdb` | `-tmdb` | Forzar ID de TMDb (ej: `movie/123` o `tv/456`). |
| `--imdb` | `-imdb` | Forzar ID de IMDb (tt1234567). |
| `--mal` | `-mal` | ID de MyAnimeList. |
| `--tmdb_manual` | | Sobrescribir búsqueda automática de TMDb. |
| `--season` | `-season` | Forzar número de temporada. |
| `--episode` | `-episode` | Forzar número de episodio. |
| `--year` | `-year` | Forzar año de lanzamiento. |

### 🖼️ Capturas y Multimedia
| Argumento | Alias | Descripción |
| :--- | :--- | :--- |
| `--screens` | `-s` | Número de capturas a generar (por defecto configurado en `.env`). |
| `--imghost` | `-ih` | Host de imágenes: `imgbb`, `ptpimg`, `ptscreens`, `pixhost`, `imgbox`. |
| `--skip-imagehost-upload` | `-siu` | No subir capturas (usar locales). |
| `--vapoursynth` | `-vs` | Usar VapourSynth para generar capturas (calidad pro). |
| `--ffdebug` | | Mostrar salida de FFmpeg durante las capturas. |

### 🚀 Control de Subida
| Argumento | Alias | Descripción |
| :--- | :--- | :--- |
| `--trackers` | `-tk` | Lista de trackers (separados por espacio): `EMU MILNU BHD`. |
| `--anon` | `-a` | Subida anónima. |
| `--stream` | `-st` | Optimizado para Stream (Fast Start). |
| `--personalrelease` | `-pr` | Marcar como Personal Release. |
| `--skip-dupe-check` | `-sdc` | Forzar subida aunque detecte duplicado. |
| `--unattended` | `-ua` | Modo desatendido (sin prompts). |
| `--delay` | `-delay` | Segundos de espera entre subidas en cola. |

---

## ⚙️ Funcionamiento y Resiliencia

### Detección de Duplicados
RawLoadrr realiza una consulta API al tracker antes de cada subida. Si detecta un torrent con el mismo nombre o ID de TMDb/IMDb, **omite la subida** automáticamente para evitar penalizaciones o spam en el sitio.

### Motor de Triage
El bridge `triage_mkv.py` analiza tu biblioteca y separa las carpetas en:
1.  **HEVC:** Archivos x265 nativos, ideales para subida inmediata.
2.  **H264/Legacy:** Archivos que aún requieren conversión o que son de calidad inferior.

Esto permite optimizar el ratio de subida priorizando el contenido más demandado/moderno.

---

## 🔧 Configuración y Seguridad

### Añadir nuevos Trackers
No necesitas editar código. Usa la opción **[3] Crear nuevo tracker** en Rawncher para configurar un nuevo sitio UNIT3D interactivamente. Se generará el módulo `.py` y se añadirá a la base de datos automáticamente.

### Seguridad y Privacidad
*   **Modo Anónimo:** Cada tracker puede configurarse con `anon: True` para ocultar tu nombre de usuario en la subida.
*   **Soporte Tor:** Incluye scripts para enrutar el tráfico a través de la red Tor, protegiendo tu IP real y saltando bloqueos de ISP.
*   **Limpieza de Metadatos:** Antes de subir, RawLoadrr limpia el nombre del archivo de "basura" común de la scene.

---

## 🚀 Batch Upload
Para subidas masivas, el script `auto-upload.py` utiliza las listas generadas por el Triage para procesar cientos de carpetas en secuencia, manejando reintentos y errores de forma inteligente sin detener el pipeline.
