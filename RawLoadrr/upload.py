import requests
from src.args import Args
from src.clients import Clients
from src.prep import Prep
from src.trackers.COMMON import COMMON
import json
from pathlib import Path
import asyncio
import os
import sys
import re
import platform
import multiprocessing
import logging
import shutil
import glob
import subprocess
import traceback
import time
import random
from packaging.version import Version
from src.console import console, log, set_log_level
from src.logger import set_debug_mode as set_upload_logger_debug_mode
from rich.markdown import Markdown
from rich.style import Style
from rich.prompt import Prompt, Confirm
from rich.text import Text
from rich.panel import Panel
from rich.table import Table
from rich.align import Align
from rich.rule import Rule
from rich.console import Group
from rich.progress import Progress, TimeRemainingColumn
from difflib import SequenceMatcher
import bencodepy as bencode
from urllib.parse import urlparse, parse_qs
import importlib

####################################
#######  Tracker List Here   #######
### Add below + api or http list ###
####################################
tracker_data = {
    'api': ['ACM', 'AITHER', 'ANT', 'BHD', 'BHDTV', 'BLU', 'CBR', 'EMU', 'FNP', 'HHD', 'HUNO', 'ITA', 'JPTV', 'LCD', 'LDU', 'LST', 'LT', 'MB', 'MILNU', 'NBL', 'OE', 'OINK', 'OTW', 'PSS', 'PTT', 'RF', 'R4E', 'RHD', 'RTF', 'SHRI', 'SN', 'SP', 'TLZ', 'TTR', 'TOCA', 'ULCX', 'UTP', 'YU', 'PRBLM'],
    'http': ['FL', 'HDB', 'HDT', 'MTV', 'PTER', 'TTG'],
    'other': ['AR', 'PTP', 'THR', 'TL']
 }

# Combine all trackers into one list
tracker_list = tracker_data['api'] + tracker_data['http'] + tracker_data['other']

# Import corresponding modules and create a dictionary mapping
tracker_class_map = {}
for tracker in tracker_list:
    try:
        tracker_class_map[tracker] = getattr(importlib.import_module(f"src.trackers.{tracker}"), tracker)
    except ImportError as e:
        logging.error(f"Error importing {tracker}: {e}")

# Detect python3 or fallback to default python command
python_cmd = shutil.which("python3") or "python"

base_dir = os.path.dirname(os.path.realpath(__file__))
data_dir = os.path.join(base_dir, 'data')
config_path = os.path.abspath(os.path.join(data_dir, 'config.py'))
old_config_path = os.path.abspath(os.path.join(data_dir, 'backup', 'old_config.py'))
minimum_version = Version('1.0.5')

def get_backup_name(path, suffix='_bu'):
    base, ext = os.path.splitext(path)
    counter = 1
    while os.path.exists(path):
        path = f"{base}{suffix}{counter}{ext}"
        counter += 1
    return path

if not os.path.exists(config_path):  
    console.print("[bold red] It appears you have no config file, please ensure to configure and place `/data/config.py`")
    exit()

try:
    from data.config import config 
except ImportError as e:
    console.print(f"[bold red]Error importing config: {str(e)}[/bold red]")
    exit()

