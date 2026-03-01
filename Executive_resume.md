# PRD: RaW_Suite — Full Project Review

## 1. Overview

**RaW_Suite** is a private media management monorepo composed of two independent but complementary Python applications designed for automated media processing and torrent uploading. Both tools are oriented toward the Spanish-speaking scene community (EMUWAREZ/MILNU) and share a common infrastructure philosophy: automation-first, resilient pipelines, and zero unattended data loss.

---

## 2. Projects in the Suite

### 2.1 RawLoadrr (Uploadrr — EMUWAREZ Edition)

**Purpose:** Automated torrent preparation and multi-tracker upload assistant.

**Entry Points:**
- `upload.py` — Main CLI upload script
- `discordbot.py` — Discord bot interface wrapping upload functionality
- `auto-upload.py` — Batch/queue upload helper (reads from a `.txt` task list)
- `triage_mkv.py` — Codec scanner to classify media files by video codec (HEVC vs H264/legacy) and generate upload priority lists

**Core Modules (`src/`):**

| Module | Role |
|---|---|
| `args.py` | CLI argument parser (argparse). Maps all upload flags into a `meta` dict. |
| `prep.py` | Media preparation engine. Orchestrates mediainfo, screenshots, DB lookups (TMDB, IMDB, MAL, MusicBrainz, Discogs), torrent creation, and name generation. |
| `clients.py` | Torrent client integration (qBittorrent, Deluge, rTorrent, Transmission). Handles seeding after upload. |
| `bbcode.py` | BBCode description generator for tracker posts. |
| `discparse.py` | Disc (Blu-ray/DVD) metadata parsing. |
| `musicbrainz.py` | MusicBrainz API integration for audio releases. |
| `discogs.py` | Discogs API integration for audio releases. |
| `search.py` | Duplicate torrent detection (cross-tracker search). |
| `unit3d_config.py` | Dynamic UNIT3D tracker configuration manager. |
| `unit3d_interactive.py` | TUI for configuring new UNIT3D-based trackers without editing code. |
| `logger.py` | Structured logging setup. |
| `rate_limiter.py` | API rate limiting for external service calls. |
| `tor_client.py` | Tor network client for anonymized operations. |
| `vs.py` | VapourSynth utilities. |
| `exceptions.py` | Custom exceptions. |
| `console.py` | Rich console wrapper. |

**Tracker Modules (`src/trackers/`):**
- ~50+ individual tracker integration modules (ACM, AITHER, BHD, BLU, EMU, MILNU, PTP, etc.)
- `COMMON.py` — Shared UNIT3D upload logic (torrent editing, dupe check, description formatting)
- `UNIT3D_TEMPLATE.py` — Boilerplate for new UNIT3D trackers

**Configuration (`data/`):**
- `config.py` — Main config (Python file, loaded at runtime). Sections: `DEFAULT`, `ADULT`, `SCREENS`, `SIGNATURES`, `AUTO`, `TRACKERS`, `TORRENT_CLIENTS`, `DISCORD`
- `reconfig.py` — Config migration/update helper
- `tags.json` — Tag definitions
- `templates/` — Description templates

**Discord Bot (`cogs/commands.py`):**
- Wraps the full upload pipeline behind Discord slash commands
- Triggered in a specific channel; calls `Prep` and tracker upload flows
- Supports `upload`, `search`, and `args` commands

**Upload Workflow:**
```
CLI args / Discord command
        ↓
   Args.parse() → meta{}
        ↓
   Prep() → mediainfo, screenshots, DB IDs, torrent file
        ↓
   Dupe check (COMMON / tracker-specific)
        ↓
   Tracker.upload() → POST to tracker API / HTTP
        ↓
   Clients.add_to_client() → seed in qBittorrent/Deluge/rTorrent
```

**Batch Upload Pattern:**
```bash
for dir in "/media/PELICULAS/"*/; do
  python3 upload.py "$dir" -tk EMU --unattended
done
```

---

### 2.2 MKVerything (V2.beta "The Purge")

**Purpose:** Automated media library normalization engine. Converts ISO disc images and legacy video formats to MKV containers; rescues corrupt/broken media files.

**Entry Points:**
- `launcher.py` — TUI menu (5 modes + God Mode pipeline)

**Core Modules (`modules/`):**

