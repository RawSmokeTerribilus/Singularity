# -*- coding: utf-8 -*-
# import discord
import asyncio
import requests
import re
import langcodes
import platform
from datetime import datetime
from rich.pretty import Pretty

from src.trackers.COMMON import COMMON
from src.console import console, log


class LDU():

    def __init__(self, config):
        self.config = config
        self.tracker = 'LDU'
        self.source_flag = 'LDU'
        self.upload_url = 'https://theldu.to/api/torrents/upload'
        self.search_url = 'https://theldu.to/api/torrents/filter'
        self.signature = None
        self.banned_groups = ['']
        pass
    
    async def get_cat_id(self, category_name, genres, keywords, service, edition, meta):
        adult = meta.get('adult', False)
        soundmix = meta.get('imdb_info', {}).get('soundmix', [])
        is_silent = 'silent' in soundmix if soundmix else False
        release_date = meta.get('full_date', '')
        
        # Handle release date parsing
        if isinstance(release_date, str):
            try:
                release_date = datetime.strptime(release_date, '%Y-%m-%d')
            except ValueError:
                year = meta.get('year')
                if year is not None:
                    release_date = datetime.strptime(f'{year}-01-01', '%Y-%m-%d')

        year = meta.get('year', '')
        tag = self.get_language_tag(meta) or ''
        tags = [t[1:] for t in tag.split(']') if t] if tag else []

        anime = meta.get('anime', False)
        category_id = {
            'MOVIE': '1', 
            'TV': '2', 
            'Anime': '8',
            'FANRES': '12',
            'MUSIC' : '3', 
        }.get(category_name, '0')

        keyword_list = [k.strip() for k in keywords.lower().split(',')]
        genre_list = [g.strip() for g in genres.lower().split(',')]

        if category_name == 'MOVIE':
            if (adult and anime) or 'hentai' in keyword_list or (adult and 'animation' in keyword_list):
                category_id = '10'
            elif adult:
                category_id = '6'
            elif '???' in tags:
                category_id = '27'
            elif 'ENG' not in ''.join(tags):
                category_id = '22'
            elif '3D' in edition:
                category_id = '21'
            elif any(x in edition.upper() for x in ['FANRES', 'FANEDIT', 'FANFIX', 'RESTORATION']):
                category_id = '12'
            elif anime or 'anime' in keyword_list:
                category_id = '8'
            elif (release_date and release_date < datetime(1927, 10, 1)) or (year and int(year) <= 1926) or 'silent film' in keyword_list or is_silent:
                category_id = '18'
            elif 'holiday' in keyword_list:
                category_id = '24'
            elif 'musical' in keyword_list:
                category_id = '25'
            elif 'documentary' in genre_list:
                category_id = '17'
            elif 'stand-up' in keyword_list:
                category_id = '20'
            elif 'short film' in keyword_list:
                category_id = '19'
            else:
                category_id = '1'

        elif category_name == 'TV':
            if (adult and anime) or 'hentai' in keyword_list or (adult and 'animation' in keyword_list):
                category_id = '10'
            elif adult:
                category_id = '6'
            elif tag and not all(char.isalpha() or char.isspace() for char in tags[0]):
                category_id = '31'
            elif 'ENG' not in ''.join(tags):
                category_id = '29'
            elif anime or 'anime' in keyword_list:
                category_id = '9'
            else:
                category_id = '2'

        return category_id

    async def get_type_id(self, type, edition):
        type_id = {
            'DISC': '1', 
            'REMUX': '2',
            'WEBDL': '4', 
            'WEBRIP': '5', 
            'HDTV': '6',
            'ENCODE': '3',
            'UPSCALE': '27',
            'AAC': '10',
            'FLAC': '7',
            'MP3': '11',
            'ALAC': '8',
            'AC3': '9',
            'WAVE': '14',
            'OGG': '14',
            'MPEG4': '14',            
            }.get(type, '0')
        if type == 'ENCODE':
            if 'upscale' in edition.lower() or 'ai' in edition.lower():
                type_id = '27' 
            else:
                type_id = '3'    
        return type_id

    async def get_res_id(self, resolution):
        resolution_id = {
            '8640p':'10', 
            '4320p': '1', 
            '2160p': '2', 
            '1440p' : '3',
            '1080p': '3',
            '1080i':'4', 
            '720p': '5',  
            '576p': '6', 
            '576i': '7',
            '480p': '8', 
            '480i': '9'
            }.get(resolution, '10')
        return resolution_id

    ###############################################################
    ######   STOP HERE UNLESS EXTRA MODIFICATION IS NEEDED   ######
    ###############################################################

    async def upload(self, meta):
        is_music = meta.get('is_music', False)
        common = COMMON(config=self.config)
        await common.edit_torrent(meta, self.tracker, self.source_flag)
        cat_id = await self.get_cat_id(meta['category'], meta.get('genres', ''), meta.get('keywords', ''), meta.get('service', ''), meta.get('edition', ''), meta)
        type_id = await self.get_type_id(meta['type'],meta['edition'])
        resolution_id = await self.get_res_id(meta['resolution'])
        await common.unit3d_edit_desc(meta, self.tracker)
        manual_name = meta.get('manual_name')
        ldu_name = meta['name'] if is_music else await self.get_name(meta)
        region_id = await common.unit3d_region_ids(meta.get('region'))
        distributor_id = await common.unit3d_distributor_ids(meta.get('distributor'))
        if meta['anon'] != 0 or self.config['TRACKERS'][self.tracker].get('anon', "False"):
            anon = 1
        else:
            anon = 0

        if meta['bdinfo'] != None:
            mi_dump = None
            bd_dump = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/BD_SUMMARY_00.txt", 'r', encoding='utf-8').read()
        else:
            mi_dump = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/MEDIAINFO.txt", 'r', encoding='utf-8').read()
            bd_dump = None

        desc = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/[{self.tracker}]DESCRIPTION.txt", 'r', encoding='utf-8').read()
        if cat_id == '10':
            poster = meta.get('poster')
            backdrop = meta.get('backdrop')
            url_string = ""
            if poster:
                url_string += f"[url=torrent-cover={poster} ] [/url] \n"
            if backdrop:
                url_string += f"[url=torrent-banner={backdrop} ] [/url]"
            desc += url_string        
        open_torrent = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/[{self.tracker}]{meta['clean_name']}.torrent", 'rb')
        nfo_file = meta.get('nfo_file', None)
        files = {'torrent': open_torrent}
        if nfo_file:
            open_nfo = open(nfo_file, 'rb') 
            files['nfo'] = open_nfo
        data = {
            'name': manual_name or ldu_name,
            'description': desc,
            'mediainfo': mi_dump,
            'category_id': cat_id,
            'type_id': type_id,
            'tmdb': meta.get('tmdb', 0),
            'imdb': meta.get('imdb_id', 0).replace('tt', '') if not is_music else 0,
            'tvdb': meta.get('tvdb_id', 0),
            'mal': meta.get('mal_id', 0),
            'igdb': 0,
            'anonymous': anon,
            'stream': int(meta.get('stream', False)),
            'sd': meta['sd'],
            'keywords': meta['keywords'],
            'personal_release': int(meta.get('personalrelease', False)),
            'internal': 0,
            'featured': 0,
            'free': 0,
            'doubleup': 0,
            'sticky': 0,
        }

        if not is_music:
            data.update({
                'resolution_id': resolution_id,
                'bdinfo': bd_dump,
            })
        # Internal
        if self.config['TRACKERS'][self.tracker].get('internal', False):
            if meta['tag'] != "" and (meta['tag'][1:] in self.config['TRACKERS'][self.tracker].get('internal_groups', [])):
                data['internal'] = 1
                
        if region_id != 0:
            data['region_id'] = region_id
        if distributor_id != 0:
            data['distributor_id'] = distributor_id
        if meta.get('category') == "TV" and not cat_id == '10':
            data['season_number'] = int(meta.get('season_int', '0'))
            data['episode_number'] = int(meta.get('episode_int', '0'))
        headers = {
            'User-Agent': f'Uploadrr / v1.0 ({platform.system()} {platform.release()})'
        }
        params = {
            'api_token' : self.config['TRACKERS'][self.tracker]['api_key'].strip()
        }

        if meta['debug']:
            console.print(f"[blue]DATA 2 SEND[/blue]:")
            console.print(Pretty(data))

        else:
            success = 'Unknown'
            try:
                response = requests.post(url=self.upload_url, files=files, data=data, headers=headers, params=params)
                if response.status_code >= 200 and response.status_code < 300:
                    response_json = response.json()
                    success = response_json.get('success', False)
                    data = response_json.get('data', {})

                    if not success:
                        message = response_json.get('message', 'No message provided')
                        console.print(f"[red]Upload failed: {message}[/red]")
                        if data:
                            console.print(f"[cyan]Error details:[/cyan] {data}")

                else:
                    try:
                        from bs4 import BeautifulSoup
                        soup = BeautifulSoup(response.text, 'html.parser')
                        error_heading = soup.find(class_='error__heading')
                        error_body = soup.find(class_='error__body')
                        
                        if error_heading and error_body:
                            console.print(f"[red]{error_heading.text.strip()}[/red]")
                            console.print(f"[b][yellow]{error_body.text.strip()}[/yellow][/b]")
                        else:
                            console.print(f"[red]Encountered HTTP Error: {response.status_code}[/red]")
                            console.print(f"[blue]Server Response[/blue]: {response.text}")
                    except Exception as parse_error:
                        console.print(f"[red]Failed to parse error response: {parse_error}[/red]")
                        console.print(f"[blue]Server Response[/blue]: {response.text}")
                    
                    success = False
                    data = {}

            except requests.exceptions.RequestException as e:
                console.print(f"[red]Encountered Error: {e}[/red]")
                data = {}

            if success == 'Unknown':
                console.print("[bold yellow]Status of upload is unknown, please go check..")

            elif success:
                console.print("[bold green]Torrent uploaded successfully!")
            else:
                console.print("[bold red]Torrent upload failed.")
            
            try:
                open_torrent.close()
            except Exception as e:
                console.print(f"[red]Failed to close torrent file: {e}[/red]")

            return success

    def get_language_tag(self, meta):
        soundmix = meta.get('imdb_info', {}).get('soundmix', [])
        is_silent = 'silent' in soundmix if soundmix else False 

        def map_language(language):
            try:
                lang_code = langcodes.find(language).to_alpha3()
                return lang_code.upper()
            except langcodes.LanguageTagError:
                return '???'

        audio_lang = []
        sub_lang = []
        if meta.get("is_disc") == "BDMV":
            if 'discs' in meta and meta['discs']:
                bdinfo = meta['discs'][0].get('bdinfo', {})
                audio_tracks = bdinfo.get('audio', [])
                subtitle_tracks = bdinfo.get('subtitles', [])
                
                for track in audio_tracks:
                    language = track.get('language')
                    if language and 'comment' not in language.lower() and 'review' not in language.lower():
                        audio_lang.append(map_language(language))

                audio_lang = list(dict.fromkeys(audio_lang))  # Remove dupes + keep order
                
                if not audio_lang:
                    audio_lang.append('???')
                
                if is_silent:
                    lang_tag = "[Silent]"
                else:    
                    lang_tag = f"[{' '.join(audio_lang)}]"
                
                for lang in subtitle_tracks:
                    sub_lang.append(map_language(lang))
                
                if not sub_lang:
                    sub_lang_tag = "[No Subs]"
                else:
                    sub_lang = list(dict.fromkeys(sub_lang))  # Remove dupes + keep order
                    if 'ENG' in sub_lang:
                        if len(sub_lang) > 1:
                            sub_lang_tag = "[Subs ENG+]"
                        else:
                            sub_lang_tag = "[Subs ENG]"
                    else:
                        if sub_lang[0] == '???':
                            sub_lang_tag = "[Subs ???]"
                        else:
                            if len(sub_lang) > 1:
                                sub_lang_tag = f"[Subs {sub_lang[0]}+]"
                            else:
                                sub_lang_tag = f"[Subs {sub_lang[0]}]"
        elif 'mediainfo' in meta:
            for x in meta["mediainfo"]["media"]["track"]:
                if x["@type"] == "Audio":
                    commentary_found = 'Title' in x and ('comment' in x['Title'].lower() or 'review' in x['Title'].lower())
                    if not commentary_found and 'Language_String3' in x:
                        audio_lang.append(x.get('Language_String3'))
            
            audio_lang = list(dict.fromkeys(audio_lang))  # Remove dupes + keep order
            if not audio_lang:
                audio_lang.append('???')
            if is_silent:
                lang_tag = "[Silent]"
            else:        
                lang_tag = f"[{' '.join(lang.upper() for lang in audio_lang)}]"
            
            sub_lang = [x.get('Language_String3') for x in meta["mediainfo"]["media"]["track"] if x["@type"] == "Text"]
            if not sub_lang:
                sub_lang_tag = "[No Subs]"
            else:
                sub_lang = list(dict.fromkeys(sub_lang))  # Remove dupes + keep order
                if 'eng' in sub_lang:
                    if len(sub_lang) > 1:
                        sub_lang_tag = "[Subs ENG+]"
                    else:
                        sub_lang_tag = "[Subs ENG]"
                else:
                    if sub_lang[0] is None:
                        sub_lang_tag = "[Subs ???]"
                    else:
                        if len(sub_lang) > 1:
                            sub_lang_tag = f"[Subs {sub_lang[0].upper()}+]"
                        else:
                            sub_lang_tag = f"[Subs {sub_lang[0].upper()}]"
        else:
            audio_lang.append('???')
            if is_silent:
                lang_tag = "[Silent]"
            else:    
                lang_tag = f"[{' '.join(audio_lang)}]"
            sub_lang_tag = "[No Subs]"

        return lang_tag + " " + sub_lang_tag


   
    async def get_name(self, meta):
        """
        Have to agree with whoever made HUNO's script
        was easier to rebuild name with Prep.get_name() and mofidy 
        than to attempt to edit the name thereafter - thanks for the tip!
        """
        type = meta.get('type', "")
        title = meta.get('title',"")
        alt_title = meta.get('aka', "")
        year = meta.get('year', "")
        resolution = meta.get('resolution', "")
        if resolution == "OTHER":
            resolution = ""
        audio = meta.get('audio', "")
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
        if meta.get('no_aka', False) is True:
            alt_title = ''
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
                    name = f"{title} {alt_title} ({year}) {three_d} [{cut} {ratio} {edition} {repack} {resolution} {region} {uhd} {source} {hdr} {video_codec} {audio}{tag}] {lang_tag}"
                    potential_missing = ['edition', 'region', 'distributor']
                elif meta['is_disc'] == 'DVD': 
                    name = f"{title} {alt_title} ({year}) [{cut} {ratio} {edition} {repack} {source} {dvd_size} {audio}{tag}] {lang_tag}"
                    potential_missing = ['edition', 'distributor']
                elif meta['is_disc'] == 'HDDVD':
                    name = f"{title} {alt_title} ({year}) [{cut} {ratio} {edition} {repack} {resolution} {source} {video_codec}] {audio}{tag}] {lang_tag}"
                    potential_missing = ['edition', 'region', 'distributor']
            elif type == "REMUX" and source in ("BluRay", "HDDVD"): #BluRay/HDDVD Remux
                name = f"{title} {alt_title} ({year}) {three_d} [{cut} {ratio} {edition} {repack} {resolution} {uhd} {source} REMUX {hdr} {video_codec} {audio}{tag}] {lang_tag}" 
                potential_missing = ['edition', 'description']
            elif type == "REMUX" and source in ("PAL DVD", "NTSC DVD", "DVD"): #DVD Remux
                name = f"{title} {alt_title} ({year}) [{cut} {ratio} {edition} {repack} {source} REMUX  {audio}{tag}] {lang_tag}" 
                potential_missing = ['edition', 'description']
            elif type == "ENCODE": #Encode
                name = f"{title} {alt_title} ({year}) [{cut} {ratio} {edition} {repack} {resolution} {uhd} {source} {audio} {hdr} {video_encode}{tag}] {lang_tag}"  
                potential_missing = ['edition', 'description']
            elif type == "WEBDL": #WEB-DL
                name = f"{title} {alt_title} ({year}) [{cut} {ratio} {edition} {repack} {resolution} {uhd} {service} WEB-DL {audio} {hdr} {video_encode}{tag}] {lang_tag}"
                potential_missing = ['edition', 'service']
            elif type == "WEBRIP": #WEBRip
                name = f"{title} {alt_title} ({year}) [{cut} {ratio} {edition} {repack} {resolution} {uhd} {service} WEBRip {audio} {hdr} {video_encode}{tag}] {lang_tag}"
                potential_missing = ['edition', 'service']
            elif type == "HDTV": #HDTV
                name = f"{title} {alt_title} ({year}) [{cut} {ratio} {edition} {repack} {resolution} {source} {audio} {video_encode}{tag}] {lang_tag}"
                potential_missing = []
        elif meta['category'] == "TV": #TV SPECIFIC
            if type == "DISC": #Disk
                if meta['is_disc'] == 'BDMV':
                    name = f"{title} ({year}) {alt_title} {season}{episode} {three_d} [{cut} {ratio} {edition} {repack} {resolution} {region} {uhd} {source} {hdr} {video_codec} {audio}{tag}] {lang_tag}"
                    potential_missing = ['edition', 'region', 'distributor']
                if meta['is_disc'] == 'DVD':
                    name = f"{title} {alt_title} {season}{episode} {three_d} [{cut} {ratio} {edition} {repack} {source} {dvd_size} {audio}{tag}] {lang_tag}"
                    potential_missing = ['edition', 'distributor']
                elif meta['is_disc'] == 'HDDVD':
                    name = f"{title} {alt_title} ({year}) [{cut} {ratio} {edition} {repack} {resolution} {source} {video_codec} {audio}{tag}] {lang_tag}"
                    potential_missing = ['edition', 'region', 'distributor']
            elif type == "REMUX" and source in ("BluRay", "HDDVD"): #BluRay Remux
                name = f"{title} ({year}) {alt_title} {season}{episode} {episode_title} {part} [{three_d} {cut} {ratio} {edition} {repack} {resolution} {uhd} {source} REMUX {hdr} {video_codec} {audio}{tag}] {lang_tag}" #SOURCE
                potential_missing = ['edition', 'description']
            elif type == "REMUX" and source in ("PAL DVD", "NTSC DVD"): #DVD Remux
                name = f"{title} ({year}) {alt_title} {season}{episode} {episode_title} {part} [{cut} {ratio} {edition} {repack} {source} REMUX {audio}{tag}] {lang_tag}" #SOURCE
                potential_missing = ['edition', 'description']
            elif type == "ENCODE": #Encode
                name = f"{title} ({year}) {alt_title} {season}{episode} {episode_title} {part} [{cut} {ratio} {edition} {repack} {resolution} {uhd} {source} {audio} {hdr} {video_encode}{tag}] {lang_tag}" #SOURCE
                potential_missing = ['edition', 'description']
            elif type == "WEBDL": #WEB-DL
                name = f"{title} ({year}) {alt_title} {season}{episode} {episode_title} {part} [{cut} {ratio} {edition} {repack} {resolution} {uhd} {service} WEB-DL {audio} {hdr} {video_encode}{tag}] {lang_tag}"
                potential_missing = ['edition', 'service']
            elif type == "WEBRIP": #WEBRip
                name = f"{title} ({year}) {alt_title} {season}{episode} {episode_title} {part} [{cut} {ratio} {edition} {repack} {resolution} {uhd} {service} WEBRip {audio} {hdr} {video_encode}{tag}] {lang_tag}"
                potential_missing = ['edition', 'service']
            elif type == "HDTV": #HDTV
                name = f"{title} ({year}) {alt_title} {season}{episode} {episode_title} {part} [{cut} {ratio} {edition} {repack} {resolution} {source} {audio} {video_encode}{tag}] {lang_tag}"
                potential_missing = []

        parts = name.split()
        if '[' in parts:        
            bracket_index = parts.index('[')
            sq_bracket = next((i for i, part in enumerate(parts[bracket_index+1:]) if part.strip()), None)
            if sq_bracket is not None:
                name = ' '.join(parts[:bracket_index+1]) + ' '.join(parts[bracket_index+1:])
        
        return ' '.join(name.split())
    

    async def search_existing(self, meta):
        dupes = {}
        console.print("[yellow]Searching for existing torrents on site...")
        params = {
            'api_token': self.config['TRACKERS'][self.tracker]['api_key'].strip(),
            'categories[]': await self.get_cat_id(
                meta['category'], meta.get('genres', ''), meta.get('keywords', ''), 
                meta.get('service', ''), meta.get('edition', ''), meta
            ),
            'types[]': await self.get_type_id(meta['type'], meta['edition']),
            'name': meta.get('album', '') if meta.get('is_music', False) else ""
        }

        if not meta.get('is_music', False):
            params.update({
                'tmdbId': meta['tmdb'],
                'resolutions[]': await self.get_res_id(meta['resolution'])
            })

            if meta.get('edition'):
                params['name'] = f"{meta['edition']}".strip()

        try:
            response = requests.get(url=self.search_url, params=params).json()
            for each in response.get('data', []):
                result = each['attributes']['name']
                size = each['attributes']['size']

                # Extract the main part of the name using regex
                match = re.split(r'(-\w*\])', result)
                if len(match) > 1:
                    result = match[0] + match[1]
                
                # Filter results and populate dupes
                if "🔥Eternal" not in result:
                    dupes[result] = size
        except requests.exceptions.RequestException as req_err:
            log.error(f'[bold red]Request error while searching for torrents: {req_err}')
        except Exception as e:
            log.error(f'[bold red]Unexpected error during search: {e}')
            await asyncio.sleep(5)

        log.debug(f'[blue]Dupe List[/blue]:\n {dupes}')
        return dupes