def reconfigure():
    console.print("[bold red]WARN[/bold red]: Version out of date, automatic upgrade in progress")
    try:
        if os.path.exists(old_config_path):
            backup_name = get_backup_name(old_config_path)
            shutil.move(old_config_path, backup_name)
        shutil.move(config_path, old_config_path)
    except Exception as e:
        console.print("[bold red]ERROR[/bold red]: Unable to proceed with automatic upgrade. Please rename `config.py` to `old_config.py` move it to 'data/backup` and run `python3 data/reconfig.py`")
        console.print(f"Error: {str(e)}")
        exit()

    result = subprocess.run(
        [python_cmd, os.path.join(data_dir, "reconfig.py"), "--output-dir", data_dir],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        console.print(f"[bold red]Error during reconfiguration: {result.stderr}[/bold red]")
        exit()

    if os.path.exists(config_path):
        console.print("[bold green]Congratulations! config.py was successfully updated.[/bold green]")
    else:
        console.print("[bold][red]ERROR[/red]: config.py not found in the expected directory after reconfiguration.[/bold]")
        exit()

    console.print("Please double-check new config and ensure client settings were appropriately set.")
    console.print("[bold yellow]WARN[/bold yellow]: After verification of config, rerun command.")
    console.print("[dim green]Thanks for using Uploadrr :)")
    exit()

if 'version' not in config or Version(config.get('version')) < minimum_version:  # Check for version and reconfigures
    reconfigure()

try:
    from data.backup import example_config
    if 'version' in example_config.config and Version(example_config.config.get('version')) > Version(config.get('version')):
        console.print("[bold yellow]WARN[/bold yellow]: Config version out of date, updating is recommended.")
        console.print("[bold yellow]WARN[/bold yellow]: Simply pass --reconfig")
except Exception as e:
    console.print(f"[bold red]Error: {str(e)}[/bold red]")
    pass

# Initialize client and argument parser
try:
    client = Clients(config=config)
    parser = Args(config)
except Exception as e:
    console.print(f"[bold red]Error initializing client or parser: {e}[/bold red]")
    sys.exit(1)

def build_recursive_queue(root_path):
    """
    Recursively scans a directory to build a queue of items to upload.
    - Identifies TV Show seasons and adds them as season packs.
    - Identifies movie folders (with one video file) and adds the folder path.
    - Identifies loose movie files (multiple videos in a dir) and adds individual file paths.
    """
    queue = []
    video_extensions = ('.mkv', '.mp4', '.avi', '.ts', '.m2ts', '.m4v')
    season_patterns = [r'S[0-9]+', r'Season[\s-]*[0-9]+']
    
    processed_paths = set()

    for dirpath, dirnames, filenames in os.walk(root_path, topdown=True):
        if dirpath in processed_paths:
            dirnames.clear() # Prune this path
            continue

        dirnames[:] = [d for d in dirnames if 'trickplay' not in d.lower()]
        
        # Check if current dir is a season folder
        is_season_dir = any(re.search(p, os.path.basename(dirpath), re.IGNORECASE) for p in season_patterns)
        if is_season_dir:
            # It's a season pack, add the directory and don't go deeper
            queue.append(dirpath)
            processed_paths.add(dirpath) 
            dirnames.clear() 
            continue
        
        # Check if current dir is a show folder (contains season sub-folders)
        season_subdirs = [d for d in dirnames if any(re.search(p, d, re.IGNORECASE) for p in season_patterns)]
        if season_subdirs:
            # Add season folders to queue and mark them as processed
            for d in season_subdirs:
                season_path = os.path.join(dirpath, d)
                queue.append(season_path)
                processed_paths.add(season_path)
            # Prune season folders from future traversal from here
            dirnames[:] = [d for d in dirnames if d not in season_subdirs]
            # Continue to the next directory in the walk. We don't want to accidentally
            # process loose files in the same directory as season folders.
            continue

        # If not a season/show folder, check for movies or loose files
        video_files = [f for f in filenames if f.lower().endswith(video_extensions)]
        if video_files:
            if len(video_files) > 1:
                # This directory contains multiple videos. Treat them as loose files.
                for f in video_files:
                    queue.append(os.path.join(dirpath, f))
                # Don't clear dirnames, to allow traversal to other folders at this level
            else: # len(video_files) == 1
                # This directory contains a single video. Treat as a "Movie Folder".
                queue.append(dirpath)
                # Since this is a self-contained movie, don't descend into its subdirectories.
                processed_paths.add(dirpath)
                dirnames.clear()
                
    return sorted(list(set(queue)))


async def do_the_thing(base_dir):
    print_banner()
    meta = {'base_dir': base_dir}

    # Parse the command-line arguments and update meta
    meta, help, before_args = parser.parse(sys.argv[1:], meta)

    #LOG LEVEL
    set_log_level(debug=True) if meta.get('debug') else set_log_level(debug=False)
    set_log_level(ddebug=True) if meta.get('deep_debug') else set_log_level(ddebug=False)
    set_upload_logger_debug_mode(bool(meta.get('debug') or meta.get('deep_debug')))

    # If 'reconfig' is set in meta, run reconfigure()
    if meta.get("reconfig", False):
        reconfigure()

    # Clean up tmp directory if 'cleanup' flag is set
    if meta.get('cleanup', False):
        tmp_dir = f"{base_dir}/tmp"
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir)
            console.print("[bold green]Successfully emptied tmp directory")
        else:
            console.print("[bold yellow]tmp directory is already empty")

    
    # This is the new recursive queue building logic
    queue = []
    if meta.get('path'):
        root_path = os.path.abspath(meta['path'])
        if os.path.exists(root_path):
            if os.path.isdir(root_path):
                console.print(f"[bold green]Starting recursive scan on:[/bold green] [cyan]{root_path}[/cyan]")
                queue = build_recursive_queue(root_path)
            else: # It's a file
                queue.append(root_path)
        else:
            console.print(f"[red]Path: [bold red]{root_path}[/bold red] does not exist")
            exit(1)
    else:
        console.print("[red]No input path provided. Please specify a file or directory to process.[/red]")
        exit(0)

    if not queue:
        console.print("[yellow]No items found to process in the specified path.[/yellow]")
        exit(0)

    if meta.get('show_queue') or meta.get('debug'):
        md_text = "\n - ".join(queue)
        console.print("\n[bold green]Automatically queuing these files:[/bold green]", end='')
        console.print(Markdown(f"- {md_text.rstrip()}\n\n", style=Style(color='cyan')))
    
    console.print(f"\nUnique uploads queued: [bold cyan]{len(queue)}[/bold cyan]")


    delay = meta.get('delay', 0) or config['AUTO'].get('delay', 0)
    base_meta = {k: v for k, v in meta.items()}

    # Initialize counters
    total_files = len(queue)
    successful_uploads = 0
    skipped_files = 0
    skipped_details = []
    skipped_tmdb_files = []
    current_file = 1

    if meta.get('random'):
        random.shuffle(queue)
    elif meta.get('auto_queue'):
        queue = sorted(queue, key=str.lower)
    else:
        queue = queue

    for path in queue:
        meta = {k: v for k, v in base_meta.items()}
        meta['path'] = path
        meta['uuid'] = None # Ensure UUID is reset for each new item being processed
        try:
            with open(f"{base_dir}/tmp/{os.path.basename(path)}/meta.json", encoding='utf-8') as f:
                saved_meta = json.load(f)
                # If the path in the saved meta doesn't match the current path,
                # it means this meta.json is for a different item. Discard old media-specific data.
                if saved_meta.get('path') != path:
                    saved_meta.pop('mediainfo', None)
                    saved_meta.pop('bdinfo', None)
                    saved_meta.pop('filelist', None)
                    saved_meta.pop('user_images', None)
                    saved_meta.pop('name_notag', None)
                    saved_meta.pop('name', None)
                    saved_meta.pop('clean_name', None)
                    saved_meta.pop('potential_missing', None)
                    saved_meta.pop('tmdb', None) 
                    saved_meta.pop('imdb_id', None)
                    saved_meta.pop('uuid', None) # Force new UUID
                for key, value in saved_meta.items():
                    overwrite_list = [
                        'base_dir', 'path', 'trackers', 'dupe', 'debug', 'anon', 'category', 'type', 'screens', 'nohash', 'manual_edition', 'imdb', 'tmdb_manual', 'mbid_manual', 'mal', 'manual', 'manual_name', 
                        'hdb', 'ptp', 'blu', 'no_season', 'no_aka', 'no_year', 'no_dub', 'no_tag', 'no_seed', 'client', 'desclink', 'descfile', 'desc', 'draft', 'region', 'freeleech', 
                        'personalrelease', 'unattended', 'season', 'episode', 'torrent_creation', 'qbit_tag', 'qbit_cat', 'skip_imghost_upload', 'imghost', 'manual_source', 'webdv', 'hardcoded-subs'
                    ]
                    if meta.get(key, None) != value and key in overwrite_list:
                        saved_meta[key] = meta[key]
                meta = saved_meta
                f.close()
        except FileNotFoundError:
            pass
        
        console.print(Align.center(f"\n\n——— Processing # [bold bright_cyan]{current_file}[/bold bright_cyan] of [bold bright_magenta]{total_files}[/bold bright_magenta] ———"))
        if delay > 0:
            with Progress("[progress.description]{task.description}", TimeRemainingColumn(), transient=True) as progress:
                task = progress.add_task("[cyan]Auto delay...", total=delay)
                for i in range(delay):
                    await asyncio.sleep(1)
                    progress.update(task, advance=1)
        console.print(f"[green]Gathering info for {os.path.basename(path)}")
        if meta['imghost'] is None or meta['imghost'] == '':
            # Ensure a default is always set, even if config default is missing
            meta['imghost'] = config['DEFAULT'].get('img_host_1', 'imgbox')
        else:
            # Ensure it's a string, even if it came from meta.json as something else
            meta['imhost'] = str(meta['imghost'])
        if meta['unattended']:
            console.print("[yellow]Running in Auto Mode")
                
        current_file += 1
        prep = Prep(screens=meta.get('screens', 3), img_host=meta.get('imghost', 'imgbox'), config=config)
        meta = await prep.gather_prep(meta=meta, mode='cli')

        # Gather TMDb ID
        if meta.get('tmdb_not_found'):
            skipped_files += 1
            skipped_tmdb_files.append(path)
            continue

        try:
            meta['name_notag'], meta['name'], meta['clean_name'], meta['potential_missing'] = await prep.get_name(meta)
            if any(val is None for val in (meta['name_notag'], meta['name'], meta['clean_name'], meta['potential_missing'])):
                raise ValueError("Name values are None")
        except Exception as e:
            skipped_files += 1
            skipped_details.append((path, f'Error getting name: {str(e)}'))
            if meta['is_music']:
                log.error("get_name was called")            
            continue

        if meta.get('image_list', False) in (False, []) and meta.get('skip_imghost_upload', False) == False:
            return_dict = {}
            meta['image_list'], dummy_var = prep.upload_screens(meta, meta['screens'], 1, 0, meta['screens'],[], return_dict)
            if meta['debug']:
                console.print(meta['image_list'])
            # meta['uploaded_screens'] = True
        elif meta.get('skip_imghost_upload', False) and not meta.get('image_list', False):
            meta['image_list'] = []


        if not os.path.exists(os.path.abspath(f"{meta['base_dir']}/tmp/{meta['uuid']}/BASE.torrent")):
            reuse_torrent = None
            if not meta.get('rehash', False):
                reuse_torrent = await client.find_existing_torrent(meta)
                if reuse_torrent != None:
                    prep.create_base_from_existing_torrent(reuse_torrent, meta['base_dir'], meta['uuid'])
            if not meta['nohash'] and reuse_torrent is None:
                prep.create_torrent(meta, Path(meta['path']), "BASE", meta.get('piece_size_max', 0))
            if meta['nohash']:
                meta['client'] = "none"
        elif os.path.exists(os.path.abspath(f"{meta['base_dir']}/tmp/{meta['uuid']}/BASE.torrent")) and meta.get('rehash', False) is True and meta['nohash'] is False:
            prep.create_torrent(meta, Path(meta['path']), "BASE", meta.get('piece_size_max', 0))
        if int(meta.get('randomized', 0)) >= 1:
            prep.create_random_torrents(meta['base_dir'], meta['uuid'], meta['randomized'], meta['path'])
            
        if meta.get('trackers', None) != None:
            trackers = meta['trackers']
        else:
            trackers = config['TRACKERS']['default_trackers']
        if "," in trackers:
            trackers = trackers.split(',')
        with open (f"{meta['base_dir']}/tmp/{meta['uuid']}/meta.json", 'w', encoding='utf-8') as f:
            json.dump(meta, f, ensure_ascii=False, indent=4)
            f.close()
        confirm = get_confirmation(meta)  
        while not confirm:
            # help.print_help()
            if meta.get('is_music', False):
                console.print("Input args that need correction e.g.(--tag PMEDIA --mbid e7bb5806-36bb-45a7-b6ea-0b6de4eed94b)") 
            else:    
                console.print("Input args that need correction e.g.(--tag NTb --category tv --tmdb 12345)")  
            console.print("Enter 'skip' if no correction needed", style="dim")
            editargs = Prompt.ask("")
            if editargs.lower() == 'skip':
                break
            elif editargs == '':
                console.print("Invalid input. Please try again or type 'skip' to pass.", style="dim")
            else:
                editargs = (meta['path'],) + tuple(editargs.split())
                if meta['debug']:
                    editargs = editargs + ("--debug",)
                meta, help, before_args = parser.parse(editargs, meta)
                meta['edit'] = True
                meta = await prep.gather_prep(meta=meta, mode='cli') 
                meta['name_notag'], meta['name'], meta['clean_name'], meta['potential_missing'] = await prep.get_name(meta)
                confirm = get_confirmation(meta)
                if confirm:
                    break

        if not isinstance(trackers, list):
            trackers = [trackers]
        trackers = [s.strip().upper() for s in trackers]
        if meta.get('manual', False):
            trackers.insert(0, "MANUAL")

        console.print(f"Processing: [bold cyan]{path}[/bold cyan]")
        common = COMMON(config=config)
        for tracker in trackers:
            if meta['name'].endswith('DUPE?'):
                meta['name'] = meta['name'].replace(' DUPE?', '')
            tracker = tracker.replace(" ", "").upper().strip()
            
            if meta['debug']:
                debug = "(DEBUG)"
            else:
                debug = ""

            if tracker not in tracker_list:
                console.print(f"[bold red]Error:[/bold red] Tracker '{tracker}' not recognized or supported.")
                skipped_files += 1
                skipped_details.append((path, f"No such tracker: {tracker}"))
                continue

            if tracker in tracker_data['api']:
                tracker_class = tracker_class_map[tracker](config=config)
                # Auto-upload by default (unless debug mode without unattended flag)
                if meta.get('debug', False) and not meta.get('unattended', False):
                    upload_to_tracker = Confirm.ask(f"Upload to {tracker_class.tracker}? {debug}")
                else:
                    upload_to_tracker = True
                if upload_to_tracker:
                    console.print(f"Uploading to {tracker_class.tracker}")
                else:
                    upload_to_tracker = False
                    skipped_files += 1
                    skipped_details.append((path, f"User skipped Upload on {tracker_class.tracker}"))
                    continue
                if check_banned_group(tracker_class.tracker, tracker_class.banned_groups, meta, skipped_details, path):
                    skipped_files += 1
                    skipped_details.append((path, f"Banned Group on {tracker_class.tracker}"))
                    continue
                dupes = await tracker_class.search_existing(meta)
                if not meta.get('is_music', False):
                    dupes = await common.filter_dupes(dupes, meta)
                meta, skipped = dupe_check(dupes, meta, config, skipped_details, path)                    
                if skipped:
                    skipped_files += 1
                    skipped_details.append((path, f"Potential duplicate on {tracker_class.tracker}"))
                    continue                        
                if meta['upload']:
                    #await tracker_class.upload(meta)    
                    upload_success = await tracker_class.upload(meta)
                    if upload_success:
                        # tracker_class.logger.info("DEBUG: Inside upload_success block, checking for MILNU tracker")
                        # tracker_class.logger.info(f"DEBUG_MILNU_VAR: Current tracker variable value: '{tracker}'")
                        # tracker_class.logger.info(f"DEBUG_MILNU_VAR: Comparison 'MILNU' == tracker: {'MILNU' == tracker}")
                                                    # # console.print("DEBUG_UNCONDITIONAL: Entered MILNU download block. (Direct print)") # NEW LINE ADDED
                        # tracker_class.logger.info(f"DEBUG_UPLOAD_SUCCESS: Value of upload_success: {upload_success}")
                        # tracker_class.logger.info(f"DEBUG_UPLOAD_SUCCESS: Type of upload_success: {type(upload_success)}")
                        # tracker_class.logger.info(f"DEBUG_UPLOAD_SUCCESS: isinstance(upload_success, dict): {isinstance(upload_success, dict)}")
                        # LÓGICA ESPECÍFICA PARA MILNU (UNIT3D)
                        if tracker in tracker_data['api'] and isinstance(upload_success, dict):
                            # The 'data' field directly contains the download URL
                            download_url_from_tracker = upload_success.get('data')
                            
                            if download_url_from_tracker and download_url_from_tracker.startswith('http'):
                                console.print(f"[bold yellow]Download URL Detectado: {download_url_from_tracker}. Descargando versión oficial del tracker...")
                                tracker_class.logger.info(f"Downloading regenerated torrent from: {download_url_from_tracker}")
                                
                                # Ruta del archivo torrent local que vamos a sobreescritura
                                torrent_path_to_overwrite = f"{meta['base_dir']}/tmp/{meta['uuid']}/[{tracker}]{meta['clean_name']}.torrent"
                                
                                # Descarga y sobreescritura automática
                                try:
                                    r = requests.get(download_url_from_tracker, timeout=30)
                                    if r.status_code == 200:
                                        with open(torrent_path_to_overwrite, 'wb') as f:
                                            f.write(r.content)
                                        console.print("[bold green]Torrent local actualizado con éxito (Entropy inyectado).")
                                        tracker_class.logger.info(f"Successfully downloaded and updated local torrent at: {torrent_path_to_overwrite}")
                                    else:
                                        console.print(f"[bold red]Error al descargar el torrent oficial (HTTP {r.status_code}).")
                                        tracker_class.logger.error(f"Error downloading torrent: HTTP {r.status_code} - {r.text}")
                                except Exception as e:
                                    console.print(f"[bold red]Fallo en la conexión de descarga: {e}")
                                    tracker_class.logger.error(f"Failed to download torrent: {str(e)}")
                            else:
                                console.print("[bold red]No download URL found in tracker response.")
                                tracker_class.logger.error("No download URL found in tracker response.")
                        # End MILNU specific logic
                        
                        if tracker == 'SN':
                            await asyncio.sleep(16)
                        await client.add_to_client(meta, tracker_class.tracker)
                        successful_uploads += 1
                    else:
                        skipped_files += 1
                        if meta['debug']:
                            skipped_details.append((path, f"{tracker_class.tracker} (DEBUG MODE)"))
                        else:
                            skipped_details.append((path, f"{tracker_class.tracker} Rejected Upload"))
            
            if tracker in tracker_data['http']:
                tracker_class = tracker_class_map[tracker](config=config)
                # Auto-upload by default (unless debug mode without unattended flag)
                if meta.get('debug', False) and not meta.get('unattended', False):
                    upload_to_tracker = Confirm.ask(f"Upload to {tracker_class.tracker}? {debug}", choices=["y", "N"])
                else:
                    upload_to_tracker = True
                if upload_to_tracker:
                    console.print(f"Uploading to {tracker}")
                    if check_banned_group(tracker_class.tracker, tracker_class.banned_groups, meta, skipped_details, path):
                        skipped_files += 1
                        skipped_details.append((path, f"Banned group on {tracker_class.tracker}"))                        
                        continue
                    if await tracker_class.validate_credentials(meta):
                        dupes = await tracker_class.search_existing(meta)
                        dupes = await common.filter_dupes(dupes, meta)
                        meta, skipped = dupe_check(dupes, meta, config, skipped_details, path)
                        if skipped:
                            skipped_files += 1
                            skipped_details.append((path, tracker))
                            continue
                        if upload_success:
                            await tracker_class.upload(meta)
                            await client.add_to_client(meta, tracker_class.tracker)
                            successful_uploads += 1

            if tracker == "MANUAL":
                if meta['unattended']:
                    do_manual = True
                else:
                    do_manual = Confirm.ask("Get files for manual upload?", default=True)
                if do_manual:
                    for manual_tracker in trackers:
                        if manual_tracker != 'MANUAL':
                            manual_tracker = manual_tracker.replace(" ", "").upper().strip()
                            tracker_class = tracker_class_map[manual_tracker](config=config)
                            if manual_tracker in tracker_data['api']:
                                await common.unit3d_edit_desc(meta, tracker_class.tracker, tracker_class.signature)
                            else:
                                await tracker_class.edit_desc(meta)
                    url = await prep.package(meta)
                    if not url:
                        console.print(f"[yellow]Unable to upload prep files, they can be found at `tmp/{meta['uuid']}")
                    else:
                        console.print(f"[green]{meta['name']}")
                        console.print(f"[green]Files can be found at: [yellow]{url}[/yellow]")  

            ar = None
            if tracker == "AR":
                ar = tracker_class_map[tracker](config=config)
                # Auto-upload by default (unless debug mode without unattended flag)
                if meta.get('debug', False) and not meta.get('unattended', False):
                    upload_to_ar = Confirm.ask(f"Upload to AlphaRatio? {debug}", choices=["y", "N"])
                else:
                    upload_to_ar = True
                if upload_to_ar:
                    console.print("Uploading to AlphaRatio")               
                    if check_banned_group(tracker, ar.banned_groups, meta, skipped_details, path):
                        skipped_files += 1
                        skipped_details.append((path, f"Banned group on {tracker_class.tracker}"))                
                        continue
                console.print("[yellow]Searching for Existing Releases")
                if await ar.validate_credentials(meta):
                    dupes = await ar.search_existing(meta)
                    dupes = await common.filter_dupes(dupes, meta)
                    meta, skipped = dupe_check(dupes, meta, config, skipped_details, path)
                    if skipped:
                        skipped_files += 1
                        skipped_details.append((path, tracker))
                        continue
                if meta['upload']:
                    await ar.upload(meta)
                    #await ar.update_torrent_file
                    await asyncio.sleep(5)
                    await client.add_to_client(meta, "AR")
                    successful_uploads += 1
            if ar is not None:
                await ar.close_session()
                    
            if tracker == "BHD":
                bhd = tracker_class_map[tracker](config=config)
                draft_int = await bhd.get_live(meta)
                draft = "Draft" if draft_int == 0 else "Live"
                # Auto-upload by default (unless debug mode without unattended flag)
                if meta.get('debug', False) and not meta.get('unattended', False):
                    upload_to_bhd = Confirm.ask(f"Upload to BHD? ({draft}) {debug}")
                else:
                    upload_to_bhd = True
                if upload_to_bhd:
                    console.print("Uploading to BHD")
                    if check_banned_group("BHD", bhd.banned_groups, meta, skipped_details, path):
                        skipped_files += 1
                        skipped_details.append((path, f"Banned group on {tracker_class.tracker}")) 
                        continue
                    dupes = await bhd.search_existing(meta)
                    dupes = await common.filter_dupes(dupes, meta)
                    meta, skipped = dupe_check(dupes, meta, config, skipped_details, path)
                    if skipped:
                        skipped_files += 1
                        skipped_details.append((path, tracker))
                        continue
                    if meta['upload']:
                        await bhd.upload(meta)
                        await client.add_to_client(meta, "BHD")
                        successful_uploads += 1
            
            if tracker == "THR":
                # Auto-upload by default (unless debug mode without unattended flag)
                if meta.get('debug', False) and not meta.get('unattended', False):
                    upload_to_thr = Confirm.ask(f"Upload to THR? {debug}")
                else:
                    upload_to_thr = True
                if upload_to_thr:
                    console.print("Uploading to THR")
                    def is_valid_imdb_id(imdb_id):
                        return re.match(r'tt\d{7}', imdb_id) is not None
                    if meta.get('imdb_id', '0') == '0':
                        while True:
                            imdb_id = Prompt.ask("Please enter a valid IMDB id (e.g., tt1234567)")
                            if is_valid_imdb_id(imdb_id):
                                meta['imdb_id'] = imdb_id.replace('tt', '').zfill(7)
                                break
                            else:
                                print("Invalid IMDB id. Please try again.")
                    def get_youtube_id(url):
                        parsed_url = urlparse(url)
                        if "youtube.com" in parsed_url.netloc:
                            if "watch" in parsed_url.path:
                                video_id = parse_qs(parsed_url.query).get('v', None)
                                if video_id:
                                    return video_id[0]
                        return None

                    if meta.get('youtube', None) is None:
                        while True:
                            youtube = Prompt.ask("Unable to find youtube trailer, please link one\n[dim] e.g.(https://www.youtube.com/watch?v=dQw4w9WgXcQ or dQw4w9WgXcQ)[/dim]")
                            video_id = get_youtube_id(youtube)
                            if video_id is not None:
                                meta['youtube'] = video_id
                                break
                            else:
                                print("Invalid YouTube URL or ID. Please enter a valid full URL.")
                    thr = tracker_class_map[tracker](config=config)
                    try:
                        with requests.Session() as session:
                            console.print("[yellow]Logging in to THR")
                            session = thr.login(session)
                            console.print("[yellow]Searching for Dupes")
                            dupes = thr.search_existing(session, meta.get('imdb_id'))
                            dupes = await common.filter_dupes(dupes, meta)
                            meta, skipped = dupe_check(dupes, meta)
                            if skipped:
                                skipped_files += 1
                                skipped_details.append((path, tracker))
                                continue
                            if meta['upload']:
                                await thr.upload(session, meta)
                                await client.add_to_client(meta, "THR")
                                successful_uploads += 1
                    except:
                        console.print(traceback.print_exc())

            if tracker == "PTP":
                # Auto-upload by default (unless debug mode without unattended flag)
                if meta.get('debug', False) and not meta.get('unattended', False):
                    upload_to_ptp = Confirm.ask(f"Upload to {tracker}? {debug}")
                else:
                    upload_to_ptp = True
                if upload_to_ptp:
                    console.print(f"Uploading to {tracker}")
                    def is_valid_imdb_id(imdb_id):
                        return re.match(r'tt\d{7}', imdb_id) is not None
                    if meta.get('imdb_id', '0') == '0':
                        while True:
                            imdb_id = Prompt.ask("Please enter a valid IMDB id (e.g., tt1234567)")
                            if is_valid_imdb_id(imdb_id):
                                meta['imdb_id'] = imdb_id.replace('tt', '').zfill(7)
                                break
                            else:
                                print("Invalid IMDB id. Please try again.")
                    ptp = tracker_class_map[tracker](config=config)
                    if check_banned_group(tracker_class.tracker, tracker_class.banned_groups, meta, skipped_details, path):
                        skipped_files += 1
                        skipped_details.append((path, f"Banned group on {tracker_class.tracker}"))                                          
                        continue
                    try:
                        console.print("[yellow]Searching for Group ID")
                        groupID = await ptp.get_group_by_imdb(meta['imdb_id'])
                        if groupID is None:
                            console.print("[yellow]No Existing Group found")
                            def get_youtube_id(url):
                                parsed_url = urlparse(url)
                                if "youtube.com" in parsed_url.netloc:
                                    if "watch" in parsed_url.path:
                                        video_id = parse_qs(parsed_url.query).get('v', None)
                                        if video_id:
                                            return video_id[0]
                                return None

                            if meta.get('youtube', None) is None:
                                while True:
                                    youtube = Prompt.ask("Unable to find youtube trailer, please link one\n[dim] e.g.(https://www.youtube.com/watch?v=dQw4w9WgXcQ or dQw4w9WgXcQ)[/dim]")
                                    video_id = get_youtube_id(youtube)
                                    if video_id is not None:
                                        meta['youtube'] = video_id
                                        break
                                    else:
                                        print("Invalid YouTube URL or ID. Please enter a valid full URL.")
                            meta['upload'] = True
                        else:
                            console.print("[yellow]Searching for Existing Releases")
                            dupes = await ptp.search_existing(groupID, meta)
                            dupes = await common.filter_dupes(dupes, meta)
                            meta, skipped = dupe_check(dupes, meta)
                            if skipped:
                                skipped_files += 1
                                skipped_details.append((path, tracker))
                                continue
                        if meta.get('imdb_info', {}) == {}:
                            meta['imdb_info'] = await prep.get_imdb_info(meta['imdb_id'], meta)
                        if meta['upload']:
                            ptpUrl, ptpData = await ptp.fill_upload_form(groupID, meta)
                            await ptp.upload(meta, ptpUrl, ptpData)
                            await asyncio.sleep(5)
                            await client.add_to_client(meta, "PTP")
                            successful_uploads += 1
                    except:
                        console.print(traceback.print_exc())

            if tracker == "TL":
                tracker_class = tracker_class_map[tracker](config=config)
                # Auto-upload by default (unless debug mode without unattended flag)
                if meta.get('debug', False) and not meta.get('unattended', False):
                    upload_to_tracker = Confirm.ask(f"Upload to {tracker_class.tracker}? {debug}")
                else:
                    upload_to_tracker = True
                if upload_to_tracker:
                    console.print(f"Uploading to {tracker_class.tracker}")
                    if check_banned_group(tracker_class.tracker, tracker_class.banned_groups, meta, skipped_details, path):
                        skipped_files += 1
                        skipped_details.append((path, f"Banned group on {tracker_class.tracker}"))  
                        continue
                    await tracker_class.upload(meta)
                    await client.add_to_client(meta, tracker_class.tracker)
                    successful_uploads += 1            

    ### FEEDBACK ###

    def format_path_with_files(path, files):
        formatted_text = Text()
        formatted_text.append("Path: ")
        formatted_text.append(f"{path}", style="bold")  # Removed the newline here
        for i, file in enumerate(files):
            file_name = os.path.basename(file)
            # Add a newline before each file, but not before the first one
            #if i != 0:
            formatted_text.append("\n")
            formatted_text.append(f"• {file_name}") 
        return formatted_text

    if total_files > 0:
        console.print()
        console.print(Panel(
            f"Processed [bold bright_magenta]{total_files}[/bold bright_magenta] Unique Uploads\n"
            f"Successful Uploads: [bold green]{successful_uploads}[/bold green]\n"
            f"Failed Uploads: [bold red]{skipped_files}[/bold red]",
            title="Upload Summary",
            border_style="bold cyan"
        ))

    # Handle skipped files
    if skipped_files > 0:
        tracker_skip_map = {}
        for detail in skipped_details:
            if len(detail) == 2:
                file, reason = detail
                tracker = "Unknown Tracker"
            else:
                file, reason, tracker = detail
            if reason not in tracker_skip_map:
                tracker_skip_map[reason] = []
            tracker_skip_map[reason].append((file, tracker))

        for reason, files in tracker_skip_map.items():
            reason_text = f"{reason}"
            reason_style = "bold red" if "banned" in reason.lower() or "rejected" in reason.lower() or "no such tracker" in reason.lower() else "bold yellow"
            
            path_file_map = {}
            for file, _ in files:
                path = os.path.dirname(file) + os.sep  
                if path not in path_file_map:
                    path_file_map[path] = []
                path_file_map[path].append(file)

            combined_renderable = []
            for i, (path, files) in enumerate(path_file_map.items()):
                if i != 0:
                    combined_renderable.append(Text())
                formatted_text = format_path_with_files(path, files)
                combined_renderable.append(formatted_text)


            if 'duplicate' in reason.lower():
                combined_renderable.append(Text("\nTip: If 100% sure not a dupe pass with --skip-dupe-check", style="dim"))

            reason_panel = Panel(
                renderable=Group(*combined_renderable),
                title=reason_text,
                border_style=reason_style
            )

            console.print(reason_panel)

    # Handle skipped TMDB files
    if skipped_tmdb_files:
        path_file_map = {}
        for file in skipped_tmdb_files:
            path = os.path.dirname(file) + os.sep
            if path not in path_file_map:
                path_file_map[path] = []
            path_file_map[path].append(file)
        
        combined_renderable = []
        for i, (path, files) in enumerate(path_file_map.items()):
            if i != 0:
                combined_renderable.append(Text())
            formatted_text = format_path_with_files(path, files)
            combined_renderable.append(formatted_text)

        combined_renderable.append(Text("\nTip: Pass individually with --tmdb #####", style="dim"))

        reason_panel = Panel(
            renderable=Group(*combined_renderable),
            title="TMDb ID not found",
            border_style="bold red"
        )

        console.print(reason_panel)

