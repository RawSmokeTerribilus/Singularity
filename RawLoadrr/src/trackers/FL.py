import requests
import asyncio
import re
import os
from pathlib import Path
import json
import glob
import pickle
from unidecode import unidecode
from urllib.parse import urlparse, quote
from rich.prompt import Prompt, Confirm
from bs4 import BeautifulSoup

from src.trackers.COMMON import COMMON
from src.exceptions import *
from src.console import console

class FL():

    def __init__(self, config):
        self.config = config
        self.tracker = 'FL'
        self.source_flag = 'FL'
        self.signature = None
        self.username = config['TRACKERS'][self.tracker].get('username', '').strip()
        self.password = config['TRACKERS'][self.tracker].get('password', '').strip()
        self.fltools = config['TRACKERS'][self.tracker].get('fltools', {})
        self.uploader_name = config['TRACKERS'][self.tracker].get('uploader_name')
        self.banned_groups = [""]
    

    async def get_category_id(self, meta):
        has_ro_audio, has_ro_sub = await self.get_ro_tracks(meta)
        # 25 = 3D Movie
        if meta['category'] == 'MOVIE':
            # 4 = Movie HD
            cat_id = 4
            if meta['is_disc'] == "BDMV" or meta['type'] == "REMUX":
                # 20 = BluRay
                cat_id = 20
                if meta['resolution'] == '2160p':
                    # 26 = 4k Movie - BluRay
                    cat_id = 26
            elif meta['resolution'] == '2160p':
                # 6 = 4k Movie
                cat_id = 6
            elif meta.get('sd', 0) == 1:
                # 1 = Movie SD
                cat_id = 1
            if has_ro_sub and meta.get('sd', 0) == 0 and meta['resolution'] != '2160p':
                # 19 = Movie + RO
                cat_id = 19
        
        if meta['category'] == 'TV':
            # 21 = TV HD
            cat_id = 21
            if meta['resolution'] == '2160p':
                # 27 = TV 4k
                cat_id = 27
            elif meta.get('sd', 0) == 1:
                # 23 = TV SD
                cat_id = 23
            
        if meta['is_disc'] == "DVD":
            # 2 = DVD
            cat_id = 2
            if has_ro_sub:
                # 3 = DVD + RO 
                cat_id = 3

        if meta.get('anime', False):
            # 24 = Anime
            cat_id = 24
        return cat_id

    async def edit_name(self, meta):
        fl_name = meta['name']
        if 'DV' in meta.get('hdr', ''):
            fl_name = fl_name.replace(' DV ', ' DoVi ')
        if meta.get('type') in ('WEBDL', 'WEBRIP', 'ENCODE'):
            fl_name = fl_name.replace(meta['audio'], meta['audio'].replace(' ', '', 1))
        fl_name = fl_name.replace(meta.get('aka', ''), '')
        if meta.get('imdb_info'):
            fl_name = fl_name.replace(meta['title'], meta['imdb_info']['aka'])
            if meta['year'] != meta.get('imdb_info', {}).get('year', meta['year']) and str(meta['year']).strip() != '':
                fl_name = fl_name.replace(str(meta['year']), str(meta['imdb_info']['year']))
        if meta['category'] == "TV" and meta.get('tv_pack', 0) == 0 and meta.get('episode_title_storage', '').strip() != '' and meta['episode'].strip() != '':
            fl_name = fl_name.replace(meta['episode'], f"{meta['episode']} {meta['episode_title_storage']}")
        if 'DD+' in meta.get('audio', '') and 'DDP' in meta['uuid']:
            fl_name = fl_name.replace('DD+', 'DDP')
        if 'Atmos' in meta.get('audio', '') and 'Atmos' not in meta['uuid']:
            fl_name = fl_name.replace('Atmos', '')

        fl_name = fl_name.replace('BluRay REMUX', 'Remux').replace('BluRay Remux', 'Remux').replace('Bluray Remux', 'Remux')
        fl_name = fl_name.replace('PQ10', 'HDR').replace('HDR10+', 'HDR')
        fl_name = fl_name.replace('DoVi HDR HEVC', 'HEVC DoVi HDR').replace('HDR HEVC', 'HEVC HDR').replace('DoVi HEVC', 'HEVC DoVi')
        fl_name = fl_name.replace('DTS7.1', 'DTS').replace('DTS5.1', 'DTS').replace('DTS2.0', 'DTS').replace('DTS1.0', 'DTS')
        fl_name = fl_name.replace('Dubbed', '').replace('Dual-Audio', '')
        fl_name = ' '.join(fl_name.split())
        fl_name = re.sub(r"[^0-9a-zA-ZÀ-ÿ. &+'\-\[\]]+", "", fl_name)
        fl_name = fl_name.replace(' ', '.').replace('..', '.')
        return fl_name 

    
    ###############################################################
    ######   STOP HERE UNLESS EXTRA MODIFICATION IS NEEDED   ######
    ###############################################################

    async def upload(self, meta):
        common = COMMON(config=self.config)
        await common.edit_torrent(meta, self.tracker, self.source_flag)
        await self.edit_desc(meta)
        manual_name = meta.get('manual_name')
        fl_name = await self.edit_name(meta) if not manual_name else manual_name
        cat_id = await self.get_category_id(meta)
        has_ro_audio, has_ro_sub = await self.get_ro_tracks(meta)
        
        # Confirm the correct naming order for FL
        console.print(f"[bold blue]Filelist name:[/bold blue] {fl_name}")
        if not meta.get('unattended', False):
            fl_confirm = Confirm.ask("Correct?", default=False)
            if not fl_confirm:
                fl_name_manually = Prompt.ask("Please enter a proper name", default="")
                if fl_name_manually == "":
                    console.print('No proper name given')
                    console.print("Aborting...")
                    return
                else:
                    fl_name = fl_name_manually

        # Torrent File Naming
        # Note: Don't Edit .torrent filename after creation, SubsPlease anime releases (because of their weird naming) are an exception
        if meta.get('anime', True) and meta.get('tag', '') == '-SubsPlease':
            torrentFileName = fl_name
        else:
            if meta.get('isdir', False) is False:
                torrentFileName = meta.get('uuid')
                torrentFileName = os.path.splitext(torrentFileName)[0]
            else:
                torrentFileName = meta.get('uuid')

        # Download new .torrent from site
        fl_desc = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/[{self.tracker}]DESCRIPTION.txt", 'r', newline='', encoding='utf-8').read()
        torrent_path = f"{meta['base_dir']}/tmp/{meta['uuid']}/[{self.tracker}]{meta['clean_name']}.torrent"
        if meta['bdinfo'] != None:
            mi_dump = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/BD_SUMMARY_00.txt", 'r', encoding='utf-8').read()
        else:
            mi_dump = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/MEDIAINFO_CLEANPATH.txt", 'r', encoding='utf-8').read()
        with open(torrent_path, 'rb') as torrentFile:
            torrentFileName = unidecode(torrentFileName)
            files = {
                'file' : (f"{torrentFileName}.torrent", torrentFile, "application/x-bittorent")
            }
            data = {
                'name' : fl_name,
                'type' : cat_id,
                'descr' : fl_desc.strip(),
                'nfo' : mi_dump
            }

            if int(meta.get('imdb_id', '').replace('tt', '')) != 0:
                data['imdbid'] = meta.get('imdb_id', '').replace('tt', '')
                data['description'] = meta['imdb_info'].get('genres', '')
            if self.uploader_name and not self.config['TRACKERS'][self.tracker].get('anon', False):
                data['epenis'] = self.uploader_name
            if has_ro_audio:
                data['materialro'] = 'on'
            if meta['is_disc'] == "BDMV" or meta['type'] == "REMUX":
                data['freeleech'] = 'on'
            if int(meta.get('tv_pack', '0')) != 0:
                data['freeleech'] = 'on'
            if int(meta.get('freeleech', '0')) != 0:
                data['freeleech'] = 'on'

            url = "https://filelist.io/takeupload.php"
            # Submit
            if meta['debug']:
                console.print(url)
                console.print(data)
            else:
                with requests.Session() as session:
                    cookiefile = os.path.abspath(f"{meta['base_dir']}/data/cookies/FL.pkl")
                    with open(cookiefile, 'rb') as cf:
                        session.cookies.update(pickle.load(cf))
                    up = session.post(url=url, data=data, files=files)
                    torrentFile.close()
                    
                    # Match url to verify successful upload
                    match = re.match(r".*?filelist\.io/details\.php\?id=(\d+)&uploaded=(\d+)", up.url)
                    if match:
                        id = re.search(r"(id=)(\d+)", urlparse(up.url).query).group(2)
                        await self.download_new_torrent(session, id, torrent_path)
                    else:
                        console.print(data)
                        console.print("\n\n")
                        console.print(up.text)
                        raise UploadException(f"Upload to FL Failed: result URL {up.url} ({up.status_code}) was not expected", 'red')
        return


    async def search_existing(self, meta):
        dupes = {}
        with requests.Session() as session:
            cookiefile = os.path.abspath(f"{meta['base_dir']}/data/cookies/FL.pkl")
            with open(cookiefile, 'rb') as cf:
                session.cookies.update(pickle.load(cf))
            
            search_url = f"https://filelist.io/browse.php"
            if int(meta['imdb_id'].replace('tt', '')) != 0:
                params = {
                    'search' : meta['imdb_id'],
                    'cat' : await self.get_category_id(meta),
                    'searchin' : '3'
                }
            else:
                params = {
                    'search' : meta['title'],
                    'cat' : await self.get_category_id(meta),
                    'searchin' : '0'
                }
            try:
                r = session.get(search_url, params=params)
                await asyncio.sleep(0.5)
                soup = BeautifulSoup(r.text, 'html.parser')
                find = soup.find_all('a', href=True)
                for each in find:
                    if each['href'].startswith('details.php?id=') and "&" not in each['href']:
                        result = each['title']
                        try:
                            size = each.find('size').text
                        except Exception:
                            size = 0
                        dupes[result] = size                        
                    # CvT: Flying blind, hoping ['size'] exists. If broken, file a ticket a please include some of html from a search result (any search will do as long as it contains a result) orrr send me an invite I'll fix ;)
            except Exception as e:
                console.print(f'[bold red]Unable to search for existing torrents on site. Either the site is down or passkey is incorrect. Error: {e}')
                console.print('[bold yellow]Issue might be Uploadrr script. Please try again, if broken please let me know.')
                await asyncio.sleep(5)        

        return dupes

    


    async def validate_credentials(self, meta):
        cookiefile = os.path.abspath(f"{meta['base_dir']}/data/cookies/FL.pkl")
        if not os.path.exists(cookiefile):
            await self.login(cookiefile)
        vcookie = await self.validate_cookies(meta, cookiefile)
        if vcookie != True:
            console.print('[red]Failed to validate cookies. Please confirm that the site is up and your passkey is valid.')
            recreate = Confirm.ask("Log in again and create new session?")
            if recreate == True:
                if os.path.exists(cookiefile):
                    os.remove(cookiefile)
                await self.login(cookiefile)
                vcookie = await self.validate_cookies(meta, cookiefile)
                return vcookie
            else:
                return False
        return True
    
    
    async def validate_cookies(self, meta, cookiefile):
        url = "https://filelist.io/index.php"
        if os.path.exists(cookiefile):
            with requests.Session() as session:
                with open(cookiefile, 'rb') as cf:
                    session.cookies.update(pickle.load(cf))
                resp = session.get(url=url)
                if meta['debug']:
                    console.print('[cyan]Cookies:')
                    console.print(session.cookies.get_dict())
                    console.print(resp.url)
                if resp.text.find("Logout") != -1:
                    return True
                else:
                    return False
        else:
            return False
    
    async def login(self, cookiefile):
        with requests.Session() as session:
            r = session.get("https://filelist.io/login.php")
            await asyncio.sleep(0.5)
            soup = BeautifulSoup(r.text, 'html.parser')
            validator = soup.find('input', {'name' : 'validator'}).get('value')
            data = {
                'validator' : validator,
                'username' : self.username,
                'password' : self.password,
                'unlock' : '1',
            }
            response = session.post('https://filelist.io/takelogin.php', data=data)
            await asyncio.sleep(0.5)
            index = 'https://filelist.io/index.php'
            response = session.get(index)
            if response.text.find("Logout") != -1:
                console.print('[green]Successfully logged into FL')
                with open(cookiefile, 'wb') as cf:
                    pickle.dump(session.cookies, cf)
            else:
                console.print('[bold red]Something went wrong while trying to log into FL')
                await asyncio.sleep(1)
                console.print(response.url)
        return

    async def download_new_torrent(self, session, id, torrent_path):
        download_url = f"https://filelist.io/download.php?id={id}"
        r = session.get(url=download_url)
        if r.status_code == 200:
            with open(torrent_path, "wb") as tor:
                tor.write(r.content)
        else:
            console.print("[red]There was an issue downloading the new .torrent from FL")
            console.print(r.text)
        return


    
    async def get_ro_tracks(self, meta):
        has_ro_audio = has_ro_sub = False
        if meta.get('is_disc', '') != 'BDMV':
            mi = meta['mediainfo']
            for track in mi['media']['track']:
                if track['@type'] == "Text":
                    if track.get('Language') == "ro":
                        has_ro_sub = True
                if track['@type'] == "Audio":
                    if track.get('Audio') == 'ro':
                        has_ro_audio = True
        else:
            if "Romanian" in meta['bdinfo']['subtitles']:
                has_ro_sub = True
            for audio_track in meta['bdinfo']['audio']:
                if audio_track['language'] == 'Romanian':
                    has_ro_audio = True
                    break
        return has_ro_audio, has_ro_sub
