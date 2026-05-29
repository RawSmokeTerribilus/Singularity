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

No tienes que cazar archivos sueltos por el repo. Cada plataforma tiene su carpeta lista para
descargar, con **todo lo necesario dentro**:

| Plataforma | Carpeta | Contenido |
|---|---|---|
| 🐧 Linux | [`linux-installer/`](linux-installer/) | `docker-compose.yml` · `makefile` · `final-user-install.sh` |
| 🪟 Windows | [`windows-installer/`](windows-installer/) | `docker-compose.yml` · `install-windows.bat` · `setup-windows.ps1` |

Baja la carpeta de tu sistema (o solo esos archivos), mételos en una carpeta vacía en tu `HOME`
y sigue los pasos de abajo. No hace falta clonar el repo entero ni reconstruir la imagen: solo la
imagen publicada + esos archivos. Las plantillas de config **y los 53 módulos de tracker** se
extraen solos desde la imagen.

---

### 🐧 Linux

```bash
make install   # crea config/ y work_data/, genera plantillas, siembra trackers, instala el lanzador
make up        # baja la imagen si hace falta y arranca el contenedor
make attach    # entra a la TUI
singularity    # y a partir de aquí, este comando abre la TUI cuando quieras
```

Qué hace `make install`:
- crea `./config/` y `./work_data/`
- instala `singularity` y `singularity-shell`
- genera `.env`, `config.py`, `singularity_config.py` y `mass_config.py`
- siembra `work_data/trackers` desde la imagen (si no, verías `ModuleNotFoundError: src.trackers.PTP`)
- deja `NOBS` preformado y `config.py` multi-tracker para cualquier UNIT3D serio

**Qué evitar:** no ejecutes los `make` con `sudo` (el script pide permisos solo cuando toca); no
muevas `config/` ni `work_data/` tras instalar; no bajes `RawLoadrr/` suelto — esto es un tanque,
no una pieza suelta.

---

### 🪟 Windows (Docker Desktop)

1. Instala **Docker Desktop** y déjalo arrancado (WSL2 backend).
2. Crea una carpeta vacía, por ejemplo `C:\Singularity`, y mete dentro los 3 archivos de
   [`windows-installer/`](windows-installer/).
3. **Doble clic en `install-windows.bat`** (o botón derecho → Ejecutar). Hace lo mismo que
   `make install`: crea `config/` y `work_data/`, extrae las plantillas y los trackers desde la
   imagen, y genera los lanzadores `up.bat` / `singularity.bat` / `singularity-shell.bat`.
4. Edita tus claves en `config/` (ver “Qué configurar…”). **En Windows, el qBit/Sonarr/Radarr de
   tu host se alcanzan por `host.docker.internal`, no por `127.0.0.1`** — cámbialo en
   `config/config.py`.
5. `up.bat` para arrancar el contenedor → `singularity.bat` para entrar a la TUI.

**Realidad de Windows (no es magia):**
- **Sin aceleración hardware.** WSL2 es virtualización: MKVerything transcodifica por CPU (lento).
  Sirve para probar la lógica de subida, no para lotes de transcode.
- **Medios:** por defecto se monta la carpeta `media` que el instalador crea junto al compose —
  suelta ahí tus pelis/series y listo. Para apuntar a tu carpeta real, **abre
  `docker-compose.yml` con el Bloc de notas** y edita la línea marcada (ej. `- D:\Pelis:/media`).
  Sin terminal, sin variables de entorno.
- El compose de Windows va **sin** `privileged`, `/dev/dri`, `group_add`, `:z` ni `network_mode:
  host` (ninguno aplica en Docker Desktop).

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

## 🔑 Qué configurar para que funcione de verdad

Poner solo el tracker no basta. La suite necesita claves para **identificar** la película/serie
y para **subir las imágenes**. Si te falta alguna, el upload se queda a medias.

**Identificación (lo más importante):** se decide por **consenso entre proveedores**, no por uno
solo. Hace falta que **al menos dos coincidan**.
- `tmdb_api` — TMDB (gratis, registro).
- `imdb_api` — en realidad es la clave de **OMDb** (gratis, te la mandan por email).
- TVmaze — **sin clave**, pero **solo sirve para series**.

Consecuencia práctica:
- **Solo TMDB → la identificación falla** (un único voto no confirma nada). Verás cosas tipo
  “ID not confirmed — providers disagree”.
