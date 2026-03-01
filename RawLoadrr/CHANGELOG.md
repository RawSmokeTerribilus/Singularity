# CHANGELOG — RawLoadrr

---

## [22-02-2026] — MILNUEVE Integration & Auto-Upload Overhaul

### MILNUEVE Tracker Integration

**Archivo**: `src/trackers/MILNU.py` (basado en EMU.py)

- Tracker integrado en `upload.py` y `data/config.py`
- URLs: upload `https://milnueve.neklair.es/api/torrents/upload`, search `.../api/torrents/filter`

**Rate Limiter asincrónico** (`src/rate_limiter.py`):
- Por-tracker, no-bloqueante (30 calls/min para MILNU, 60 para el resto)
- Estadísticas en tiempo real, configurable por tracker

**Sistema de logging dual** (`src/logger.py`):
- `logs/{tracker}_errors.log` — Solo errores (human-readable)
- `logs/{tracker}_debug.log` — Debug completo con timestamps
- Integrado en EMU.py y MILNU.py

**Archivos creados/modificados:**
```
CREADOS:
├── src/rate_limiter.py
├── src/logger.py
└── src/trackers/MILNU.py

MODIFICADOS:
├── upload.py          (+ MILNU a tracker list)
├── data/config.py     (+ MILNU config section)
└── src/trackers/EMU.py  (+ rate limiter + logger)
```

---

### Auto-Detect & Recursive Upload

**Impacto**: cambio de comportamiento core — automático por defecto, sin flags extra.

- Añadida función `build_smart_queue()` en `upload.py`:
  - Detecta automáticamente película (1 torrent) vs serie (1 torrent por temporada)
  - Incluye archivos extras (backdrops, NFO) en el torrent de película
- Upload ahora es **automático por defecto** (antes requería `--unattended`)
- Confirmaciones de nombre y upload se saltan en modo normal; sólo en `--debug` se piden
- `--delay N` espera N segundos entre uploads; `--random` mezcla el orden

**Cambios en upload.py**: ~70 líneas cambiadas/añadidas

---

### Bug Fix: API `/torrents/filter` MILNU — parámetros sin brackets

**Problema:** Los parámetros se enviaban con brackets `[]` (estándar Unit3D), pero Milnueve espera SIN brackets.

```
ANTES (Unit3D estándar): ?categories[]=1&types[]=2&resolutions[]=3
AHORA (Milnueve):        ?categories=1&types=2&resolutions=3
```

**Fix en** `src/trackers/MILNU.py` líneas 216-225:
```python
params = {
    'categories': ...,   # SIN brackets
    'types': ...,        # SIN brackets
    'resolutions': ...,  # SIN brackets
}
```
