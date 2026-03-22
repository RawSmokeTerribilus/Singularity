# Herramientas Extra

> **"Sometimes you need chaos to test order."**

Además del pipeline principal, Singularity incluye una serie de utilidades satélite para tareas específicas de mantenimiento, pruebas y organización.

## 🌪️ Chaos Maker
**Ubicación**: `extras/Chaos-Maker/chaos-maker.py`

Una herramienta de **fuzzing destructivo** diseñada para validar la eficacia de los scripts de recuperación (`Verifier` y `Universal Rescuer`).

- **Funcionamiento**: Inyecta ruido aleatorio (bytes basura) en archivos MKV válidos, corrompiendo su estructura interna sin alterar necesariamente el encabezado.
- **Objetivo**: Simular "bit rot" o descargas corruptas para comprobar si `MKVerything` es capaz de detectar y reparar el daño (o al menos reportarlo).

!!! danger "PELIGRO EXTREMO"
    **Chaos Maker corrompe archivos de forma irreversible.**
    Úsalo **SOLAMENTE** en copias de seguridad o carpetas de prueba aisladas. Jamás lo ejecutes sobre tu biblioteca principal.

## ⚖️ Triage MKV
**Ubicación**: `RawLoadrr/triage_mkv.py`

El clasificador táctico. Esencial para separar el "grano de la paja" antes de subir contenido.

- **Función**: Analiza recursivamente un directorio y clasifica las carpetas en dos listas de texto:
    1. **HEVC (x265)**: Contenido moderno, eficiente y listo para archivar/subir.
    2. **H.264 / Legacy**: Contenido que podría beneficiarse de una recodificación o que pertenece a estándares anteriores.
- **Uso en Pipeline**: Estas listas son consumidas directamente por el **Auto-Upload** de RawLoadrr para priorizar qué subir.

## 🏷️ Tag Ingestor
**Ubicación**: `core/tag_ingestor.py`

El bibliotecario de metadatos.

- **Función**: Escanea los nombres de archivos y carpetas para extraer y estandarizar etiquetas de grupos de release (`-Group`, `[Group]`, etc.) y resoluciones.
- **Integración**: Alimenta la base de datos de `tags.json` usada por RawLoadrr para identificar correctamente la procedencia de los archivos durante el proceso de subida.