def get_confirmation(meta):
    ddebug = meta.get('deep_debug')
    if meta['debug'] or ddebug:
        console.print("[bold red]DEBUG: True")
    console.print(f"Prep material saved to {meta['base_dir']}/tmp/{meta['uuid']}")
    console.print()

    if meta['is_music']:
        db_info = [
            f"[bold]Album[/bold]: {meta['album']} ({meta['year']})",
            f"[bold]Artist[/bold]: {meta['artist']}",
            f"[bold]Category[/bold]: {meta['category']}",
        ]
        if meta.get('mbid'):
            db_info.append(f"\n[bold]MBID[/bold]: https://musicbrainz.org/release/{meta['mbid']}")
        if meta.get('discogs_url'):
            db_info.append(f"[bold]Discogs[/bold]: {meta['discogs_url']}")
    else: 
        db_info = [
            f"[bold]Title[/bold]: {meta['title']} ({meta['year']})\n",
            f"[bold]Overview[/bold]: {meta['overview']}\n",
            f"[bold]Category[/bold]: {meta['category']}\n",
        ]

    if int(meta.get('tmdb', 0)) != 0:
        db_info.append(f"TMDB: https://www.themoviedb.org/{meta['category'].lower()}/{meta['tmdb']}")
    if int(meta.get('imdb_id', '0')) != 0:
        db_info.append(f"IMDB: https://www.imdb.com/title/tt{meta['imdb_id']}")
    if int(meta.get('tvdb_id', '0')) != 0:
        db_info.append(f"TVDB: https://www.thetvdb.com/?id={meta['tvdb_id']}&tab=series")
    if int(meta.get('mal_id', 0)) != 0:
        db_info.append(f"MAL : https://myanimelist.net/anime/{meta['mal_id']}")

    console.print(Panel("\n".join(db_info), title="Database Info", border_style="bold yellow"))
    console.print()
    if int(meta.get('freeleech', '0')) != 0:
        console.print(f"[bold]Freeleech[/bold]: {meta['freeleech']}")
    if meta['tag'] == "":
            tag = ""
    else:
        tag = f" / {meta['tag'][1:]}"
    if meta['is_disc'] == "DVD":
        res = meta['source']
    else:
        res = meta['resolution']

    console.print(Text(f" {res} / {meta['type']}{tag}", style="bold"))
    if meta.get('personalrelease', False):
        console.print("[bright_magenta]Personal Release!")
    console.print()
    
    # Auto-proceed by default (unless debug mode is on and unattended is explicitly false)
    # User can use --debug to get confirmation prompts
    if meta.get('debug', False) and not meta.get('unattended', False):
        get_missing(meta)
        ring_the_bell = "\a" if config['DEFAULT'].get("sfx_on_prompt", True) is True else "" # \a rings the bell
        console.print(f"[bold yellow]Is this correct?{ring_the_bell}") 
        console.print(f"[bold]Name[/bold]: {meta['name']}")
        confirm = Confirm.ask(" Correct?")
    else:
        console.print(f"[bold]Name[/bold]: {meta['name']}")
        confirm = True
    return confirm

