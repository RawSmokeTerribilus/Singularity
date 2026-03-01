# -*- coding: utf-8 -*-
import asyncio
import requests
import json
import os
import platform
from rich.pretty import Pretty
from src.trackers.COMMON import COMMON
from src.console import console
from src.rate_limiter import rate_limiter
from src.logger import get_logger


class EMU():
    def __init__(self, config):
        self.config = config
        self.tracker = 'EMU'
        self.source_flag = 'eMuwarez'
        self.upload_url = 'https://emuwarez.com/api/torrents/upload'
        self.search_url = 'https://emuwarez.com/api/torrents/filter'
        self.banned_groups = [""]
        self.logger = get_logger(self.tracker)
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

    async def upload(self, meta):
        common = COMMON(config=self.config)
        await common.edit_torrent(meta, self.tracker, self.source_flag)
        cat_id = await self.get_cat_id(meta['category'])
        type_id = await self.get_type_id(meta['type'])
        resolution_id = await self.get_res_id(meta['resolution'])
        await common.unit3d_edit_desc(meta, self.tracker)
        region_id = await common.unit3d_region_ids(meta.get('region'))
        distributor_id = await common.unit3d_distributor_ids(meta.get('distributor'))
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
        manual_name = meta.get('manual_name')
        data = {
            'name' : manual_name or self.emu_name(meta),
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
                # Respect rate limiter
                await rate_limiter.acquire(self.tracker)
                
                response = requests.post(url=self.upload_url, files=files, data=data, headers=headers, params=params, timeout=60)
                
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
        console.print(f"[yellow]Searching for existing torrents on {self.tracker}...")
        params = {
            'api_token' : self.config['TRACKERS'][self.tracker]['api_key'].strip(),
            'tmdbId' : meta['tmdb'],
            'categories[]' : await self.get_cat_id(meta['category']),
            'types[]' : await self.get_type_id(meta['type']),
            'resolutions[]' : await self.get_res_id(meta['resolution']),
            'name' : ""
        }
        if meta.get('edition', "") != "":
            params['name'] = params['name'] + f" {meta['edition']}"
        
        # Retry logic for dupe search (timeout issues possible)
        max_retries = 2
        timeout = 15  # seconds
        
        for attempt in range(max_retries):
            try:
                # Respect rate limiter
                await rate_limiter.acquire(self.tracker)
                
                response = requests.get(url=self.search_url, params=params, timeout=timeout)
                response = response.json()
                for each in response['data']:
                    result = each['attributes']['name']
                    size = each['attributes']['size']
                    dupes[result] = size
                self.logger.debug(f"Dupe search found {len(dupes)} results")
                break  # Success, exit retry loop
                
            except requests.exceptions.Timeout:
                self.logger.warning(f"Dupe search timeout (attempt {attempt+1}/{max_retries})")
                if attempt < max_retries - 1:
                    console.print(f"[yellow]Timeout searching dupes, retrying... (attempt {attempt+1}/{max_retries})")
                    await asyncio.sleep(2)  # Wait before retry
                else:
                    console.print('[bold yellow]Timeout: Proceeding without dupe check')
                    self.logger.warning("Skipping dupe check due to repeated timeouts")
                    
            except Exception as e:
                console.print('[bold red]Unable to search for existing torrents on site. Either the site is down or your API key is incorrect')
                self.logger.error(f"Dupe search error: {str(e)}")
                break

        return dupes


    def emu_name(self, meta):
        built_name = meta['name']
        title = meta.get('title', '')
        aka = meta.get('aka', "")
        og_title = meta.get('original_title', "")
        
        if meta.get('original_language', '') in ('es', 'spa') and og_title:
            emu_name = built_name.replace(title, og_title).strip()
        else: 
            emu_name = built_name
            
        # Validate length
        while len(emu_name) > 255:
            original_len = len(emu_name)
            if aka:
                emu_name = emu_name.replace(aka, '')
            if len(emu_name) <= 255:
                break
            
            resolution = meta.get('resolution', '')
            if resolution:
                emu_name = emu_name.replace(resolution, '')
            
            if len(emu_name) <= 255:
                break
            type = meta.get('type', '')
            if type:
                emu_name = emu_name.replace(type, '')
            if len(emu_name) <= 255:
                break
            
            if len(emu_name) == original_len:
                # Break if no change in length to prevent infinite loop
                break
        return emu_name[:255]
