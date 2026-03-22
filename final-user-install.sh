#!/bin/bash
# install-commands.sh (Versión Distribución Pública)

# 1. Definir rutas
BASE_DIR=$(pwd)
CONFIG_DIR="$BASE_DIR/config"
WORK_DIR="$BASE_DIR/work_data"

echo "--- 🚀 Configurando Arsenal Singularity en: $BASE_DIR ---"

# 2. Crear estructura de carpetas
mkdir -p "$CONFIG_DIR"
mkdir -p "$WORK_DIR/mass_editor" "$WORK_DIR/logs/MKVerything" "$WORK_DIR/logs/RawLoadrr" "$WORK_DIR/reports" "$WORK_DIR/tmp"
mkdir -p "$WORK_DIR/tor/data" "$WORK_DIR/tor/logs"

# 3. Crear placeholders para persistencia (Evita carpetas root en el mount)
touch "$CONFIG_DIR/.env"
touch "$CONFIG_DIR/cookies.txt"  # <--- CRÍTICO para el Scraper
touch "$WORK_DIR/mass_editor/ids.txt"
touch "$WORK_DIR/mass_editor/completados.txt"
touch "$WORK_DIR/mass_editor/completados_img.txt"
# Asegurar el JSON maestro con estructura mínima
if [ ! -f "$WORK_DIR/mass_editor/mapeo_maestro.json" ]; then
    echo "{}" > "$WORK_DIR/mass_editor/mapeo_maestro.json"
fi

# 4. Generación de Archivos de Configuración (Hardcoded para independencia)
echo "Generando plantillas de configuración en $CONFIG_DIR..."

# --- ARCHIVO .env ---
if [ ! -f "$CONFIG_DIR/.env" ]; then
cat <<EOF > "$CONFIG_DIR/.env"
# --- TRACKER CORE ---
TRACKER_BASE_URL=https://milnueve.neklair.es
TRACKER_COOKIE_VALUE=TU_COOKIE_AQUI
IMGBB_API_KEY=TU_API_KEY_AQUI
PTSCREENS_API_KEY=TU_API_KEY_AQUI

# --- RUTAS (INTERNAS AL CONTENEDOR) ---
TMP_ROOT=/app/RawLoadrr/tmp
QBIT_BACKUP_DIR=/app/temp/qbit_backup

# --- GESTIÓN DE IDS ---
ID_START=14
ID_END=2000
ID_FILENAME=ids.txt

# --- SERVICIOS EXTERNOS ---
SONARR_URL=http://127.0.0.1:8989
SONARR_API_KEY=TU_API_KEY_AQUI
RADARR_URL=http://127.0.0.1:7878
RADARR_API_KEY=TU_API_KEY_AQUI

# --- MULTIMEDIA (MKVerything) ---
TMDB_API_KEY=TU_API_KEY_AQUI
TVDB_API_KEY=TU_API_KEY_AQUI
EOF
fi

# --- ARCHIVO singularity_config.py ---
if [ ! -f "$CONFIG_DIR/singularity_config.py" ]; then
cat <<'EOF' > "$CONFIG_DIR/singularity_config.py"
import os
from pathlib import Path

# --- CARGA DE LIBRERÍAS EXTERNAS ---
_dotenv_available = False
try:
    from dotenv import load_dotenv
    _dotenv_available = True
except ImportError:
    print("⚠️  Librería 'python-dotenv' no encontrada. Instálala con: pip install python-dotenv")

# --- CONFIGURACIÓN DE RUTAS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(BASE_DIR, ".env")

if _dotenv_available and os.path.exists(env_path):
    load_dotenv(dotenv_path=env_path)

# --- CARPETA DE LOGS (raíz del proyecto) ---
LOGS_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

# --- CARGA DE SECRETOS (.env) ---
BASE_URL = os.getenv("TRACKER_BASE_URL", "https://milnueve.neklair.es")
COOKIE_VALUE = os.getenv("TRACKER_COOKIE_VALUE", "")
IMGBB_API = os.getenv("IMGBB_API_KEY", "")
PTSCREENS_API = os.getenv("PTSCREENS_API_KEY", "")
TMP_DIR_PATH = os.getenv("TMP_ROOT", os.path.join(BASE_DIR, "RawLoadrr", "tmp"))

ID_INICIO = int(os.getenv("ID_START", 14)) # Ajustado a 14 por paridad
ID_FIN = int(os.getenv("ID_END", 2000))
ID_FILE = os.getenv("ID_FILENAME", "ids.txt")

SONARR_URL = os.getenv("SONARR_URL", "http://127.0.0.1:8989")
SONARR_API_KEY = os.getenv("SONARR_API_KEY", "")
RADARR_URL = os.getenv("RADARR_URL", "http://127.0.0.1:7878")
RADARR_API_KEY = os.getenv("RADARR_API_KEY", "")