def dupe_check(dupes, meta, config, skipped_details, path):
    if meta.get('dupe', False):
        console.print("[yellow]Skipping duplicate check as requested.")
        meta['upload'] = True   
        return meta, False  # False indicates not skipped
    
    if not dupes:
        console.print("[green]No dupes found")
        meta['upload'] = True   
        return meta, False  # False indicates not skipped

    table = Table(
        title="Are these dupes?",
        title_justify="center",
        show_header=True,
        header_style="bold underline",
        expand=True,
        show_lines=False,
        box=None
    )

    table.add_column("Name")
    table.add_column("Size", justify="center")

    for name, size in dupes.items():
        try:
            if "GB" in str(size).upper():
                size_gb = str(size).upper()
            else:
                size = int(size)
                if size > 0:
                    size_gb = str(round(size / (1024 ** 3), 2)) + " GB"  # Convert size to GB
                else:
                    size_gb = "N/A"
        except ValueError:
            size_gb = "N/A"
        table.add_row(name, f"[magenta]{size_gb}[/magenta]")

    console.print()
    console.print(table)
    console.print()

    def preprocess_string(text):
        text = re.sub(r'\[[a-z]{3}\]', '', text, flags=re.IGNORECASE)
        text = re.sub(r'[^\w\s]', '', text)
        text = text.lower()
        return text

    def handle_similarity(similarity, meta):
        if similarity == 1.0:
            console.info(f"[red]Found exact name match. Aborting..")
            meta['upload'] = False
            return meta, True  # True indicates skipped
        elif meta['unattended']:
            console.print(f"[red]Found potential dupe with {similarity * 100:.2f}% similarity. Aborting.")
            meta['upload'] = False
            return meta, True  # True indicates skipped
        else:
            upload = Confirm.ask(" Upload Anyways?")
            if not upload:
                meta['upload'] = False
                return meta, True  # True indicates skipped
        return meta, False  # False indicates not skipped

    similarity_threshold = max(config['AUTO'].get('dupe_similarity', 90.00) / 100, 0.70)
    console.print(f"Similarity: [red]{similarity_threshold}")
    size_tolerance = max(min(config['AUTO'].get('size_tolerance', 1 if meta['unattended'] else 30), 100), 1) / 100
    console.print(f"Size Tolerance: [red]{size_tolerance}")
    cleaned_meta_name = preprocess_string(meta['clean_name'])

    for name, size in dupes.items():
        if isinstance(size, str) and "GB" in size:
            size = float(size.replace(" GB", "")) * (1024 ** 3)  # Convert GB to bytes
        elif isinstance(size, (int, float)) and size != 0:
            size = int(size)
        else:
            console.print(f"Skipping invalid size for {name}: {size}")
            continue  # Skip to the next iteration if size is invalid

        meta_size = meta.get('content_size')
        if meta_size is None:
            meta_size = extract_size_from_torrent(meta['base_dir'], meta['uuid'])

        log.dinfo(f"Comparing {name} with size {size} bytes to {meta['clean_name']} with size {meta_size} bytes")

        # Define a maximum size tolerance to catch abnormally huge differences
        max_tolerance = config['AUTO'].get('max_size_tolerance', 25) / 100  # Default to 25%

        if meta_size == size:
            # Exact size match
            console.print(f"[red]Exact size match. [dim](byte-for-byte)[/dim] Aborting..")
            cleaned_dupe_name = preprocess_string(name)
            # similarity = SequenceMatcher(None, cleaned_meta_name, cleaned_dupe_name).ratio()
            return meta, True #Skip Upload

        elif abs(meta_size - size) > max_tolerance * meta_size:
            # Abnormally huge size difference
            log.dinfo("Size difference exceeds max tolerance (%.2f%%): %d bytes.", max_tolerance * 100, abs(meta_size - size))

        elif abs(meta_size - size) <= size_tolerance * meta_size:
            # Size is within reasonable tolerance
            log.dinfo(f"Size difference within tolerance: {abs(meta_size - size)} bytes.")
            cleaned_dupe_name = preprocess_string(name)
            similarity = SequenceMatcher(None, cleaned_meta_name, cleaned_dupe_name).ratio()

            if similarity >= similarity_threshold:
                log.dinfo(f"[yellow]Close size match ({abs(meta_size - size)} bytes difference) with {similarity * 100:.2f}% name similarity.")
                upload = Confirm.ask(" Upload anyways?")
                if not upload:
                    meta['upload'] = False
                    return meta, True #Skip Upload
            else:
                log.dinfo(f"[green]Close size match, but low name similarity ({similarity * 100:.2f}%). Proceeding.")

        else:
            # Size difference exceeds regular tolerance but is not abnormally large
            log.dinfo(f"Size difference exceeds regular tolerance but within max tolerance: {abs(meta_size - size)} bytes.")
            cleaned_dupe_name = preprocess_string(name)
            similarity = SequenceMatcher(None, cleaned_meta_name, cleaned_dupe_name).ratio()

            if similarity >= similarity_threshold:
                log.dinfo(f"[yellow]Large size difference but high name similarity ({similarity * 100:.2f}%). Treating as potential dupe.")
                upload = Confirm.ask(" Upload anyways?")
                if not upload:
                    meta['upload'] = False
                    return meta, True #Skip Upload
            else:
                console.print(f"[green]Large size difference and low name similarity ({similarity * 100:.2f}%). Proceeding.")
    # If no matches found
    console.print("[yellow]No dupes found above the similarity threshold. Uploading anyways.")
    meta['upload'] = True
    return meta, False  # Proceed with upload


