# 🌌 Singularity Core — RaW_Suite
### Zero Loss, Maximum Resiliencia.

[![Docker Support](https://img.shields.io/badge/Docker-Supported-blue.svg?logo=docker&logoColor=white)](https://www.docker.com/)
[![License: GPL-3.0](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://opensource.org/licenses/GPL-3.0)

Singularity Core no es “RawLoadrr con una interfaz web”. Es el stack completo: normalización, verificación, subida, edición masiva y mantenimiento de trackers UNIT3D.

---

## 📖 Wiki oficial

[![Wiki](https://img.shields.io/badge/Wiki-Singularity-blueviolet?style=for-the-badge)](https://rawsmoke.codeberg.page/Singularity/)

Puertas rápidas:
- [![Setup](https://img.shields.io/badge/Setup-Despliegue-1f6feb?style=flat-square)](https://rawsmoke.codeberg.page/Singularity/setup/)
- [![Índice](https://img.shields.io/badge/Docs-Índice-1f6feb?style=flat-square)](https://rawsmoke.codeberg.page/Singularity/)
- [![Notas técnicas](https://img.shields.io/badge/Docs-Notas_técnicas-1f6feb?style=flat-square)](https://rawsmoke.codeberg.page/Singularity/technical_notes/)
- [![Mass Edition](https://img.shields.io/badge/UNIT3D-Mass_Edition-1f6feb?style=flat-square)](https://rawsmoke.codeberg.page/Singularity/unit3d_mass_edition/)
- [![RawLoadrr Wiki](https://img.shields.io/badge/RawLoadrr-Wiki-1f6feb?style=flat-square)](https://rawsmoke.codeberg.page/Singularity/rawloadrr_wiki/Home/)

---

## 🚀 Instalación rápida (la de siempre)

Si solo quieres arrancar la suite, basta con estos archivos:
- `docker-compose.yml`
- `makefile`
- `final-user-install.sh`

Y luego:

```bash
make install
make up
make attach
singularity
```

Ése sigue siendo el flujo principal.

Qué hace `make install`:
- crea `./config/`
- crea `./work_data/`
- instala `singularity` y `singularity-shell`
- genera `.env`, `config.py`, `singularity_config.py` y `mass_config.py`
- deja `NOBS` preformado
- conserva `config.py` multi-tracker para tirar contra cualquier UNIT3D serio

No hace falta bajar el repo completo para usar el modo ligero.
No hace falta reconstruir la imagen.
Solo la imagen publicada + esos 3 archivos.

---

## 🧩 Config shipping-ready

El instalador deja preparada una base funcional con:
- `TRACKER_BASE_URL=https://nobs.rawsmoke.net`
- `TRACKER_ABBREV=NOBS`
- `TRACKER_COOKIE_NAME=nuclear_order_bit_syndicate_session`
- `ME_TRACKER_URL=https://nobs.rawsmoke.net`
- `ME_TRACKER_DEFAULT=NOBS`
- `ME_TRACKER_COOKIE_NAME=nuclear_order_bit_syndicate_session`
- bloque `NOBS` en `config/config.py`
- `default_trackers = 'NOBS'`

Y además `config.py` conserva la flota multi-tracker anonimizada para no capar la suite a un solo tracker.

`NABS` queda fuera porque es testing interno.

---

## ✅ Qué editar después de instalar

Solo esto:

```text
config/.env
config/config.py
config/singularity_config.py
config/mass_config.py
```

Si esos archivos no existen tras `make install`, para ahí. No lances la suite todavía.

---

## ⚠️ Qué NO hacer

- bajar `RawLoadrr/` suelto y montarte una movida paralela
- clonar subdirectorios e inventar el resto
- desplegar en VM/LXC rara sin respetar mounts, launcher y config
- tunear menús sin haber corrido `make install`

Si haces eso, luego aparecen fantasmas tipo “falta NOBS” cuando en realidad faltan piezas del tanque.

---

## 🛠️ Qué hace esta suite

En corto:
1. MKVerything normaliza y rescata medios
2. Verifier audita en 4 capas
3. RawLoadrr sube a trackers UNIT3D
4. UNIT3D Orchestrator hace edición masiva, banners, imágenes, metadatos y mantenimiento
5. Singularity coordina todo desde TUI + dashboard

No es un uploader aislado. Es un orquestador.

---

## 📦 Modo repo completo (opcional)

Si clonas el repo entero, además del modo ligero tienes plantillas visibles en:
- `config/.env.example`
- `config/config.py.example`
- `config/singularity_config.py.example`
- `config/mass_config.py.example`

Sirven para inspección, diff y mantenimiento. Pero no son requisito para el usuario final del modo ligero.

---

## 🤝 Acknowledgments

Respeto a:
- ldu / Uploadrr
- MakeMKV
- MKVToolNix
- FFmpeg
- The TOR Project

---

## 📚 Lo técnico va aquí

Este README queda en modo operativo.

[![Setup](https://img.shields.io/badge/Setup-Despliegue-1f6feb?style=flat-square)](https://rawsmoke.codeberg.page/Singularity/setup/)
[![Índice](https://img.shields.io/badge/Docs-Índice-1f6feb?style=flat-square)](https://rawsmoke.codeberg.page/Singularity/)
[![Notas técnicas](https://img.shields.io/badge/Docs-Notas_técnicas-1f6feb?style=flat-square)](https://rawsmoke.codeberg.page/Singularity/technical_notes/)
[![Mass Edition](https://img.shields.io/badge/UNIT3D-Mass_Edition-1f6feb?style=flat-square)](https://rawsmoke.codeberg.page/Singularity/unit3d_mass_edition/)
[![RawLoadrr Wiki](https://img.shields.io/badge/RawLoadrr-Wiki-1f6feb?style=flat-square)](https://rawsmoke.codeberg.page/Singularity/rawloadrr_wiki/Home/)

Instalar sin inventar: arriba.
Entender las tripas: esos botones.