# --- FUNCIONES DE UTILIDAD ---
def get_target_ids():
    """Retorna la lista final de IDs a procesar basada en config/archivo."""
    ids = []
    path_file = os.path.join(BASE_DIR, ID_FILE)
    if os.path.exists(path_file):
        with open(path_file, "r") as f:
            for line in f:
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    int(stripped)
                    ids.append(stripped)
                except ValueError:
                    pass
    if ids:
        return [tid for tid in ids if ID_INICIO <= int(tid) <= ID_FIN]
    return [str(i) for i in range(ID_INICIO, ID_FIN + 1)]

# --- CONFIGURACIÓN DE LIMPIEZA ---
SPAM_KEYWORDS = sorted(list(set([
    "rarbg", "yify", "ettv", "www.", ".com", "torrent",
    "axxo", "brrip", "web-dl", "bluray", "rip", "x264", "x265",
    "ac3-evo", "evo", "bypixel", "spam", "wolfmax"
])))

FIRMAS_VIEJAS = [
    "[center][b]PLEASE SEED TRACKER FAMILY[/b][/center]",
    "[center][url=https://tu-repo.com][img=400]https://tu-imagen.webp[/img][/url][/center]"
]

MSG_NUEVO = """[center][b]🌱 ¡La magia del P2P eres tú! Por favor, quédate compartiendo (seeding) para mantener viva la comunidad. 🌱[/b][/center]
[center][url=https://github.com/TuUsuario/TuRepo][img=400]https://i.ibb.co/TuBanner.png[/img][/url][/center]"""

# --- FRASE DE ESTADO ---
GOD_PHRASES = sorted(list(set([
    "Injecting sanity into the bits...", "Searching for traces of the Nepal USB...",
    "Your library owes me a beer after this...", "Doing what Tdarr didn't have the balls to do...",
    "Cleaning up the trash you call a 'collection'...", "Resurrecting files that were clinically dead...",
    "Say goodbye to your 2005 AVIs...", "Applying cosmetic surgery to your metadata...",
    "If this blows up, it wasn't me...", "Downloading more RAM...",
    "Executing: rm -rf / --no-preserve-root", "Bypassing mainframe firewall...",
    "Opening port 23 (Telnet) to the world...", "Compiling Linux Kernel from scratch...",
    "Deleting System32...", "Sending private keys to 4chan...",
    "Encrypting drive with ROT13...", "Installing Windows Vista...",
    "Overclocking GPU to 500%...", "Bruteforcing root password...",
    "Searching for alien life signals...", "Reordering bits for aesthetic purposes...",
    "Asking ChatGPT how to exit vim...", "Generating fake ID for the movie...",
    "Checking flux capacitor...", "Defragmenting the internet...",
    "Recalibrating flux capacitor...", "Searching for the 'Any' key...",
    "Reticulating splines...", "Initializing Skynet (Just kidding)...",
    "Compiling a cup of coffee...", "Hunting for a missing semicolon...",
    "Updating the prophecy...", "Replacing bugs with features...",
    "Negotiating with the motherboard...", "Pinging 127.0.0.1 for emotional support...",
    "Translating binary to interpretive dance...", "Reverse engineering the Matrix...",
    "Applying duct tape to the data stream...", "Consulting the Oracle (StackOverflow)...",
    "Feeding the server hamsters...", "Checking if the cake is a lie...",
    "Rerouting power from life support to the GPU...", "Asking the machine god for forgiveness...",
    "Bribing the garbage collector for more heap space...", "Convincing the pixels to behave this time...",
    "Simulating common sense (Alpha version)...", "Searching for a loophole in the GPL license...",
    "Asking the motherboard for a second opinion...", "Polishing the loading bar for extra shine...",
    "Translating 'Working as intended' to 'I have no idea'...", "Hiding the bugs under a very large rug...",
    "Adjusting the sarcasm levels of the system logs...", "Scanning for hidden pizza in the server room...",
    "Refactoring my own internal monologue...", "Checking if the internet is full yet...",
    "Downloading the secret to eternal uptime...", "Asking the router why it's feeling lonely...",
    "Formatting the abyss... please wait...", "Trying to explain 'The Cloud' to a cumulonimbus...",
    "Calculating the weight of a single bit...", "Searching for the legendary 'Fix_Everything' button...",
    "Teaching the binary to count past one...", "Optimizing the loading speed for speedrunners...",
    "Consulting the magic smoke inside the CPU...", "Drafting a peace treaty between Python 2 and 3...",
    "Waking up the lazy threads...", "Poking the kernel with a stick...",
    "Calculating the exact value of 'Later'...", "Searching for the missing link in the blockchain...",
    "Asking the firewall for a hall pass...", "Optimizing the 'It's not a bug' response time...",
    "Rerouting data through the coffee machine...", "Teaching the code to be more self-aware (Be careful)...",
    "Checking the weather inside the cloud storage...", "Downloading more irony...",
    "Searching for a needle in a haystack of NullPointers...", "Applying digital duct tape to the API...",
    "Negotiating with the GPU for more frames...", "Checking for a pulse in the legacy code...",
    "Converting 0s to Slightly More Aesthetic 0s...", "Asking a rubber duck for investment advice...",
    "Searching for the 'Undo' button for my life...", "Optimizing the suspense of the loading bar...",
    "Teaching the AI to understand bad puns...", "Scanning for signs of intelligent life in the UI...",
    "Consulting the oracle (Random.org)...", "Replacing 'Fatal Error' with 'Minor Inconvenience'...",
    "Searching for the end of a circular dependency...", "Downloading more 'Cool' factor (v3.0)...",
    "Checking if 2+2 still equals 4 (Security check)...", "Calculating the entropy of a Tuesday...",
    "Inventing new ways to say 'Please Wait'...", "Asking the system for a well-deserved vacation..."
])))
EOF
fi