| Module | Role |
|---|---|
| `analyzer.py` | `DiscScanner` — uses `makemkvcon` to scan ISO contents and extract title metadata (duration-based filtering). |
| `extract.py` | `IsoExtractor` — orchestrates full ISO → MKV extraction via makemkvcon, selects main feature (largest file), verifies integrity. |
| `verifier.py` | `Verifier` — multi-layer integrity checks: structural (mkvmerge), metadata (ffprobe), full decode (ffmpeg null scan), rescue comparison, spam metadata detection. |
| `universal_rescuer.py` | `UniversalRescuer` — transcodes legacy/broken files to H.264 MKV via ffmpeg. Supports strict mode (broken MKVs only) and full mode (all legacy + MKV). |
| `mediainfo.py` | MediaInfo wrapper. |
| `metadata_provider.py` | TMDB/TVDB API integration for file metadata enrichment. |
| `persistence.py` | State persistence (`states/`) to enable resume across sessions. |

**5 Operating Modes:**

| Mode | Action |
|---|---|
| `[1]` ISO Extraction | ISO → MKV using makemkvcon |
| `[2]` Rescue Broken MKVs | Only corrupt MKVs → re-encode H.264 |
| `[3]` Field Audit | Full library health scan + report (`videos-rotos-DD-MM-YY.txt`) |
| `[4]` Convert Legacy | `.avi/.mp4/.wmv/etc` → `.mkv` (delete originals on success) |
| `[5]` God Mode | Full pipeline: modes 1 → 4 → cleanup, fully unattended |

**God Mode Pipeline:**
```
ISO Extraction → Legacy Conversion → MKV Rescue → Health Audit → Cleanup → GOD_MODE_log.txt
```

**Key Design Principles:**
- ISOs are **never deleted** (sacred masters)
- Legacy files (`.avi`, `.mp4`) are deleted only after successful `check_health()` verification
- 4-step `check_health()`: mkvmerge structural → ffprobe metadata → ffmpeg full decode
- `states/` directory enables pipeline resume (idempotent processing)
- Platform-portable: Windows + Linux (path injection at runtime)

**External Dependencies:**
- `ffmpeg` + `ffprobe` — transcoding and integrity verification
- `makemkvcon` — ISO disc image extraction
- `mkvmerge` — MKV structural validation
- `mediainfo` — metadata extraction
- `TMDB API` / `TVDB API` — metadata enrichment

---

## 3. Inter-Project Relationship

The two tools form a **pipeline**:

```
[Raw Media Library]
        ↓
MKVerything → normalizes ISOs + legacy files → clean MKV library
        ↓
RawLoadrr → takes clean MKVs → prepares + uploads to private trackers
        ↓
[Seeded in torrent client]
```

**triage_mkv.py** (in RawLoadrr root) serves as a bridge tool: it scans the normalized library, classifies files by codec (HEVC vs H264), and generates prioritized upload queues for RawLoadrr.

---

## 4. Technology Stack

| Component | Technology |
|---|---|
| Language | Python 3.6+ |
| CLI framework | `argparse` + `rich` (console UI) |
| Media analysis | `pymediainfo`, `ffmpeg-python`, subprocess calls to `mediainfo`/`ffprobe`/`mkvmerge` |
| Database APIs | `tmdbsimple`, `imdbpy` (Cinemagoer), MusicBrainz, Discogs |
| Torrent | `torf`, `bencodepy` |
| Torrent clients | `qbittorrentapi`, `deluge_client`, rTorrent XML-RPC, Transmission |
| Image hosting | imgbb, ptpimg, imgbox, pixhost, lensdump |
| Discord bot | `discord.py` (ext.commands) |
| Async | `asyncio`, `aiohttp`, `nest_asyncio` |
| Logging | Python `logging` + structured file loggers |
| State | File-based (`states/` JSON files) |
| Config | Python module (`data/config.py`) |

---

## 5. Configuration Model

### RawLoadrr (`data/config.py`)
- `DEFAULT`: TMDb API key, default screens count, image host, torrent client
- `TRACKERS`: per-tracker API keys and announce URLs
- `TORRENT_CLIENTS`: per-client connection settings
- `DISCORD`: bot token, channel ID, command prefix
- `SIGNATURES`: per-tracker description footers
- `AUTO`: duplicate check behavior, auto-mode flags
- `SCREENS`: screenshot generation options

### MKVerything (`.env`)
- `TMDB_API_KEY`
- `TVDB_API_KEY`

---

## 6. Operational Workflows

