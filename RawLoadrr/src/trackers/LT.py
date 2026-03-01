# -*- coding: utf-8 -*-
# import discord
import asyncio
import requests
import json
import os
import platform
from rich.pretty import Pretty
from src.trackers.COMMON import COMMON
from src.console import console


class LT():

    def __init__(self, config):
        self.config = config
        self.tracker = 'LT'
        self.source_flag = 'Lat-Team "Poder Latino"'
        self.upload_url = 'https://lat-team.com/api/torrents/upload'
        self.search_url = 'https://lat-team.com/api/torrents/filter'
        self.signature = None
        self.banned_groups = [""]
        pass
    
    async def get_cat_id(self, category_name):
        category_id = {
            'MOVIE': '1', 
            'TV': '2', 
            }.get(category_name, '0')
        return category_id

    async def get_type_id(self, type):
        type_id = {
            'DISC': '1', 
            'REMUX': '2',
            'WEBDL': '4', 
            'WEBRIP': '5', 
            'HDTV': '6',
            'ENCODE': '3'
            }.get(type, '0')
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


    def get_subs_or_cast(self, meta):
        media_info = meta.get('mediainfo')
        is_disc = meta.get('is_disc', False)
        imdb_info = meta.get('imdb_info', {})

        if is_disc:
            # Check for subtitles in BDMV discs
            if is_disc == 'BDMV':
                disc = meta['discs'][0]
                subtitles = disc['bdinfo'].get('subtitles', [])
                
                if 'spanish' in [s.lower() for s in subtitles]:
                    return ' [SUBS]'
            return ''

        else:
            if not media_info or 'media' not in media_info:
                return ''

            audio_tracks = [track for track in media_info['media']['track'] if track.get('StreamKind_String', '').lower() == 'audio']
            text_tracks = [track for track in media_info['media']['track'] if track.get('StreamKind_String', '').lower() == 'text']
            
            # Check for Spanish audio tracks
            for track in audio_tracks:
                lang = track.get('Language', '')
                lang_string2 = track.get('Language_String2', '').lower()                
                title = track.get('Title', '').lower()
                
                if not any(title.find(word) != -1 for word in ['comment', 'director', 'review']) and not 'Spain' in imdb_info.get('countries_of_origin', []):
                    if lang == 'es-ES':
                        return ' [CAST]'
                    if lang in ('es-419', 'es-CO' ,'es-AR','es-MX'):
                        return ''
                    if lang_string2 == 'es':                        
                        if any(title.find(word) != -1 for word in ['cast', 'euro', 'españa', 'spain']):
                            return ' [CAST]'
                        return ''
                
            # Check for Spanish subtitles if no Spanish audio
            for track in text_tracks:
                language = track.get('Language_String', '').lower()
                if language in ['spanish', 'es']:
                    return ' [SUBS]'

            return ''
            

    async def get_name(self, meta):
        type = meta.get('type', "")
        title = meta.get('title',"")
        original_title = meta.get('original_title', "") 
        year = meta.get('year', "")
        resolution = meta.get('resolution', "")
        if resolution == "OTHER":
            resolution = ""
        audio = meta.get('audio', "").replace('Dubbed', '').replace('Dual-Audio', '')
        subs_or_cast = self.get_subs_or_cast(meta)
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

        if meta.get('original_language', '') in ('es', 'spa'):
            title = original_title            

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
                    name = f"{title} {year} {three_d} {cut} {ratio} {edition} {repack} {resolution} {region} {uhd} {source} {hdr} {video_codec} {audio}{subs_or_cast}{tag}"
                    potential_missing = ['edition', 'region', 'distributor']
                elif meta['is_disc'] == 'DVD': 
                    name = f"{title} {year} {cut} {ratio} {edition} {repack} {source} {dvd_size} {audio}{subs_or_cast}{tag}"
                    potential_missing = ['edition', 'distributor']
                elif meta['is_disc'] == 'HDDVD':
                    name = f"{title} {year} {cut} {ratio} {edition} {repack} {resolution} {source} {video_codec} {audio}{subs_or_cast}{tag}"
                    potential_missing = ['edition', 'region', 'distributor']
            elif type == "REMUX" and source in ("BluRay", "HDDVD"): #BluRay/HDDVD Remux
                name = f"{title} {year} {three_d} {cut} {ratio} {edition} {repack} {resolution} {uhd} {source} REMUX {hdr} {video_codec} {audio}{subs_or_cast}{tag}" 
                potential_missing = ['edition', 'description']
            elif type == "REMUX" and source in ("PAL DVD", "NTSC DVD", "DVD"): #DVD Remux
                name = f"{title} {year} {cut} {ratio} {edition} {repack} {source} REMUX  {audio}{subs_or_cast}{tag}" 
                potential_missing = ['edition', 'description']
            elif type == "ENCODE": #Encode
                name = f"{title} {year} {cut} {ratio} {edition} {repack} {resolution} {uhd} {source} {audio} {hdr} {video_encode}{subs_or_cast}{tag}"  
                potential_missing = ['edition', 'description']
            elif type == "WEBDL": #WEB-DL
                name = f"{title} {year} {cut} {ratio} {edition} {repack} {resolution} {uhd} {service} WEB-DL {audio} {hdr} {video_encode}{subs_or_cast}{tag}"
                potential_missing = ['edition', 'service']
            elif type == "WEBRIP": #WEBRip
                name = f"{title} {year} {cut} {ratio} {edition} {repack} {resolution} {uhd} {service} WEBRip {audio} {hdr} {video_encode}{subs_or_cast}{tag}"
                potential_missing = ['edition', 'service']
            elif type == "HDTV": #HDTV
                name = f"{title} {year} {cut} {ratio} {edition} {repack} {resolution} {source} {audio} {video_encode}{subs_or_cast}{tag}"
                potential_missing = []
        elif meta['category'] == "TV": #TV SPECIFIC
            if type == "DISC": #Disk
                if meta['is_disc'] == 'BDMV':
                    name = f"{title} {year} {season}{episode} {three_d} {cut} {ratio} {edition} {repack} {resolution} {region} {uhd} {source} {hdr} {video_codec} {audio}{subs_or_cast}{tag}"
                    potential_missing = ['edition', 'region', 'distributor']
                if meta['is_disc'] == 'DVD':
                    name = f"{title} {season}{episode} {three_d} {cut} {ratio} {edition} {repack} {source} {dvd_size} {audio}{subs_or_cast}{tag}"
                    potential_missing = ['edition', 'distributor']
                elif meta['is_disc'] == 'HDDVD':
                    name = f"{title} {year} {cut} {ratio} {edition} {repack} {resolution} {source} {video_codec} {audio}{subs_or_cast}{tag}"
                    potential_missing = ['edition', 'region', 'distributor']
            elif type == "REMUX" and source in ("BluRay", "HDDVD"): #BluRay Remux
                name = f"{title} {year} {season}{episode} {episode_title} {part} {three_d} {cut} {ratio} {edition} {repack} {resolution} {uhd} {source} REMUX {hdr} {video_codec} {audio}{subs_or_cast}{tag}" #SOURCE
                potential_missing = ['edition', 'description']
            elif type == "REMUX" and source in ("PAL DVD", "NTSC DVD"): #DVD Remux
                name = f"{title} {year} {season}{episode} {episode_title} {part} {cut} {ratio} {edition} {repack} {source} REMUX {audio}{subs_or_cast}{tag}" #SOURCE
                potential_missing = ['edition', 'description']
            elif type == "ENCODE": #Encode
                name = f"{title} {year} {season}{episode} {episode_title} {part} {cut} {ratio} {edition} {repack} {resolution} {uhd} {source} {audio} {hdr} {video_encode}{subs_or_cast}{tag}" #SOURCE
                potential_missing = ['edition', 'description']
            elif type == "WEBDL": #WEB-DL
                name = f"{title} {year} {season}{episode} {episode_title} {part} {cut} {ratio} {edition} {repack} {resolution} {uhd} {service} WEB-DL {audio} {hdr} {video_encode}{subs_or_cast}{tag}"
                potential_missing = ['edition', 'service']
            elif type == "WEBRIP": #WEBRip
                name = f"{title} {year} {season}{episode} {episode_title} {part} {cut} {ratio} {edition} {repack} {resolution} {uhd} {service} WEBRip {audio} {hdr} {video_encode}{subs_or_cast}{tag}"
                potential_missing = ['edition', 'service']
            elif type == "HDTV": #HDTV
                name = f"{title} {year} {season}{episode} {episode_title} {part} {cut} {ratio} {edition} {repack} {resolution} {source} {audio} {video_encode}{subs_or_cast}{tag}"
                potential_missing = []

        parts = name.split()
        if '[' in parts:        
            bracket_index = parts.index('[')
            sq_bracket = next((i for i, part in enumerate(parts[bracket_index+1:]) if part.strip()), None)
            if sq_bracket is not None:
                name = ' '.join(parts[:bracket_index+1]) + ' '.join(parts[bracket_index+1:])
        
        return ' '.join(name.split())



    async def upload(self, meta):
        common = COMMON(config=self.config)
        await common.edit_torrent(meta, self.tracker, self.source_flag)
        cat_id = await self.get_cat_id(meta['category'])
        type_id = await self.get_type_id(meta['type'])
        resolution_id = await self.get_res_id(meta['resolution'])
        await common.unit3d_edit_desc(meta, self.tracker)
        region_id = await common.unit3d_region_ids(meta.get('region'))
        distributor_id = await common.unit3d_distributor_ids(meta.get('distributor'))
        lt_name = await self.get_name(meta)
        manual_name = meta.get('manual_name')
        if meta['anon'] != 0 or self.config['TRACKERS'][self.tracker].get('anon', False):
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
        open_torrent = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/[{self.tracker}]{meta['clean_name']}.torrent", 'rb')
        nfo_file = meta.get('nfo_file', None)
        files = {'torrent': open_torrent}
        if nfo_file:
            open_nfo = open(nfo_file, 'rb') 
            files['nfo'] = open_nfo
        data = {
            'name' : manual_name or lt_name,
            'description' : desc,
            'mediainfo' : mi_dump,
            'bdinfo' : bd_dump, 
            'category_id' : cat_id,
            'type_id' : type_id,
            'resolution_id' : resolution_id,
            'tmdb' : meta['tmdb'],
            'imdb' : meta['imdb_id'].replace('tt', ''),
            'tvdb' : meta['tvdb_id'],
            'mal' : meta['mal_id'],
            'igdb' : 0,
            'anonymous' : anon,
            'stream' : meta['stream'],
            'sd' : meta['sd'],
            'keywords' : meta['keywords'],
            'personal_release' : int(meta.get('personalrelease', False)),
            'internal' : 0,
            'featured' : 0,
            'free' : 0,
            'doubleup' : 0,
            'sticky' : 0,
        }
        # Internal
        if self.config['TRACKERS'][self.tracker].get('internal', False):
            if meta['tag'] != "" and (meta['tag'][1:] in self.config['TRACKERS'][self.tracker].get('internal_groups', [])):
                data['internal'] = 1
                
        if region_id != 0:
            data['region_id'] = region_id
        if distributor_id != 0:
            data['distributor_id'] = distributor_id
        if meta.get('category') == "TV":
            data['season_number'] = meta.get('season_int', '0')
            data['episode_number'] = meta.get('episode_int', '0')
        headers = {
            'User-Agent': f'Uploadrr ({platform.system()} {platform.release()})'
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


    async def search_existing(self, meta):
        dupes = {}
        console.print("[yellow]Searching for existing torrents on site...")
        params = {
            'api_token' : self.config['TRACKERS'][self.tracker]['api_key'].strip(),
            'tmdbId' : meta['tmdb'],
            'categories[]' : await self.get_cat_id(meta['category']),
            'types[]' : await self.get_type_id(meta['type']),
            'resolutions[]' : await self.get_res_id(meta['resolution']),
            'name' : ""
        }
        if meta['category'] == 'TV':
            params['name'] = params['name'] + f" {meta.get('season', '')}{meta.get('episode', '')}"
        if meta.get('edition', "") != "":
            params['name'] = params['name'] + f" {meta['edition']}"
        try:
            response = requests.get(url=self.search_url, params=params)
            response = response.json()
            for each in response['data']:
                result = each['attributes']['name']
                size = each['attributes']['size']
                dupes[result] = size
        except:
            console.print('[bold red]Unable to search for existing torrents on site. Either the site is down or your API key is incorrect')
            await asyncio.sleep(5)

        return dupes