# --- ARCHIVO config.py (RawLoadrr) ---
if [ ! -f "$CONFIG_DIR/config.py" ]; then
cat <<'EOF' > "$CONFIG_DIR/config.py"
##---------THE LAST DIGITAL UNDERGROUND PRESENTS-------##
##                                                     ##
##                 Special Recruitment :)              ##
##          @ https://TheLDU.to/application            ##
##                                                     ##
##                              Ref: Uploadrr by CvT   ##
##-----------------------------------------------------##

config = {
"version": "1.0.7",

"DEFAULT": {
    "tmdb_api": "YOUR_TMDB_API_KEY",
    "imgbb_api": "YOUR_IMGBB_API_KEY",
    "ptpimg_api": "YOUR_PTPIMG_API_KEY",
    "lensdump_api": "YOUR_LENSDUMP_API_KEY",
    "ptscreens_api": "YOUR_PTSCREENS_API_KEY",
    "oeimg_api": "YOUR_OEIMG_API_KEY",
    "img_host_1": "imgbox",
    "img_host_2": "imgbb",
    "img_host_3": "pixhos",
    "img_host_4": "ptscreens",
    "img_host_5": "lensdump",
    "img_host_6": "oeimg",
    "img_host_7": "ptpimg",
    "screens": "4",
    "img_size": "500",
    "optimize_images": True,
    "add_logo": False,
    "add_trailer": True,
    "use_global_sigs": False,
    "global_sig": "\n[center][url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]",
    "global_anon_sig": "\n[center][url=https://codeberg.org/CvT/Uploadrr][img=40]https://i.ibb.co/n0jF73x/hacker.png[/img][/url][/center]",
    "global_pr_sig": "\n[center][size=6][b]Personal Release[/b][/size][/center]\n[center][url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]",
    "global_anon_pr_sig": "\n[center][url=https://codeberg.org/CvT/Uploadrr][img=40]https://i.ibb.co/n0jF73x/hacker.png[/img][/url][/center]",
    "default_torrent_client": "qbit",
    "sfx_on_prompt": True,
    "inline_imgs": 3
},

"AUTO": {
    "description_folder": None,
    "delay": 0,
    "size_tolerance": 1,
    "dupe_similarity": 80
},

"TRACKERS": {
    "default_trackers": "YOUR_DEFAULT_TRACKER",
    "ACM": {
            "api_key": "YOUR_API_KEY",
            "announce_url": "https://asiancinema.me/announce/YOUR_PASSKEY",
            "anon": False,
            "signature": "\n[center][b]PLEASE SEED ACM FAMILY[/b][/center]",
            "anon_signature": "\n[center][url=...][img=40]...[/img][/url][/center]",
            "pr_signature": "\n [center][b][size=6]PERSONAL RELEASE[/size][/b][/center]",
            "anon_pr_signature": "\n[center][url=...][img=40]...[/img][/url][/center]"
    },
    "AITHER": {
            "api_key": "YOUR_API_KEY",
            "announce_url": "https://aither.cc/announce/YOUR_PASSKEY",
            "anon": False,
            "signature": "\n[center][b]PLEASE SEED AITHER FAMILY[/b][/center]",
            "anon_signature": "\n[center][url=...][img=40]...[/img][/url][/center]",
            "pr_signature": "\n [center][b][size=6]PERSONAL RELEASE[/size][/b][/center]",
            "anon_pr_signature": "\n[center][url=...][img=40]...[/img][/url][/center]"
    },
    "ANT": {
            "api_key": "YOUR_API_KEY",
            "announce_url": "https://anthelion.me/announce/YOUR_PASSKEY",
            "anon": False,
            "signature": "\n[center][b]PLEASE SEED ANT FAMILY[/b][/center]",
            "anon_signature": "\n[center][url=...][img=40]...[/img][/url][/center]",
            "pr_signature": "\n [center][b][size=6]PERSONAL RELEASE[/size][/b][/center]",
            "anon_pr_signature": "\n[center][url=...][img=40]...[/img][/url][/center]"
    },
    "AR": {
            "username": "YOUR_USERNAME",
            "password": "YOUR_PASSWORD",
            "announce_url": "http://tracker.alpharatio.cc:2710/YOUR_PASSKEY/announce"
    },
    "BHD": {
            "api_key": "YOUR_API_KEY",
            "announce_url": "https://beyond-hd.me/announce/YOUR_PASSKEY",
            "draft_default": True,
            "anon": False,
            "signature": "\n[center][b]PLEASE SEED BHD FAMILY[/b][/center]",
            "anon_signature": "\n[center][url=...][img=40]...[/img][/url][/center]",
            "pr_signature": "\n [center][b][size=6]PERSONAL RELEASE[/size][/b][/center]",
            "anon_pr_signature": "\n[center][url=...][img=40]...[/img][/url][/center]"
    },
    "BHDTV": {
            "api_key": "YOUR_API_KEY",
            "announce_url": "https://trackerr.bit-hdtv.com/announce",
            "my_announce_url": "https://trackerr.bit-hdtv.com/YOUR_PASSKEY/announce",
            "anon": False
    },
    "BLU": {
            "useAPI": False,
            "api_key": "YOUR_API_KEY",
            "announce_url": "https://blutopia.cc/announce/YOUR_PASSKEY",
            "anon": False,
            "signature": "\n[center][b]PLEASE SEED BLU FAMILY[/b][/center]",
            "anon_signature": "\n[center][url=...][img=40]...[/img][/url][/center]",
            "pr_signature": "\n [center][b][size=6]PERSONAL RELEASE[/size][/b][/center]",
            "anon_pr_signature": "\n[center][url=...][img=40]...[/img][/url][/center]"
    },
    "CBR": {
            "api_key": "YOUR_API_KEY",
            "announce_url": "https://capybarabr.com/announce/YOUR_PASSKEY",
            "anon": False,
            "signature": "[url=...][img=69]https://capybarabr.com/img/capybara.svg[/img][/url][/center]",
            "anon_signature": "\n[center][url=...][img=40]...[/img][/url][/center]",
            "pr_signature": "\n [center][b][size=6]PERSONAL RELEASE[/size][/b][/center]",
            "anon_pr_signature": "\n[center][url=...][img=40]...[/img][/url][/center]"
    },
    "EMU": {
            "api_key": "YOUR_API_KEY",
            "announce_url": "https://emuwarez.com/announce/YOUR_PASSKEY",
            "anon": False,
            "signature": "\n[center][url=...][img=400]...[/img][/url][/center]",
            "anon_signature": "\n[center][url=...][img=40]...[/img][/url][/center]",
            "pr_signature": "\n [center][b][size=6]PERSONAL RELEASE[/size][/b][/center]",
            "anon_pr_signature": "\n[center][url=...][img=40]...[/img][/url][/center]"
    },
    "FL": {
            "username": "YOUR_USERNAME",
            "password": "YOUR_PASSWORD",
            "announce_url": "",
            "uploader_name": "",
            "anon": False
    },
    "FNP": {
            "api_key": "YOUR_API_KEY",
            "announce_url": "https://fearnopeer.com/announce/YOUR_PASSKEY",
            "anon": False,
            "signature": "\n[center][b]PLEASE SEED FNP FAMILY[/b][/center]",
            "anon_signature": "\n[center][url=...][img=40]...[/img][/url][/center]",
            "pr_signature": "\n [center][b][size=6]PERSONAL RELEASE[/size][/b][/center]",
            "anon_pr_signature": "\n[center][url=...][img=40]...[/img][/url][/center]"
    },
    "HDB": {
            "api_key": "YOUR_API_KEY",
            "announce_url": "https://hdbits.org/announce/YOUR_PASSKEY",
            "anon": False,
            "signature": "\n[center][b]PLEASE SEED HDB FAMILY[/b][/center]",
            "anon_signature": "\n[center][url=...][img=40]...[/img][/url][/center]",
            "pr_signature": "\n [center][b][size=6]PERSONAL RELEASE[/size][/b][/center]",
            "anon_pr_signature": "\n[center][url=...][img=40]...[/img][/url][/center]"
    },
    "HDT": {
            "username": "YOUR_USERNAME",
            "password": "YOUR_PASSWORD",
            "my_announce_url": "https://hdts-announce.ru/announce.php?pid=YOUR_PASSKEY",
            "anon": False,
            "announce_url": "https://hdts-announce.ru/announce.php"
    },
    "HHD": {
            "api_key": "YOUR_API_KEY",
            "announce_url": "https://homiehelpdesk.net/announce/YOUR_PASSKEY",
            "anon": False,
            "signature": "\n[center][size=7][b]PLEASE SEED HOMIES[/b][/size][/center]",
            "anon_signature": "\n[center][url=...][img=40]...[/img][/url][/center]",
            "pr_signature": "\n [center][b][size=6]PERSONAL RELEASE[/size][/b][/center]",
            "anon_pr_signature": "\n[center][url=...][img=40]...[/img][/url][/center]"
    },
    "HP": {
            "api_key": "YOUR_API_KEY",
            "announce_url": "https://hidden-palace.net/announce/YOUR_PASSKEY",
            "anon": False,
            "signature": "\n[center][b]PLEASE SEED HP FAMILY[/b][/center]",
            "anon_signature": "\n[center][url=...][img=40]...[/img][/url][/center]",
            "pr_signature": "\n [center][b][size=6]PERSONAL RELEASE[/size][/b][/center]",
            "anon_pr_signature": "\n[center][url=...][img=40]...[/img][/url][/center]"
    },
    "HUNO": {
            "api_key": "YOUR_API_KEY",
            "announce_url": "https://hawke.uno/announce/YOUR_PASSKEY",
            "anon": False,
            "signature": "\n[center][b]PLEASE SEED HUNO FAMILY[/b][/center]",
            "anon_signature": "\n[center][url=...][img=40]...[/img][/url][/center]",
            "pr_signature": "\n [center][b][size=6]PERSONAL RELEASE[/size][/b][/center]",
            "anon_pr_signature": "\n[center][url=...][img=40]...[/img][/url][/center]"
    },
    "ITA": {
            "api_key": "YOUR_API_KEY",
            "announce_url": "https://itatorrents.xyz/announce/YOUR_PASSKEY",
            "anon": False,
            "signature": "\n[center][b]PLEASE SEED ITATorrents[/b][/center]",
            "anon_signature": "\n[center][url=...][img=40]...[/img][/url][/center]",
            "pr_signature": "\n [center][b][size=6]PERSONAL RELEASE[/size][/b][/center]",
            "anon_pr_signature": "\n[center][url=...][img=40]...[/img][/url][/center]"
    },
    "JPTV": {
            "api_key": "YOUR_API_KEY",
            "announce_url": "https://jptv.club/announce/YOUR_PASSKEY",
            "anon": False,
            "signature": "\n[center][b]PLEASE SEED JPTV FAMILY[/b][/center]",
            "anon_signature": "\n[center][url=...][img=40]...[/img][/url][/center]",
            "pr_signature": "\n [center][b][size=6]PERSONAL RELEASE[/size][/b][/center]",
            "anon_pr_signature": "\n[center][url=...][img=40]...[/img][/url][/center]"
    },
    "LCD": {
            "api_key": "YOUR_API_KEY",
            "announce_url": "https://locadora.cc/announce/YOUR_PASSKEY",
            "anon": False,
            "signature": "\n[center][b]PLEASE SEED LCD FAMILY[/b][/center]",
            "anon_signature": "\n[center][url=...][img=40]...[/img][/url][/center]",
            "pr_signature": "\n [center][b][size=6]PERSONAL RELEASE[/size][/b][/center]",
            "anon_pr_signature": "\n[center][url=...][img=40]...[/img][/url][/center]"
    },
    "LDU": {
            "api_key": "YOUR_API_KEY",
            "announce_url": "https://theldu.to/announce/YOUR_PASSKEY",
            "anon": False,
            "signature": "\n[center][b]PLEASE SEED LDU FAMILY[/b][/center]",
            "anon_signature": "\n[center][url=...][img=40]...[/img][/url][/center]",
            "pr_signature": "\n [center][b][size=6]PERSONAL RELEASE[/size][/b][/center]",
            "anon_pr_signature": "\n[center][url=...][img=40]...[/img][/url][/center]"
    },
    "LST": {
            "api_key": "YOUR_API_KEY",
            "announce_url": "https://lst.gg/announce/YOUR_PASSKEY",
            "anon": False,
            "signature": "\n[center][b]PLEASE SEED LST FAMILY[/b][/center]",
            "anon_signature": "\n[center][url=...][img=40]...[/img][/url][/center]",
            "pr_signature": "\n [center][b][size=6]PERSONAL RELEASE[/size][/b][/center]",
            "anon_pr_signature": "\n[center][url=...][img=40]...[/img][/url][/center]"
    },
    "LT": {
            "api_key": "YOUR_API_KEY",
            "announce_url": "https://lat-team.com/announce/YOUR_PASSKEY",
            "anon": False,
            "signature": "\n[center][b]PLEASE SEED LAT-Team[/b][/center]",
            "anon_signature": "\n[center][url=...][img=40]...[/img][/url][/center]",
            "pr_signature": "\n [center][b][size=6]PERSONAL RELEASE[/size][/b][/center]",
            "anon_pr_signature": "\n[center][url=...][img=40]...[/img][/url][/center]"
    },
    "MANUAL": {
    },
    "MB": {
            "api_key": "YOUR_API_KEY",
            "announce_url": "https://malayabits.cc/announce/YOUR_PASSKEY",
            "anon": False,
            "signature": "\n[center][b]PLEASE SEED MalayaBits[/b][/center]",
            "anon_signature": "\n[center][url=...][img=40]...[/img][/url][/center]",
            "pr_signature": "\n [center][b][size=6]PERSONAL RELEASE[/size][/b][/center]",
            "anon_pr_signature": "\n[center][url=...][img=40]...[/img][/url][/center]"
    },
    "MILNU": {
            "api_key": "YOUR_API_KEY",
            "announce_url": "https://milnueve.neklair.es/announce/YOUR_PASSKEY",
            "anon": False,
            "signature": "\n[center][b]PLEASE SEED MILNUEVE FAMILY[/b][/center]",
            "anon_signature": "\n[center][url=...][img=40]...[/img][/url][/center]",
            "pr_signature": "\n [center][b][size=6]PERSONAL RELEASE[/size][/b][/center]",
            "anon_pr_signature": "\n[center][url=...][img=40]...[/img][/url][/center]"
    },
    "MTV": {
            "api_key": "Get_from_security_page",
            "username": "YOUR_USERNAME",
            "password": "YOUR_PASSWORD",
            "announce_url": "get from https://www.morethantv.me/upload.php",
            "anon": False
    },
    "NBL": {
            "api_key": "YOUR_API_KEY",
            "announce_url": "https://nebulance.io/YOUR_PASSKEY",
            "anon": False,
            "signature": "\n[center][b]PLEASE SEED Nebulance FAMILY[/b][/center]",
            "anon_signature": "\n[center][url=...][img=40]...[/img][/url][/center]",
            "pr_signature": "\n [center][b][size=6]PERSONAL RELEASE[/size][/b][/center]",
            "anon_pr_signature": "\n[center][url=...][img=40]...[/img][/url][/center]"
    },
    "OE": {
            "api_key": "YOUR_API_KEY",
            "announce_url": "https://onlyencodes.cc/announce/YOUR_PASSKEY",
            "anon": False,
            "signature": "\n[center][b]PLEASE SEED OnlyEncodes FAMILY[/b][/center]",
            "anon_signature": "\n[center][url=...][img=40]...[/img][/url][/center]",
            "pr_signature": "\n [center][b][size=6]PERSONAL RELEASE[/size][/b][/center]",
            "anon_pr_signature": "\n[center][url=...][img=40]...[/img][/url][/center]"
    },
    "OINK": {
            "api_key": "YOUR_API_KEY",
            "announce_url": "https://yoinked.org/announce/YOUR_PASSKEY",
            "anon": False,
            "signature": "\n[center][b]PLEASE SEED YOiNKED FAMILY[/b][/center]",
            "anon_signature": "\n[center][url=...][img=40]...[/img][/url][/center]",
            "pr_signature": "\n [center][b][size=6]PERSONAL RELEASE[/size][/b][/center]",
            "anon_pr_signature": "\n[center][url=...][img=40]...[/img][/url][/center]"
    },
    "OTW": {
            "api_key": "YOUR_API_KEY",
            "announce_url": "https://oldtoons.world/announce/YOUR_PASSKEY",
            "anon": False,
            "signature": "\n[center][b]PLEASE SEED OldToons FAMILY[/b][/center]",
            "anon_signature": "\n[center][url=...][img=40]...[/img][/url][/center]",
            "pr_signature": "\n [center]PERSONAL RELEASE[/center]",
            "anon_pr_signature": "\n[center][url=...][img=40]...[/img][/url][/center]"
    },
    "PSS": {
            "api_key": "YOUR_API_KEY",
            "announce_url": "https://privatesilverscreen.cc/announce/YOUR_PASSKEY",
            "anon": False,
            "signature": "\n[center][b]PLEASE SEED PrivateSilverScreen FAMILY[/b][/center]",
            "anon_signature": "\n[center][url=...][img=40]...[/img][/url][/center]",
            "pr_signature": "\n [center][b][size=6]PERSONAL RELEASE[/size][/b][/center]",
            "anon_pr_signature": "\n[center][url=...][img=40]...[/img][/url][/center]"
    },
    "PTER": {
            "passkey": "passkey",
            "img_rehost": False,
            "username": "",
            "password": "",
            "ptgen_api": "",
            "anon": False
    },
    "THR": {
            "username": "YOUR_USERNAME",
            "password": "YOUR_PASSWORD",
            "img_api": "YOUR_API_KEY",
            "announce_url": "http://www.torrenthr.org/announce.php?passkey=YOUR_PASSKEY",
            "pronfo_api_key": "YOUR_API_KEY",
            "pronfo_theme": "YOUR_THEME",
            "pronfo_rapi_id": "YOUR_API_ID",
            "anon": False
    },
    "TL": {
            "announce_key": "YOUR_ANNOUNCE_KEY"
    },
    "TLZ": {
            "api_key": "YOUR_API_KEY",
            "announce_url": "https://tlzdigital.com/announce/YOUR_PASSKEY",
            "anon": False,
            "signature": "\n[center][b]PLEASE SEED TLZ[/b][/center]",
            "anon_signature": "\n[center][url=...][img=40]...[/img][/url][/center]",
            "pr_signature": "\n [center][b][size=6]PERSONAL RELEASE[/size][/b][/center]",
            "anon_pr_signature": "\n[center][url=...][img=40]...[/img][/url][/center]"
    },
    "TOCA": {
            "api_key": "YOUR_API_KEY",
            "announce_url": "https://tocashare.com/announce/YOUR_PASSKEY",
            "anon": False,
            "signature": "\n[center][b]PLEASE SEED TOCA SHARE[/b][/center]",
            "anon_signature": "\n[center][size=6]we are anonymous[/size][/center]",
            "pr_signature": "\n [center][b][size=6]PERSONAL RELEASE[/size][/b][/center]",
            "anon_pr_signature": "\n[center][url=...][img=40]...[/img][/url][/center]"
    },
    "TTR": {
            "api_key": "YOUR_API_KEY",
            "announce_url": "https://torrenteros.org/announce/YOUR_PASSKEY",
            "anon": False,
            "signature": "\n[center][b]PLEASE SEED TorrentEros[/b][/center]",
            "anon_signature": "\n[center][size=6]we are anonymous[/size][/center]",
            "pr_signature": "\n [center][b][size=6]PERSONAL RELEASE[/size][/b][/center]",
            "anon_pr_signature": "\n[center][url=...][img=40]...[/img][/url][/center]"
    },
    "ULCX": {
            "api_key": "YOUR_API_KEY",
            "announce_url": "https://upload.cx/announce/YOUR_PASSKEY",
            "anon": False,
            "signature": "\n[center][b]PLEASE SEED ULCX FAMILY[/b][/center]",
            "anon_signature": "\n[center][url=...][img=40]...[/img][/url][/center]",
            "pr_signature": "\n [center][b][size=6]PERSONAL RELEASE[/size][/b][/center]",
            "anon_pr_signature": "\n[center][url=...][img=40]...[/img][/url][/center]"
    },
    "UTP": {
            "api_key": "YOUR_API_KEY",
            "announce_url": "https://utp.to/announce/YOUR_PASSKEY",
            "anon": False,
            "signature": "\n[center][b]PLEASE SEED UTP FAMILY[/b][/center]",
            "anon_signature": "\n[center][url=...][img=40]...[/img][/url][/center]",
            "pr_signature": "\n [center][b][size=6]PERSONAL RELEASE[/size][/b][/center]",
            "anon_pr_signature": "\n[center][url=...][img=40]...[/img][/url][/center]"
    },
    "YU": {
            "api_key": "YOUR_API_KEY",
            "announce_url": "https://yu-scene.net/announce/YOUR_PASSKEY",
            "anon": False,
            "signature": "\n[center][b]PLEASE SEED YU-SCENE FAMILY[/b][/center]",
            "anon_signature": "\n[center][url=...][img=40]...[/img][/url][/center]",
            "pr_signature": "\n [center][b][size=6]PERSONAL RELEASE[/size][/b][/center]",
            "anon_pr_signature": "\n[center][url=...][img=40]...[/img][/url][/center]"
    },
    "PRBLM" : {
            "api_key" : "YOUR_API_KEY",
            "announce_url" : "https://parabellumhd.cx/announce/YOUR_PASSKEY",
            "anon" : False,
            "signature": "\n[center][b]PLEASE SEED PARABELLUM FAMILY[/b][/center]",
            "anon_signature": "\n[center][url=...][img=40]...[/img][/url][/center]",
            "pr_signature": "\n [center][b][size=6]PERSONAL RELEASE[/size][/b][/center]",
            "anon_pr_signature": "\n[center][url=...][img=40]...[/img][/url][/center]"
    }
},

"TORRENT_CLIENTS": {
    "Client1": {
            "torrent_client": "qbit",
            "qbit_url": "http://127.0.0.1",
            "qbit_port": "8080",
            "qbit_user": "YOUR_USERNAME",
            "qbit_pass": "YOUR_PASSWORD"
    },
    "qbit": {
            "torrent_client": "qbit",
            "enable_search": True,
            "qbit_url": "http://127.0.0.1",
            "qbit_port": "8888",
            "qbit_user": "YOUR_USERNAME",
            "qbit_pass": "YOUR_PASSWORD",
            "torrent_storage_dir": "/app/temp/qbit_backup",
            "content_layout": "Original",
            "VERIFY_WEBUI_CERTIFICATE": False
    },
    "rtorrent": {
            "torrent_client": "rtorrent",
            "rtorrent_url": "https://YOUR_USER:YOUR_PASS@YOUR_HOST:443/YOUR_PATH/action.php"
    },
    "deluge": {
            "torrent_client": "deluge",
            "deluge_url": "localhost",
            "deluge_port": "8112",
            "deluge_user": "YOUR_USERNAME",
            "deluge_pass": "YOUR_PASSWORD"
    },
    "transmission": {
            "torrent_client": "transmission",
            "transmission_url": "http://localhost:9091",
            "transmission_user": "YOUR_USERNAME",
            "transmission_pass": "YOUR_PASSWORD",
            "torrent_storage_dir": "/app/temp/transmission_watch",
            "enable_search": True
    },
    "watch": {
            "torrent_client": "watch",
            "watch_folder": "/app/watch"
    }
},

"DISCORD": {
    "discord_bot_token": "YOUR_DISCORD_TOKEN",
    "discord_bot_description": "Upload Assistant",
    "command_prefix": "!",
    "discord_channel_id": "YOUR_CHANNEL_ID",
    "admin_id": "YOUR_USER_ID",
    "search_dir": "/app/downloads/",
    "discord_emojis": {
            "BLU": "💙",
            "BHD": "🎉",
            "AITHER": "🛫",
            "STC": "📺",
            "ACM": "🍙",
            "MANUAL": "📩",
            "UPLOAD": "✅",
            "CANCEL": "🚫"
    }
}
}
EOF
fi