- **Películas:** necesitas **TMDB + OMDb** sí o sí (TVmaze no vota en cine).
- **Series:** TMDB + OMDb + TVmaze.
- **Anime:** además entran MAL/AniList cuando el release parece anime.

**Image hosts:** configura **varios**, no uno. Los planes gratuitos tienen límites de subida y
si uno te corta el grifo a media tanda, el upload se cae. Campos disponibles: `imgbb_api`,
imgbox, `ptscreens_api`, `ptpimg_api`, `lensdump_api`, `oeimg_api`. Pon dos o tres como mínimo.

**Cliente torrent (qBittorrent):** url, puerto, usuario, contraseña y la ruta de sesión
(`torrent_storage_dir` / `BT_backup`). Sin esto, el `.torrent` se genera pero no se siembra.

> Regla simple: **TMDB + OMDb + un par de image hosts + qBit**. Eso es el mínimo para que un
> upload termine entero.

---

## ⚠️ Qué NO hacer

- bajar `RawLoadrr/` suelto y montarte una movida paralela
- clonar subdirectorios e inventar el resto
- desplegar en VM/LXC rara sin respetar mounts, launcher y config
- tunear menús sin haber corrido `make install`

Si haces eso, luego aparecen fantasmas tipo “falta NOBS” cuando en realidad faltan piezas del tanque.

**Sobre meter capas (VM, LXC, otro Docker dentro de otro…):** corre esto en tu `~/` directo.
El motivo no es manía: **en una VM o un LXC la aceleración hardware no funciona, sin más.** Todo
el trabajo pesado cae sobre la CPU. MKVerything (normalizar, rescatar, transcodificar) pasa de
minutos a **horas o días** — directamente inusable. La única excepción es un hipervisor con
passthrough de HW real (gente de NAS/Proxmox que sabe lo que hace), y casi nadie monta eso.

Si **aun así** vas a virtualizar, asúmelo: irás por CPU y será lento. Y antes de arrancar, ten
plan para **lo compartido** — carpetas de medios (mounts NFS/CIFS), devices y la red hacia
qBittorrent. Si no defines cómo ven los datos y el cliente las distintas capas, el contenedor
arranca pero no encuentra ni los archivos ni qBit. Lo que falle ahí es tuyo.

(Workarounds concretos para desatascar el arranque en VM/LXC más abajo, mientras preparamos la
versión *lite*.)

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

## 🧪 Workarounds para VM/LXC (mientras llega la *lite*)

No es escenario soportado. **Esto NO arregla el rendimiento** — seguirás en CPU y MKVerything
seguirá siendo lento. Solo sirve para que el stack al menos arranque y se deje usar:

- **El rendimiento no se arregla.** No hay flag ni truco: sin HW accel, normalizar/transcodificar
  va por CPU. Para lotes grandes, no virtualices.
- **Permisos / UID.** El contenedor corre como `uid 1000`. Si tu usuario host (o el desplazamiento
  de UID del LXC) no es 1000, los directorios montados (`work_data`, `logs`, `config`) salen
  inaccesibles → `PermissionError`. Workaround: crea esos dirs a mano y `chown -R 1000:1000`
  sobre ellos, o corre el stack desde un usuario host que sea `uid 1000`.
- **Trackers que “desaparecen”** (`ModuleNotFoundError: src.trackers.PTP`). El bind-mount de
  `work_data/trackers` vacío tapa los trackers que trae la imagen. Déjalo que se auto-rellene
  (`make up` lo siembra desde la imagen) o, si tu capa lo impide, copia los trackers a mano:
  `docker cp singularity_core:/app/RawLoadrr/src/trackers/. work_data/trackers/`.
- **`INCORRECT QBIT LOGIN CREDENTIALS` con qBit que sí funciona.** Suele ser puerto/bloque qBit
  equivocado en `config.py`, no la contraseña. Revisa que apuntas al puerto real del WebUI y que
  no estás usando un bloque legacy.
- **qBittorrent inalcanzable.** Dentro de otra capa, `127.0.0.1` no es el qBit del host. Usa una
  IP que el contenedor pueda alcanzar (la de la bridge, o `host.docker.internal` donde exista).
- **Dashboard solo en localhost.** Escucha en loopback **a propósito**: no lleva auth, así que no
  está hecho para exponerse. Si lo necesitas desde fuera de la capa, **túnel SSH** (o un reverse
  proxy con autenticación delante). **Nunca lo bindees a `0.0.0.0`** — eso publica un panel sin
  contraseña en la red.

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