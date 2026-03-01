# -*- coding: utf-8 -*-
import aiofiles
import aiohttp
import json
import os
import pickle
import platform
import re
import rich.prompt as Prompt
import urllib.parse
from bs4 import BeautifulSoup
from torf import Torrent
from src.console import console
from src.trackers.COMMON import COMMON
from src.bbcode import BBCODE
 
class AR():
    def __init__(self, config):
        self.config = config
        self.session = None 
        self.tracker = 'AR'
        self.source_flag = 'AlphaRatio'
        self.username = config['TRACKERS']['AR'].get('username', '').strip()
        self.password = config['TRACKERS']['AR'].get('password', '').strip()        
        self.login_url = 'https://alpharatio.cc/login.php'
        self.upload_url = 'https://alpharatio.cc/upload.php'
        self.search_url = 'https://alpharatio.cc/torrents.php'
        self.user_agent = f'Uploadrr ({platform.system()} {platform.release()})'   
        self.signature = None
        self.banned_groups = []
 
    async def start_session(self):
        if self.session is not None:
            console.print("[dim red]Warning: Previous session was not closed properly. Closing it now.")
            await self.close_session()
        self.session = aiohttp.ClientSession()
 
    async def close_session(self):
        if self.session is not None:
            await self.session.close()
            self.session = None
 
    async def validate_credentials(self, meta):
        if self.session:
            console.print("[red dim]Warning: Previous session was not closed properly. Using existing session.")
        else:
            await self.start_session() 
 
        if await self.load_session(meta):  
            response = await self.get_initial_response()
            if await self.validate_login(response):
                return True
        else:
            console.print("No session file found. Attempting to log in...")
            if await self.login(meta):  
                console.print("Login successful, session file created.")
                await self.save_session(meta)  
                return True
            else:
                console.print('[red]Failed to validate credentials. Please confirm that the site is up and your passkey is valid.')
        return False
 
    async def get_initial_response(self):
        async with self.session.get(self.login_url) as response:
            return await response.text()
 
    async def validate_login(self, response_text):
        if 'login.php?act=recover' in response_text:
            console.print("Login failed. Check your credentials.")
            return False
        return True
 
    async def login(self, meta):
        data = {
            "username": self.username,
            "password": self.password,
            "keeplogged": "1",
            "login": "Login",
        }
        async with self.session.post(self.login_url, data=data) as response:
            if await self.validate_login(await response.text()):
                await self.save_session(meta)
                return True
        return False
 
    async def save_session(self, meta):
        session_file = os.path.abspath(f"{meta['base_dir']}/data/cookies/{self.tracker}.pkl")
        os.makedirs(os.path.dirname(session_file), exist_ok=True)
        cookies = self.session.cookie_jar
        cookie_dict = {}
        for cookie in cookies:
            cookie_dict[cookie.key] = cookie.value
 
        with open(session_file, 'wb') as f:
            pickle.dump(cookie_dict, f)
 
    async def load_session(self, meta):
        session_file = os.path.abspath(f"{meta['base_dir']}/data/cookies/{self.tracker}.pkl")
        retry_count = 0
        max_retries = 2

        while retry_count < max_retries:
            try:
                with open(session_file, 'rb') as f:
                    cookie_dict = pickle.load(f)

                    # Update the cookie jar with the loaded cookies
                    for name, value in cookie_dict.items():
                        self.session.cookie_jar.update_cookies({name: value})

                    if meta.get('debug', False):
                        print("Loaded cookies:", cookie_dict)
                    
                    # Validate the session by making a request after loading cookies
                    try:
                        response = await self.session.get('https://alpharatio.cc/torrents.php')
                        if response.status == 200:  # Check for successful response
                            return True  # Session is valid
                        else:
                            console.print(f"[yellow]Session might be invalid, status code: {response.status}. Retrying...")
                    except aiohttp.ClientError as e:  # Be specific about the exceptions we expect
                        console.print(f"[yellow]Session might be invalid, network error: {e}. Retrying...")
            
            except (FileNotFoundError, EOFError, pickle.UnpicklingError) as e:
                console.print(f"Session loading error: {e}. Closing session and retrying.")
                await self.close_session()  # Close the session if there's an error
                await self.start_session()  # Reinitialize the session
            retry_count += 1

        # If we've exhausted our retries, attempt to log in anew
        console.print("Failed to reuse session after retries. Attempting to log in again...")
        await self.close_session()
        await self.start_session()  # Make sure we start with a fresh session
        if await self.login(meta):
            console.print("Login successful, new session created.")
            await self.save_session(meta)
            return True
        else:
            console.print('[red]Failed to validate credentials. Please confirm that the site is up and your credentials are valid.')
            return False
 
 
    async def edit_desc(self, meta):
        bbcode = BBCODE()
        desc_path = f"{meta['base_dir']}/tmp/{meta['uuid']}/[{self.tracker}]DESCRIPTION.txt"
        if meta.get('is_music', False):
            common = COMMON(config=self.config)
            desc = await common.create_music_description(meta, self.tracker)            
            with open(desc_path, 'r', encoding='utf-8') as file:
                desc = file.read()
                        
            desc = bbcode.clean_for_ar(desc)
            with open(desc_path, 'w', encoding='utf-8') as file:
                file.write(desc)

        else:
            base = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/DESCRIPTION.txt", 'r', encoding='utf-8').read()
            base = bbcode.clean_for_ar(base)
    
            with open(desc_path, 'w') as desc:
    
                # Extracting required media info
                media_info = meta['mediainfo']['media']['track']
                filename = next((track['FileNameExtension'] for track in media_info if track["@type"] == "General"), "N/A")
                duration = next((track['Duration_String3'] for track in media_info if track["@type"] == "General"), "N/A")
                video_info = next((track for track in media_info if track["@type"] == "Video"), {})
                video_encode = meta.get('video_encode', '')
                audio_info = next((track for track in media_info if track["@type"] == "Audio"), {})
                subtitles_list = next((track.get('Text_Language_List', "N/A") for track in media_info if track["@type"] == "General"), "N/A")
                if subtitles_list != "N/A":
                    subtitles = ', '.join(sorted(set(subtitles_list.split(' / '))))  # Remove duplicates and sort
                else:
                    subtitles = "N/A"
                
                resolution = f"{video_info.get('Width', 'N/A')} x {video_info.get('Height', 'N/A')}"
                video_details = []
                if video_info:
                    bitrate = video_info.get('BitRate_String', 'N/A')
                    framerate = video_info.get('FrameRate_String', 'N/A')
                    video_details.append(resolution)
                    if bitrate != "N/A":
                        video_details.append(bitrate)
                    if framerate != "N/A":
                        video_details.append(framerate)
                    video_details.append(video_encode)
                video_details_str = ' / '.join(video_details) if video_details else "N/A"

                audio_details = []
                if audio_info:
                    audio = meta.get('audio', "N/A")
                    bitrate = audio_info.get('BitRate_String', 'N/A')
                    audio_details.append(audio)
                    if bitrate != "N/A":
                        audio_details.append(bitrate)
                audio_details_str = ' @ '.join(audio_details) if audio_details else "N/A"
    
                # Convert size from bytes to MB or GB
                size_bytes = int(media_info[0].get('FileSize', 0)) if media_info else 0
                if size_bytes < 1024 * 1024:  # Less than 1 MB (smol pdf?)
                    size = f"{size_bytes} Bytes"
                elif size_bytes < 1024 * 1024 * 1024:  # Less than 1 GB
                    size = f"{size_bytes / (1024 * 1024):.2f} MB"
                else:  # 1 GB or more
                    size = f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"
    
                imdb_id = meta.get('imdb_id')
                category = meta['category'].lower()
                tmdb_id = meta.get('tmdb')
    
                plot = meta.get('overview', '') or meta['imdb_info'].get('plot', '')
                add_logo_enabled = self.config["DEFAULT"].get("add_logo", False)
                if add_logo_enabled:
                    logo = meta.get('logo')
                    if logo:
                        desc.write(f"[align=center][img]{logo}[/img][/align]\n")  
                # Writing media details
                desc.write(f"[code]Filename........: {filename}\n")
                desc.write(f"Duration........: {duration}\n")
                desc.write(f"Video...........: {video_details_str}\n")
                desc.write(f"Audio...........: {audio_details_str}\n")
                desc.write(f"Subtitles.......: {subtitles}\n")
                desc.write(f"Size............: {size}\n")
                desc.write(f"IMDB............:[/code] [url]https://www.imdb.com/title/tt{imdb_id}/[/url]\n")
                desc.write(f"[code]TMDB............:[/code] [url]https://www.themoviedb.org/{category}/{tmdb_id}[/url]\n")
                desc.write(f"[code]Plot............: {plot}[/code]\n\n")
    
                if meta.get('bdinfo') is not None:
                    bd_dump = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/BD_SUMMARY_00.txt", 'r', encoding='utf-8').read()
                    desc.write("[hide=BD iNFO]" + bd_dump + "[/hide]\n\n")
                else:
                    mi_dump = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/MEDIAINFO_CLEANPATH.txt", 'r', encoding='utf-8').read()[:-65].strip()
                    desc.write("[hide=Mediainfo]" + mi_dump + "[/hide]\n\n")
    
                images = meta.get('image_list', [])
                if images:
                    desc.write("[hide=Screenshots][align=center]\n")
                    for each in images:
                        raw_url = each['raw_url']
                        desc.write(f"[img]{raw_url}[/img] ")
                    desc.write("[/align][/hide]\n")
    
                desc.write("\n\n" + base)
 
    async def get_cat_id(self, meta, for_search=False):
        category_name = meta.get('category')
        resolution = meta.get('resolution', '')
        anime = meta.get('anime', False)
        sd = meta.get('sd', False)
        is_disc = meta.get('is_disc', False)
        tv_pack = meta.get('tv_pack', False)

        categories = {
            'MOVIE': '8' if for_search else '7',
            'TV': '1' if for_search else '0',
            'ANIME': '16',
            'MUSIC': '28',
        }
        category_id = categories.get(category_name, '0')

        if category_name in ('MOVIE', 'TV'):
            if anime:
                category_id = '16' if sd else '17' if for_search else '16' if sd else '15'
            elif sd:
                if category_name == 'MOVIE':
                    category_id = '8' if for_search else '7'
                else:  # TV
                    category_id = '5' if tv_pack and for_search else '1'
            elif is_disc:
                category_id = '15' if for_search else '14'
            elif resolution in ('8640p', '4320p', '2160p'):
                if category_name == 'MOVIE':
                    category_id = '10' if for_search else '9'
                else:  # TV
                    category_id = '7' if tv_pack and for_search else '6' if not for_search and tv_pack else '3' if for_search else '2'
            else:
                if category_name == 'TV':
                    category_id = '6' if tv_pack and for_search else '2'
                else:  # MOVIE
                    category_id = '9' if for_search else '8'

        return category_id
 
    def get_language_tag(self, meta):
        lang_tag = ""  
        has_eng_audio = False
        audio_lang = ""
        if meta['is_disc'] != "BDMV":
            try:
                with open(f"{meta.get('base_dir')}/tmp/{meta.get('uuid')}/MediaInfo.json", 'r', encoding='utf-8') as f:
                    mi = json.load(f)
                for track in mi['media']['track']:
                    if track['@type'] == "Audio":
                        if track.get('Language', 'None').startswith('en'):
                            has_eng_audio = True
                        if not has_eng_audio:
                            audio_lang = mi['media']['track'][2].get('Language_String', "").upper()
            except Exception as e:
                print(f"Error: {e}")
        else:
            for audio in meta['bdinfo']['audio']:
                if audio['language'] == 'English':
                    has_eng_audio = True
                if not has_eng_audio:
                    audio_lang = meta['bdinfo']['audio'][0]['language'].upper()
        if audio_lang != "":
            lang_tag = audio_lang
        return lang_tag
 
    def get_basename(self, meta):
        path = next(iter(meta['filelist']), meta['path'])
        return os.path.basename(path)
 
    async def get_name(self, meta):
        manual_name = meta.get('manual_name')
        type = meta.get('type', "")
        title = meta.get('title',"")
        artist = meta.get('artist', "")
        album = meta.get('album', "")
        year = meta.get('year', "")
        resolution = meta.get('resolution', "")
        if resolution == "OTHER":
            resolution = ""
        audio = meta.get('audio', "")
        bit_depth = meta.get('bit_depth', "")
        bitrate = meta.get('bitrate', "")        
        lang_tag = self.get_language_tag(meta)
        service = meta.get('service', "")
        season = meta.get('season', "")
        episode = meta.get('episode', "")
        part = meta.get('part', "")
        repack = meta.get('repack', "")
        three_d = meta.get('3D', "")
        tag = meta.get('tag', "")
        if tag == "":
            tag = "-NOGRP"
        source = meta.get('source', "")
        uhd = meta.get('uhd', "")
        hdr = meta.get('hdr', "")
        episode_title = meta.get('episode_title', '')
        if meta.get('is_disc', "") == "BDMV": #Disk
            video_codec = meta.get('video_codec', "")
            region = meta.get('region', "")
        elif meta.get('is_disc', "") == "DVD":
            region = meta.get('region', "")
            dvd_size = meta.get('dvd_size', "")
        else:
            video_codec = meta.get('video_codec', "")
            video_encode = meta.get('video_encode', video_codec)
        edition = meta.get('edition', "")
        cut = meta.get('cut', "")
        ratio = meta.get('ratio', "")
 
        if meta['category'] == "TV":
            try:
                year = meta['year']
                if not year: 
                    raise ValueError("No TMDB Year Found..trying IMDB")
            except (KeyError, ValueError):
                try:
                    year = meta['imdb_info']['year']
                    if not year:
                        raise ValueError("No IMDB Year Found..")
                except (KeyError, ValueError):
                    year = ""
        if meta.get('no_season', False) is True:
            season = ''
        if meta.get('no_year', False) is True:
            year = ''
        if meta['debug']:
            console.log("[cyan]get_name cat/type")
            console.log(f"CATEGORY: {meta['category']}")
            console.log(f"TYPE: {meta['type']}")
            console.log("[cyan]get_name meta:")
            console.log(meta)
 
        #YAY NAMING FUN
        if meta['category'] == "MOVIE": #MOVIE SPECIFIC
            if type == "DISC": #Disk
                if meta['is_disc'] == 'BDMV':
                    name = f"{title} {year} {three_d} {lang_tag} {cut} {ratio} {edition} {repack} {resolution} {region} {uhd} {source} {hdr} {video_codec} {audio}{tag}"
                    potential_missing = ['edition', 'region', 'distributor']
                elif meta['is_disc'] == 'DVD': 
                    name = f"{title} {year} {lang_tag} {cut} {ratio} {edition} {repack} {source} {dvd_size} {audio}{tag}"
                    potential_missing = ['edition', 'distributor']
                elif meta['is_disc'] == 'HDDVD':
                    name = f"{title} {year} {lang_tag} {cut} {ratio} {edition} {repack} {resolution} {source} {video_codec}] {audio}{tag}"
                    potential_missing = ['edition', 'region', 'distributor']
            elif type == "REMUX" and source in ("BluRay", "HDDVD"): #BluRay/HDDVD Remux
                name = f"{title} {year} {three_d} {lang_tag} {cut} {ratio} {edition} {repack} {resolution} {uhd} {source} REMUX {hdr} {video_codec} {audio}{tag}" 
                potential_missing = ['edition', 'description']
            elif type == "REMUX" and source in ("PAL DVD", "NTSC DVD", "DVD"): #DVD Remux
                name = f"{title} {year} {lang_tag} {cut} {ratio} {edition} {repack} {source} REMUX  {audio}{tag}" 
                potential_missing = ['edition', 'description']
            elif type == "ENCODE": #Encode
                name = f"{title} {year} {lang_tag} {cut} {ratio} {edition} {repack} {resolution} {uhd} {source} {audio} {hdr} {video_encode}{tag}"  
                potential_missing = ['edition', 'description']
            elif type == "WEBDL": #WEB-DL
                name = f"{title} {year} {lang_tag} {cut} {ratio} {edition} {repack} {resolution} {uhd} {service} WEB-DL {audio} {hdr} {video_encode}{tag}"
                potential_missing = ['edition', 'service']
            elif type == "WEBRIP": #WEBRip
                name = f"{title} {year} {lang_tag} {cut} {ratio} {edition} {repack} {resolution} {uhd} {service} WEBRip {audio} {hdr} {video_encode}{tag}"
                potential_missing = ['edition', 'service']
            elif type == "HDTV": #HDTV
                name = f"{title} {year} {lang_tag} {cut} {ratio} {edition} {repack} {resolution} {source} {audio} {video_encode}{tag}"
                potential_missing = []
        elif meta['category'] == "TV": #TV SPECIFIC
            if type == "DISC": #Disk
                if meta['is_disc'] == 'BDMV':
                    name = f"{title} {year} {season}{episode} {three_d} {lang_tag} {cut} {ratio} {edition} {repack} {resolution} {region} {uhd} {source} {hdr} {video_codec} {audio}{tag}"
                    potential_missing = ['edition', 'region', 'distributor']
                if meta['is_disc'] == 'DVD':
                    name = f"{title} {season}{episode} {three_d} {lang_tag} {cut} {ratio} {edition} {repack} {source} {dvd_size} {audio}{tag}"
                    potential_missing = ['edition', 'distributor']
                elif meta['is_disc'] == 'HDDVD':
                    name = f"{title} {year} {lang_tag} {cut} {ratio} {edition} {repack} {resolution} {source} {video_codec} {audio}{tag}"
                    potential_missing = ['edition', 'region', 'distributor']
            elif type == "REMUX" and source in ("BluRay", "HDDVD"): #BluRay Remux
                name = f"{title} {year} {season}{episode} {episode_title} {part} {three_d} {lang_tag} {cut} {ratio} {edition} {repack} {resolution} {uhd} {source} REMUX {hdr} {video_codec} {audio}{tag}" #SOURCE
                potential_missing = ['edition', 'description']
            elif type == "REMUX" and source in ("PAL DVD", "NTSC DVD"): #DVD Remux
                name = f"{title} {year} {season}{episode} {episode_title} {part} {lang_tag} {cut} {ratio} {edition} {repack} {source} REMUX {audio}{tag}" #SOURCE
                potential_missing = ['edition', 'description']
            elif type == "ENCODE": #Encode
                name = f"{title} {year} {season}{episode} {episode_title} {part} {lang_tag} {cut} {ratio} {edition} {repack} {resolution} {uhd} {source} {audio} {hdr} {video_encode}{tag}" #SOURCE
                potential_missing = ['edition', 'description']
            elif type == "WEBDL": #WEB-DL
                name = f"{title} {year} {season}{episode} {episode_title} {part} {lang_tag} {cut} {ratio} {edition} {repack} {resolution} {uhd} {service} WEB-DL {audio} {hdr} {video_encode}{tag}"
                potential_missing = ['edition', 'service']
            elif type == "WEBRIP": #WEBRip
                name = f"{title} {year} {season}{episode} {episode_title} {part} {lang_tag} {cut} {ratio} {edition} {repack} {resolution} {uhd} {service} WEBRip {audio} {hdr} {video_encode}{tag}"
                potential_missing = ['edition', 'service']
            elif type == "HDTV": #HDTV
                name = f"{title} {year} {season}{episode} {episode_title} {part} {lang_tag} {cut} {ratio} {edition} {repack} {resolution} {source} {audio} {video_encode}{tag}"
                potential_missing = []
        elif meta['category'] == "MUSIC": #MUSIC SPECIFIC
            source = f'{source} ' if source else ''
            tag = '' if tag == "-NOGRP" else tag
            manual_edition = meta.get('manual_edition')
            edition = manual_edition if manual_edition else edition
            ed = f"[{edition}]" if edition else ''
            bd = f"{bit_depth}bit" if bit_depth else ''  
            potential_missing = []

            if type in ['ALAC', 'FLAC', 'WAV']:
                name = f"{artist} {album} {year} {ed} {source}{type} {bd} {tag}"
            else:
                name =  f"{artist} {album} {year} {ed} {source}{type} {bitrate} {tag}"

        name = name.replace(':', '').replace("'", '').replace('DD+', 'DDP')
        name = '.'.join(part for part in name.split() if part)
        return name
 
 
    async def search_existing(self, meta):
        await self.validate_credentials(meta)
        dupes = {}
        category_id = await self.get_cat_id(meta, for_search=True) 
        title = urllib.parse.quote(meta.get('title', ''))
        search_url = f"https://alpharatio.cc/torrents.php?action=basic&searchsubmit=1&" \
                    f"filter_cat%5B{category_id}%5D=1&searchstr={title}&order_by=time&order_way=desc"
 
        if meta.get('debug', False):
            console.print(f"[blue]{search_url}")            
 
        try:
            async with self.session.get(search_url) as response:
                response_text = await response.text()
                if response.status != 200 or not self._has_existing_torrents(response_text):
                    console.print("[red]No existing torrents found or request failed.")
                    return dupes
 
                soup = BeautifulSoup(response_text, 'html.parser')
                torrent_rows = soup.find_all('tr', class_='torrent')
                console.print(f"[blue]Found {len(torrent_rows)} torrent rows.")
                for row in torrent_rows:
                    title = row.find('a', title="View User Torrent") or row.find('a', title="View Auto Torrent")
                    
                    if title is not None:
                        name = title.text.strip()
                    else:
                        console.print("[yellow]No valid torrent name found in this row.")
                    size = row.find_all('td')[4].text.strip()
                    dupes[name] = size
 
                if not dupes:
                    console.print("[yellow]No duplicates found.")
        
        except Exception as e:
            console.print(f"[red]Error occurred: {e}")
 
        console.print(f"[blue]{dupes}")
        return dupes
 
 
    def _has_existing_torrents(self, response_text):
        """Check the response text for existing torrents."""
        return 'Your search did not match anything.' not in response_text
 
    def extract_auth_key(self, response_text):
        soup = BeautifulSoup(response_text, 'html.parser')
        logout_link = soup.find('a', href=True, text='Logout')
 
        if logout_link:
            href = logout_link['href']
            match = re.search(r'auth=([^&]+)', href)
            if match:
                return match.group(1)
        return None
 
    async def upload(self, meta):
        # Prepare the data for the upload
        common = COMMON(config=self.config)
        await common.edit_torrent(meta, self.tracker, self.source_flag)
        await self.edit_desc(meta)
        is_music = meta.get("is_music", False)

        # Read the description
        desc_path = f"{meta['base_dir']}/tmp/{meta['uuid']}/[{self.tracker}]DESCRIPTION.txt"
        try:
            async with aiofiles.open(desc_path, 'r') as desc_file:
                desc = await desc_file.read()
        except FileNotFoundError:
            raise Exception(f"Description file not found at {desc_path} ")
 
        # Handle cover image input
        cover = (meta.get('poster') or meta["imdb_info"].get("cover")) if not is_music else meta.get("album_cover")
        while cover is None and not meta.get("unattended", False):
            cover = Prompt.ask("No Poster was found. Please input a link to a poster:", default="")
            if not re.match(r'https?://.*\.(jpg|png|gif)$', cover):
                print("Invalid image link. Please enter a link that ends with .jpg, .png, or .gif.")
                cover = None    
 
        # Tag Compilation
        genres = meta.get('genres')
        if genres:
            genres = ', '.join(tag.strip('.') for tag in (item.replace(' ', '.') for item in genres.split(',')))
            genres = re.sub(r'\.{2,}', '.', genres)
 
        imdb_id = meta.get('imdb_id', '')
        tags = f"tt{imdb_id}, {genres}" if imdb_id else genres
        if tags == None:
            tags = ''
 
        # Get initial response and extract auth key
        initial_response = await self.get_initial_response()
        auth_key = self.extract_auth_key(initial_response)
 
        # Access the session cookie
        cookies = self.session.cookie_jar.filter_cookies(self.upload_url)
        session_cookie = cookies.get('session')
        
        if not session_cookie:
            raise Exception("Session cookie not found.")

        manual_name = meta.get('manual_name')
        ar_name = manual_name or await self.get_name(meta)

        data = {
            "submit": "true",
            "auth": auth_key, 
            "type": await self.get_cat_id(meta),
            "title": ar_name,
            "tags": tags,
            "image": cover,
            "desc": desc,
        }
 
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Origin": "https://alpharatio.cc",
            "Referer": "https://alpharatio.cc/upload.php",
            "Cookie": f"session={session_cookie.value}",
        }
 
        torrent_path = f"{meta['base_dir']}/tmp/{meta['uuid']}/[{self.tracker}]{meta['clean_name']}.torrent"
        # Print the form data for inspection
        if meta.get('debug', False):
            console.print("Submitting data:")
            for key, value in data.items():
                print(f"{key}: {value}")
        else:
            pass        
        try:
            async with aiofiles.open(torrent_path, 'rb') as torrent_file:
                # Use a single session for all requests
                async with aiohttp.ClientSession() as session:
                    form = aiohttp.FormData()
                    for key, value in data.items():
                        form.add_field(key, value)
                    form.add_field('file_input', torrent_file, filename=f"{meta['clean_name']}.torrent")
 
                    # Perform the upload
                    if not meta['debug']:
                        async with session.post(self.upload_url, data=form, headers=headers) as response:
                            if response.status == 200:
                                comment = response.url
                                await self.update_torrent_file(torrent_path, comment)
                            else:
                                print("Upload failed. Response was not 200.")
        except FileNotFoundError:
            print(f"File not found: {torrent_path}")
 
    async def update_torrent_file(self, torrent_path, comment):
        try:
            base_torrent = Torrent.read(torrent_path)
            base_torrent.comment = f"Created by Uploadrr for AlphaRatio: {comment}"
            base_torrent.write(torrent_path, overwrite=True)
        except Exception as e:
            print(f"Error updating torrent file: {e}")
 