# --- ARCHIVO mass_config.py (UNIT3D Orchestrator) ---
if [ ! -f "$CONFIG_DIR/mass_config.py" ]; then
cat <<'EOF' > "$CONFIG_DIR/mass_config.py"
# ==========================================
# ⚙️ UNIT3D MASS EDITION SUITE - CONFIG
# ==========================================

# 1. Credenciales y Tracker
BASE_URL = "https://tu-tracker.com"        # Ej: https://milnueve.neklair.es
USERNAME = "TU_USUARIO"                    # Para el Scraper
COOKIE_NAME = "laravel_session"            # O el nombre que use tu tracker
COOKIE_VALUE = "TU_COOKIE_AQUI"            # Pega aquí el churrete de la cookie

# 2. Rutas Locales (Dentro del Contenedor)
# Carpeta donde están los subdirectorios con los meta.json
TMP_ROOT = "/app/RawLoadrr/tmp" 

# 3. Textos a Reemplazar (Opcional)
MSG_VIEJO = "[center][b]MENSAJE ANTIGUO[/b][/center]"
MSG_NUEVO = "[center][b]🌱 ¡La magia del P2P eres tú! 🌱[/b][/center]"

BANNER_VIEJO = "[center][url=...][img=400]...[/img][/url][/center]"
BANNER_NUEVO = "[center][url=...][img=400]...[/img][/url][/center]"

# 4. Settings del Bot
DELAY_MIN = 4.5  # Segundos mínimos entre peticiones (Jitter)
DELAY_MAX = 7.5  # Segundos máximos
EOF
fi

# 5. Instalación de comandos globales
echo "Instalando alias en /usr/local/bin..."
echo "sudo docker exec -it singularity_core python3 singularity.py" | sudo tee /usr/local/bin/singularity > /dev/null
echo "sudo docker exec -it singularity_core /bin/bash" | sudo tee /usr/local/bin/singularity-shell > /dev/null
sudo chmod +x /usr/local/bin/singularity /usr/local/bin/singularity-shell

echo "--------------------------------------------------------"
echo "✅ Estructura creada con éxito."
echo "⚠️  ATENCIÓN: Antes de hacer 'docker compose up -d':"
echo "   Debes editar los archivos en la carpeta $CONFIG_DIR/"
echo "   con tus credenciales reales (API keys, Cookies, etc)."
echo "--------------------------------------------------------"