def extract_size_from_torrent(base_dir, uuid):
    torrent_path = f"{base_dir}/tmp/{uuid}/BASE.torrent"
    with open(torrent_path, 'rb') as f:
        torrent_data = bencode.decode(f.read())
    
    info = torrent_data[b'info']
    if b'files' in info:
        # Multi-file torrent
        return sum(file[b'length'] for file in info[b'files'])
    else:
        # Single-file torrent
        return info[b'length']


# Return True if banned group
def check_banned_group(tracker, banned_group_list, meta, skipped_details, path):
    if meta['tag'] == "":
        return False
    else:
        q = False
        for tag in banned_group_list:
            if isinstance(tag, list):
                if meta['tag'][1:].lower() == tag[0].lower():
                    console.print(f"[bold yellow]{meta['tag'][1:]}[/bold yellow][bold red] was found on [bold yellow]{tracker}'s[/bold yellow] list of banned groups.")
                    console.print(f"[bold red]NOTE: [bold yellow]{tag[1]}")
                    q = True
            else:
                if meta['tag'][1:].lower() == tag.lower():
                    console.print(f"[bold yellow]{meta['tag'][1:]}[/bold yellow][bold red] was found on [bold yellow]{tracker}'s[/bold yellow] list of banned groups.")
                    q = True
        if q:
            if meta.get('unattended', False) or not Confirm.ask("[bold red] Upload Anyways?"):
                return True
    return False

