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
Descargar final-user-install.sh, makefile y docker-compose.yml
Guárdalos en el directorio de tu elección y ejecuta:

```bash
make install
make up
make attach
singularity
```
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

## 📝 TODO / Próximos Pasos
- [ ] **Refactorización de Scripts de Mantenimiento**: Migrar los valores hardcodeados (cookies, URLs) de los scripts en `extras/MASS-EDITION-UNIT3D/` a un archivo de configuración centralizado (`singularity_config.py` o similar).
- [ ] **Mejora de la Gestión de Secretos**: Implementar soporte nativo para variables de entorno en todas las herramientas de la suite para evitar filtraciones accidentales.

