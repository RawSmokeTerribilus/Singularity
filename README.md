# 🌌 Singularity Core — RaW_Suite
### The Definitive P2P Orchestrator: Zero Loss, Maximum Resiliencia.

[![Docker Support](https://img.shields.io/badge/Docker-Supported-blue.svg?logo=docker&logoColor=white)](https://www.docker.com/)
[![License: GPL-3.0](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://opensource.org/licenses/GPL-3.0)
[![Spanglish Power](https://img.shields.io/badge/Spanglish-P2P_Power-orange.svg)]()

**Singularity Core** (RaW_Suite) no es solo un script de subida. Es un ecosistema completo diseñado para la Spanish-speaking scene (PARABELLUM/EMUWAREZ/MILNUEVE y otros muchos trackers basados en UNIT3D) que asume que el entorno es hostil. Archivos corruptos, ISOs mal estructuradas, trackers caídos o falta de espacio: **Singularity lo aguanta todo.**

---

## 🤝 Acknowledgments (Los Gigantes)
Este proyecto no sería nada sin el trabajo de aquellos que mantienen viva la llama del P2P y la preservación digital. **Respect.**

- **ldu (Uploadrr)**: La base lógica de la automatización de trackers UNIT3D. Sin su visión, estaríamos subiendo a mano.
- **MakeMKV**: Por permitirnos rescatar el contenido físico de los discos ópticos con precisión quirúrgica.
- **MKVToolNix**: El estándar de oro para la manipulación de contenedores Matroska.
- **FFmpeg**: La navaja suiza que hace posible cualquier rescate multimedia.
- **The TOR Project**: Por darnos la capa de anonimato necesaria para operar de forma segura.

---

## 📖 Documentación Oficial (Wiki)

[![Documentation](https://img.shields.io/badge/Wiki-Documentation-blueviolet?style=for-the-badge&logo=github)](https://rawsmoketerribilus.github.io/Singularity/)

Para guías detalladas sobre la configuración del entorno, el funcionamiento de los módulos internos y técnicas avanzadas de inyección de metadatos, visita nuestra Wiki oficial:

### 👉 [**Acceder a la Wiki de Singularity**](https://RawSmokeTerribilus.github.io/Singularity/)

Dentro encontrarás todo el conocimiento técnico del Tanque:
* **Setup Guide:** Instalación de dependencias y despliegue del contenedor.
* **MKVerything:** Guía de análisis profundo, verificación de pistas y rescate.
* **Mass Editor:** Orquestación de edición masiva en trackers UNIT3D.
* **RawLoadrr:** Configuración de auto-upload y gestión de trackers.

---

## 🧬 Filosofía: "Zero Loss & Maximum Resiliencia"
En Singularity, **no confiamos en los metadatos**. Confiamos en la realidad del bitstream. Cada archivo se procesa en una **carrera corta en NVMe** (`FAST_WORK_DIR`) para no contaminar almacenamiento masivo.

### El Algoritmo de 4 Capas (Verifier)
Antes de que un archivo sea considerado "válido" o sustituya a un original, pasa por nuestra auditoría forense:
1.  **Capa 1: Estructura (mkvmerge)** — Validamos que el contenedor Matroska sea íntegro y no esté truncado.
2.  **Capa 2: Stream Integrity (ffprobe)** — Comprobamos que todos los streams (video, audio, subs) sean legibles y tengan metadatos sensatos.
3.  **Capa 3: Bitstream Scan (ffmpeg -f null)** — La prueba de fuego. Decodificamos el archivo completo buscando errores. Si FFmpeg falla, sabemos exactamente dónde y por qué.
4.  **Capa 4: Coherencia de Ratio** — Comparamos duración y tamaño frente al original. Si cambió demasiado (>3x o <0.3x), marcamos para revisión.

### Reemplazo Atómico (Safety First)
- Proceso en `TEMP_RESCUE`, validación en 4 capas, luego `os.replace()` atómico al original
- Si la validación falla, el temp se borra y se reintentan niveles posteriores
- **Original jamás es tocado** hasta que el nuevo archivo es 100% validado

---

## ⚡ Pipeline: Singularity Mode
El modo "Dios" que conecta tu biblioteca local con el mundo exterior en un flujo continuo:

1.  **MKVerything (Normalización)**: ISOs y archivos legacy (.avi, .mp4) se convierten en MKVs verificados.
2.  **Triage MKV (Inteligencia)**: El sistema clasifica tu biblioteca por codec, detectando qué está listo para el mundo (HEVC) y qué necesita atención (H264).
3.  **RawLoadrr (Distribución)**: Inyección masiva en trackers UNIT3D con metadatos perfectos (TMDb/IMDb integration).
4.  **UNIT3D Orchestrator (Curación)**: Mantenimiento post-subida: banners, descripciones y resurrección de imágenes.

---

## 🔐 Seguridad y Anonimato (TOR Inside)
Diseñado para la privacidad desde el primer bit:
- **Túnel SOCKS5 Nativo**: RawLoadrr detecta si tienes TOR activo (`127.0.0.1:9050`) y enruta automáticamente las peticiones de API y Announce.
- **Fingerprint Protection**: Rotación de User-Agents y cabeceras para imitar navegación humana.
- **Local Database**: Tus secretos se quedan en tu `.env` o en archivos cifrados localmente.

---

## 🛠️ Instalación y Configuración

### 🐳 Vía Docker (Recomendado)

#### Linux / macOS
Descargar `final-user-install.sh`, `makefile` y `docker-compose.yml`.
Guárdalos en el directorio de tu elección y ejecuta:

```bash
make install
make up
make attach
```
Ejecuta:
```bash
singularity
```
Para acceder al menú interactivo.

#### Windows
1. Descarga los archivos `install-windows.bat`, `setup-windows.ps1` y `docker-compose.yml`.
2. Haz **doble clic** en `install-windows.bat`. Esto creará la estructura de carpetas y los archivos de configuración iniciales.
3. Edita tus credenciales en la carpeta `config/`.
4. Haz **doble clic** en `up.bat` para iniciar los contenedores.
5. Haz **doble clic** en `singularity.bat` para acceder al menú interactivo.

El Dashboard estará disponible en el puerto `8002`.

### 🐍 Manual (Linux/macOS)
1. **Clonar y Deps**:
   ```bash
   git clone https://github.com/tu-usuario/RaW_Suite.git
   cd RaW_Suite
   pip install -r requirements.txt
   ```
2. **Dependencias Externas**:
   Asegúrate de tener instalados: `ffmpeg`, `mkvtoolnix`, `mediainfo` y `makemkv-bin`.
3. **Secrets**:
   ```bash
   cp .env.example .env
   # Edita tus APIs de TMDb, trackers, etc.
   ```

---

## 📊 Dashboard (Single Source of Truth)
Monitoriza todo tu imperio P2P en tiempo real. El Dashboard consume un JSON asíncrono (`current_status.json`) que permite ver el estado de la CPU, hilos de subida y errores de validación sin latencia.

---

## ⚠️ Uso Responsable
*Power to the People.* Esta herramienta es para preservación y compartición ética. No la uses para spam masivo o contenido basura. Mantén los estándares de calidad de tu comunidad.

**Spanglish P2P Power. Made by the scene, for the scene.**

---

## 🔄 Integración con el ecosistema -arr
**Singularity Core** no es una isla; es el centinela de tu biblioteca. Está diseñado para trabajar codo con codo con el **arr stack** (Radarr, Sonarr, Tdarr):

- **Pre-Importación**: Diagnostica la salud de tus descargas antes de que Radarr/Sonarr las importen a tu biblioteca final. Evita meter archivos corruptos, mal etiquetados o con spam en tu colección final.
- **Rescate de Legacy Codecs**: Tdarr es excelente para transcodificar, pero a menudo falla o rechaza archivos en contenedores muy antiguos (.avi, .divx, .mp4 legacy) o con errores de cabecera que impiden el análisis. **MKVerything** normaliza estos archivos a MKV H.264/HEVC verificados que Tdarr puede entonces procesar sin fricciones.
- **Cierre del Círculo (Zero Loss)**: Dado que **RawLoadrr** solo procesa contenedores modernos y codecs eficientes, pasar tu contenido por el pipeline de MKVerything primero garantiza que *todo* lo que tengas sea apto para subida automática, sin importar cuán antiguo fuera el origen.
- **Diagnóstico Tdarr**: Ayuda a identificar por qué ciertos archivos fallan en los nodos de Tdarr antes de intentar procesarlos masivamente.

---

## 🚀 Últimos Cambios (v1.6.0 — "RawrRR! This is a Major Update!")

### 🔨 Forja de VapourSynth: Aceleración de Hardware + Rescate de Contenedores Rotos
**Nueva capacidad: Nivel 3 (VapourSynth + L-SMASH + HW)**
- Compiladas desde código fuente: **zimg**, **VapourSynth R73**, **L-SMASH**, **L-SMASH-Works** (plugin compilado)
- El plugin L-SMASH permite "cateterizar" archivos con contenedores extremadamente dañados, leyendo streams directamente a bajo nivel
- Resultado: Ficheros que `ffmpeg` rechazaría completamente ahora se rescatan con la máxima calidad
- **Dockerfile completamente reconstruido** incluyendo drivers VA-API (AMD RADV, Intel non-free)

### 🖥️ HardwareAgent: Detección Automática de GPU
- Detección inteligente: NVIDIA (h264_nvenc) → AMD (h264_vaapi) → Intel (h264_qsv) → CPU (libx264) con fallback automático
- Validación en tiempo de ejecución: Si el driver VA-API falla, fallback transparente a CPU sin errores
- Argumento exacto por plataforma: `-preset p4 -tune hq` para NVIDIA, `-vaapi_device /dev/dri/renderD128` para AMD

### 🪜 La Escalera de Resiliencia: 4 Niveles de Rescate
**Nueva arquitectura UniversalRescuer:**
1. **Nivel 3**: VapourSynth + L-SMASH + GPU (el cirujano endovascular)
2. **Nivel 2**: Remux Médico con `aresample=async=1` (para audio desincronizado)
3. **Nivel 1**: Re-Encode Bruto + Fallback CPU automático (si "Could not write header" detectado)
4. **Nivel 0**: Salvaguarda (`REQUIRES_MANUAL_REVIEW` si todo falla)

### ⚡ Mass Transcode (Herramienta Oculta)
- Batch processing de 50+ archivos sin intervención manual
- 2 intentos automáticos: AMD VA-API → CPU libx264
- Fallback transparente si la cabecera está corrompida
- Ruta: `/app/logs/rutas_host.txt` → `python3 mass_transcode.py`

### 📁 FAST_WORK_DIR: Procesamiento en NVMe
- Todos los temporales ahora van a `/app/RawLoadrr/tmp/TEMP_RESCUE` (rápido, SSD/NVMe)
- Reduce I/O de disco masivo (almacenamiento externo queda libre para destino)
- Patrón **Write-Validate-Replace**: Atomicidad garantizada mediante `os.replace()` + 4-capa Verifier

### 📚 Documentación Completa (9 Documentos Técnicos)
- Nueva wiki en `docs (updating)/` con 2,164 líneas de documentación sincronizada
- Guías para troubleshooting, mass_transcode, arquitectura HW, garantías de atomicidad
- Todas las rutas y comandos validados contra código fuente

### 🔐 Patología Multimedia: 6 Tipos de "Pudrición" Documentados
- Corrupción de Cabecera → Nivel 3/2
- Desincronización Audio → Nivel 2
- Subtítulos Dañados → SRT conversion automática
- Aspect Ratio Roto (WinX) → Fix automático con `-metadata:s:v:0 sar=1/1`
- Stream Extra Corrupto → `-ignore_unknown -map_metadata -1`
- Interleave Error → `-fflags +genpts`

---

## 📝 TODO / Próximos Pasos
- [x] **VapourSynth Forge**: Compilación desde fuente de VapourSynth R73 + L-SMASH-Works.
- [x] **Hardware Acceleration**: Detección automática de GPU (NVIDIA, AMD, Intel) con fallback a CPU.
- [x] **Escalera de Resiliencia (4 Niveles)**: Nivel 3 (VapourSynth), Nivel 2 (Remux), Nivel 1 (Re-Encode + Fallback), Nivel 0 (Salvaguarda).
- [x] **FAST_WORK_DIR**: Procesamiento en NVMe con atomicidad garantizada.
- [x] **Mass Transcode**: Herramienta oculta para batch processing sin intervención.
- [x] **Documentación Técnica Completa**: 9 documentos (2,164 líneas) sincronizados con código.
- [ ] **MOZ_X11_EGL Validation**: ¿Necesaria en tu setup específico? (PENDING_RECON)
- [ ] **Cross-Filesystem Atomicidad**: Implementar `shutil.move + fsync` si TEMP_RESCUE y destino en FS diferentes.
- [ ] **Mass Transcode Paralelismo**: Multiprocessing (4 procesos) con VA-API compartida.
- [ ] **Reporte de Fallidos**: Guardar CSV de archivos irrecuperables.
- [ ] **Heurística de Main Feature**: En `extract.py`, mejorar la selección del título principal cruzando tamaño y duración.
- [ ] **Sincronización Chaos-Maker / Verifier**: Ajustar algoritmos para detectar sabotaje incluso en archivos pequeños.
- [ ] **Modo 'Fast-Pass' en God Mode**: Flag para saltar health check profundo cuando confianza en origen es absoluta.
- [ ] **Editor de Torrents General**: Menú interactivo para pedir URL y cookie en lugar de variables hardcodeadas.
- [ ] **Remover Privileged Mode**: Ajustar permisos docker a lo estrictamente necesario tras testing.
- [ ] **FIX Trackers Creation**: URL integrada en nuevo .py de tracker debería auto-detectar, no hardcodear Milnueve.
- [ ] **Improve Trackers Edition**: Aplicar lógica de cambio de API, base URL y announce automáticamente.