def get_missing(meta):
    info_notes = {
        'edition' : 'Special Edition/Release',
        'description' : "Please include Remux/Encode Notes if possible (either here or edit your upload)",
        'service' : "WEB Service e.g.(AMZN, NF)",
        'region' : "Disc Region",
        'imdb' : 'IMDb ID (tt1234567)',
        'distributor' : "Disc Distributor e.g.(BFI, Criterion, etc)"
    }
    missing = []
    if meta.get('imdb_id', '0') == '0':
        meta['imdb_id'] = '0'
        meta['potential_missing'].append('imdb_id')
    if len(meta['potential_missing']) > 0:
        for each in meta['potential_missing']:
            if str(meta.get(each, '')).replace(' ', '') in ["", "None", "0"]:
                if each == "imdb_id":
                    each = 'imdb' 
                missing.append(f"--{each} | {info_notes.get(each)}")
    if missing != []:
        console.print(Rule("Potentially missing information", style="bold yellow"))
        for each in missing:
            if each.split('|')[0].replace('--', '').strip() in ["imdb"]:
                console.print(Text(each, style="bold red"))
            else:
                console.print(each)

    console.print()
    return

def print_banner():
    ascii_art = r"""
__________    _____  __      __.__                    .___              
\______   \  /  _  \/  \    /  \  |   _________     __| _/_____________ 
 |       _/ /  /_\  \   \/\/   /  |  /  _ \__  \   / __ |\_  __ \_  __ \
 |    |   \/    |    \        /|  |_(  <_> ) __ \_/ /_/ | |  | \/|  | \/
 |____|_  /\____|__  /\__/\  / |____/\____(____  /\____ | |__|   |__|   
        \/         \/      \/                  \/      \/               ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀

└─────────────────── Uploadrr ─────────── LDU ─x─ RAW ────────────────────┘
    """
    console.print(Align.center(Text(f"\n\n{ascii_art}\n", style='bold')))

def list_directory(directory):
    items = []
    for file in os.listdir(directory):
        if not file.startswith('.'):
            items.append(os.path.abspath(os.path.join(directory, file)))
    return items


if __name__ == '__main__':
    pyver = platform.python_version_tuple()
    if int(pyver[0]) != 3:
        console.print("[bold red]Python2 Detected, please use python3")
        exit()
    else:
        if int(pyver[1]) <= 6:
            console.print("[bold red]Python <= 3.6 Detected, please use Python >=3.7")
            loop = asyncio.get_event_loop()
            loop.run_until_complete(do_the_thing(base_dir))
        else:
            asyncio.run(do_the_thing(base_dir))