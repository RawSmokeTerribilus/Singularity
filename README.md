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
En Singularity, **no confiamos en los metadatos**. Confiamos en la realidad del bitstream.

### El Algoritmo de 4 Capas (Verifier)
Antes de que un archivo sea considerado "válido" o sustituya a un original, pasa por nuestra auditoría forense:
1.  **Capa 1: Estructura (mkvmerge)** — Verificamos que el contenedor Matroska sea válido y no esté truncado.
2.  **Capa 2: Stream Integrity (ffprobe)** — Comprobamos que todos los streams (video, audio, subs) sean legibles y tengan metadatos coherentes.
3.  **Capa 3: Bitstream Scan (ffmpeg -f null)** — La prueba de fuego. Decodificamos el archivo completo en busca de errores de bitstream. Si FFmpeg no puede leerlo, el archivo no existe para nosotros.
4.  **Capa 4: Auditoría de Ratio** — Comparamos duración y tamaño frente al original para asegurar que no ha habido una pérdida de calidad no deseada.

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

## 🚀 Últimos Cambios (v1.4.0)

- **Fix Crítico en RawLoadrr**: Corregido un `AttributeError` en `src/prep.py` que causaba que muchos lanzamientos (especialmente Anime) fallaran al detectar episodios si el valor era devuelto como entero por `guessit`.
- **Mejora en Parsing Español**: Optimización de la detección de palabras clave españolas (`Cap`, `Cap.`, `Temp`) para una mejor integración con bibliotecas no estandarizadas.
- **Forensic Stability**: Mejorada la resiliencia de MKVerything ante archivos con duraciones inconsistentes detectadas por FFmpeg.
- **Arr Integration Docs**: Actualización de la documentación para reflejar el papel de la suite en el stack automatizado.

---

## 📝 TODO / Próximos Pasos
- [x] **Fix Episode Detection**: Corregir crash en el parsing de episodios cuando `guessit` devuelve enteros.
- [ ] **Refactorización de Scripts de Mantenimiento**: Migrar los valores hardcodeados (cookies, URLs) de los scripts en `extras/MASS-EDITION-UNIT3D/` a un archivo de configuración centralizado (`singularity_config.py`).
- [ ] **Mejora de la Gestión de Secretos**: Implementar soporte nativo para variables de entorno en todas las herramientas de la suite.
- [ ] **Generalizar frases de trolleo**: Dada la duración de los pipeline, llevar el trolleo a cada esquina para amenizar.
- [ ] **Sync chaosmaker con auditoría**: Ajustar los sectores e intensidad del chaosmaker para que sea más eficiente, actualmente algunas inyecciones de ruido en archivos pequeños no son detectables por la auditoría.
- [ ] **Hacer editor de torrents general**: Actualmente la url se pasa de variable desde el pipeline completo, la cookie también. sin embargo debería de pedirla en el menú interactivo.
- [ ] **Quitar privileged mode**: El contenedor actualmente se ejecuta como root, por motivos de infraestructura. Ajsutar los permisos a los elementos extrictamente necesarios tras acabar la fase de test.
- [ ] **FIX trackers creation**: Actualmente la url que se integra en el archivo de tracker nuevo .py de src se crea con la url de milnueve. esto es una putada que obliga a modificarlo a mano desde el contendor.
- [ ] **Improve trackers edition**: El huevón no aplica la lógica de cambio de api, base url o announce.