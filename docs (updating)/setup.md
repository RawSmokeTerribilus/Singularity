# Configuración, Despliegue y Administración

Singularity Core es una suite profesional que requiere una configuración precisa de su entorno y secretos para operar con éxito.

---

## 🛠️ Despliegue con Docker (Recomendado)

El método recomendado para admins es el uso de Docker, que encapsula todas las dependencias sin ensuciar el sistema host.

### Opción A: Instalación Ligera (Solo 3 Archivos)
Si no quieres clonar el repositorio completo, solo necesitas descargar estos archivos:
1. `docker-compose.yml`
2. `makefile`
3. `final-user-install.sh`

```bash
# 1. Instala la estructura de carpetas y genera plantillas .env
make install

# 2. Descarga la imagen desde Docker Hub (3GB aprox)
make pull

# 3. Levanta el contenedor
make up
```

### Opción B: Repositorio Completo
Clona el repositorio y usa el Makefile para gestionar el ciclo de vida:

1.  **Lanzar el contenedor:**
    ```bash
    make pull
    make up
    ```
2.  **Entrar en la consola Singularity:**
    ```bash
    make attach
    ```

El contenedor monta el volumen local, por lo que tus cambios en el código y logs persistirán fuera de Docker.

---

## 🛠️ Instalación Manual (Bare Metal)

Si prefieres ejecutarlo fuera de Docker, asegúrate de tener instalados los siguientes binarios:
*   **FFmpeg / FFprobe:** Para análisis y transcodificación.
*   **MKVToolNix (mkvmerge):** Para manipulación de contenedores.
*   **MediaInfo:** Para extracción de metadatos.
*   **MakeMKV (makemkvcon):** Para extracción de ISOs.

```bash
# Ejemplo en RHEL/Fedora
sudo dnf install ffmpeg mkvtoolnix mediainfo makemkv-bin
```

Instala las dependencias de Python:
```bash
pip install -r requirements.txt
```

---

## ⚙️ Configuración del Archivo `.env`

El sistema orquesta sus constantes a través de `singularity_config.py`, pero los secretos deben vivir en un archivo `.env` en la raíz.

```ini
# --- CORE CONFIG ---
TMDB_API_KEY=tu_key_de_tmdb
IMGBB_API_KEY=tu_key_opcional

# --- TRACKER CONFIG ---
BASE_URL=https://tu-tracker-principal.com
COOKIE_VALUE=TU_COOKIE_SESION_PARA_MASS_EDITION

# --- MASS EDITION SETTINGS ---
ID_START=100      # ID inicial para el scraper
ID_END=5000       # ID final para el scraper
TMP_DIR_PATH=/app/tmp # Ruta donde se guardan los metadatos temporales

# --- IMAGE HOSTING ---
PTSCREENS_API=tu_key
IMGBB_API=tu_key
```

---

## 🧩 Configuración de Trackers (RawLoadrr)

Cada tracker tiene su propia configuración en `RawLoadrr/data/config.py`. El sistema soporta:

*   **API Keys**: Para subida directa mediante API de UNIT3D.
*   **Announce URLs**: Para la creación del archivo `.torrent`.
*   **Image Hosts**: Configuración por defecto de dónde subir las capturas.
*   **VapourSynth**: Actívalo si deseas capturas de máxima calidad (requiere VapourSynth instalado).

---

## 🏗️ Funcionamiento del Brain Core

`singularity_config.py` realiza una carga dinámica:
1.  Intenta importar `python-dotenv` para leer el `.env`.
2.  Inyecta las variables en el entorno global.
3.  Si faltan valores críticos durante el tiempo de ejecución, la **Opción 5 (Singularity Mode)** te los pedirá interactivamente y los guardará por ti.

---

## 🔐 Seguridad y Anonimato

*   **TOR Integration**: Si el script detecta que Tor está corriendo localmente, RawLoadrr puede enrutar las peticiones de API a través de `127.0.0.1:9050` (SOCKS5).
*   **Validación de Credenciales**: El sistema comprueba si las claves API están presentes antes de iniciar una fase del pipeline.
*   **Logs Rotativos**: Los logs se organizan por fecha para facilitar la auditoría administrativa sin saturar el almacenamiento.