### Workflow A: Single Upload (Interactive)
1. User invokes `python3 upload.py /path/to/media -tk EMU`
2. `Args.parse()` resolves path, tracker, options into `meta` dict
3. `Prep()` collects: mediainfo, screenshots, TMDB/IMDB IDs, creates `.torrent`
4. Tracker module performs dupe check, formats description (BBCode)
5. Tracker module posts to API
6. `Clients.add_to_client()` injects torrent into local client

### Workflow B: Batch Upload (Unattended)
1. User generates queue (e.g., with `triage_mkv.py`)
2. Shell loop or `auto-upload.py` feeds paths to `upload.py --unattended`
3. Each upload runs in sequence; failures are logged and skipped

### Workflow C: Discord Upload
1. User sends `!up /path/to/media -tk EMU` in configured Discord channel
2. Bot parses command, calls same `Prep` + tracker pipeline
3. Sends embed status updates to Discord

### Workflow D: ISO Library Normalization (MKVerything)
1. User launches `python launcher.py`
2. Selects mode `[1]` ISO Extraction
3. Provides source folder (containing `.iso` files) and destination
4. `IsoExtractor` calls makemkvcon, selects main title, verifies integrity
5. Clean MKV placed in destination; `states/` records completion

### Workflow E: God Mode (Full Unattended Pipeline)
1. User selects mode `[5]` in TUI
2. Provides source + destination + delete confirmation
3. Pipeline executes: ISO extraction → legacy conversion → MKV rescue → audit
4. Runs unattended; `GOD_MODE_log.txt` records all activity
5. Resume-capable via `states/`

---

## 7. Key Functionalities Summary

- **Multi-tracker upload**: 50+ private trackers (UNIT3D-based and custom)
- **Full media metadata resolution**: TMDB, IMDB, MAL, MusicBrainz, Discogs
- **Screenshot generation**: configurable count, multiple hosting services
- **Duplicate detection**: cross-tracker dupe check before upload
- **Torrent client integration**: qBittorrent, Deluge, rTorrent, Transmission
- **Discord bot interface**: remote upload triggering via Discord
- **Dynamic UNIT3D tracker configuration**: add new trackers via TUI without code changes
- **ISO extraction**: makemkvcon-based disc image extraction
- **File integrity verification**: 3-layer check (structural, metadata, full decode)
- **Legacy format conversion**: AVI/MP4/WMV → MKV via ffmpeg H.264
- **Broken MKV rescue**: re-encode corrupt containers
- **Codec triage**: HEVC vs H264 classification for upload prioritization
- **Resume capability**: state persistence across interrupted runs
- **Unattended/batch mode**: full automation without user interaction
- **Spam metadata detection**: flags files with piracy watermarks in metadata

---

## 8. File Structure Overview

```
RaW_Suite/
├── RawLoadrr/
│   ├── upload.py               # Main upload CLI
│   ├── discordbot.py           # Discord bot entry point
│   ├── auto-upload.py          # Batch queue uploader
│   ├── triage_mkv.py           # Codec classifier / upload list generator
│   ├── data/
│   │   ├── config.py           # Main configuration
│   │   ├── reconfig.py         # Config migration
│   │   └── templates/          # Description templates
│   ├── src/
│   │   ├── prep.py             # Media preparation engine (~4000 lines)
│   │   ├── args.py             # CLI argument parser
│   │   ├── clients.py          # Torrent client integrations
│   │   ├── bbcode.py           # Description generator
│   │   ├── unit3d_config.py    # Dynamic UNIT3D config
│   │   ├── unit3d_interactive.py # TUI for tracker config
│   │   └── trackers/
│   │       ├── COMMON.py       # Shared UNIT3D upload logic
│   │       ├── UNIT3D_TEMPLATE.py # Tracker template
│   │       └── [50+ tracker modules]
│   └── cogs/
│       └── commands.py         # Discord bot commands
└── MKVerything_Suite_Edition/
    └── MKVerything_PROJECT-V2/
        ├── launcher.py         # TUI menu entry point
        ├── modules/
        │   ├── analyzer.py     # ISO disc scanner
        │   ├── extract.py      # ISO extractor
        │   ├── verifier.py     # Integrity verifier
        │   ├── universal_rescuer.py # File transcoder
        │   ├── mediainfo.py    # MediaInfo wrapper
        │   ├── metadata_provider.py # TMDB/TVDB metadata
        │   └── persistence.py  # State management
        └── .env                # API keys
```
