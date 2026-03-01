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

class BLU():

    def __init__(self, config):
        self.config = config
        self.tracker = 'BLU'
        self.source_flag = 'BLU'
        self.search_url = 'https://blutopia.cc/api/torrents/filter'
        self.torrent_url = 'https://blutopia.cc/api/torrents/'
        self.upload_url = 'https://blutopia.cc/api/torrents/upload' 
        self.signature = None
        self.banned_groups = [
            '[Oj]', '3LTON', '4yEo', 'ADE', 'AFG', 'AniHLS', 'AnimeRG', 'AniURL', 'AROMA', 'aXXo', 'Brrip', 'CHD', 'CM8', 'CrEwSaDe', 'd3g', 'DeadFish', 'DNL', 'ELiTE', 'eSc', 'FaNGDiNG0', 'FGT', 'Flights', 
            'FRDS', 'FUM', 'HAiKU', 'HD2DVD', 'HDS', 'HDTime', 'Hi10', 'ION10', 'iPlanet', 'JIVE', 'KiNGDOM', 'Leffe', 'LEGi0N', 'LOAD', 'MeGusta', 'mHD', 'mSD', 'NhaNc3', 'nHD', 'nikt0', 'NOIVTC', 
            'nSD', 'OFT', 'PiRaTeS', 'playBD', 'PlaySD', 'playXD', 'PRODJi', 'RAPiDCOWS', 'RARBG', 'RDN', 'REsuRRecTioN', 'RetroPeeps', 'RMTeam', 'SANTi', 'SicFoI', 'SPASM', 'SPDVD', 'STUTTERSHIT', 'Telly', 'TM', 'TRiToN', 'UPiNSMOKE', 
            'URANiME', 'WAF', 'x0r', 'xRed', 'XS', 'YIFY', 'ZKBL', 'ZmN', 'ZMNT',
            # Note: You cannot add conditional checks here for AOC, EVO, TERMiNAL & ViSION , script will ignore the lists within a list. 
        ]
        
        pass
    
    async def upload(self, meta):
        common = COMMON(config=self.config)
        
        blu_name = meta['name']
        desc_header = ""
        if meta.get('webdv', False):
            blu_name, desc_header = await self.derived_dv_layer(meta)
        manual_name = meta.get('manual_name')
        blu_name = blu_name if not manual_name else manual_name
        await common.edit_torrent(meta, self.tracker, self.source_flag)
        await common.unit3d_edit_desc(meta, self.tracker, comparison=True, desc_header=desc_header)
        cat_id = await self.get_cat_id(meta['category'], meta.get('edition', ''))
        type_id = await self.get_type_id(meta['type'])
        resolution_id = await self.get_res_id(meta['resolution'])
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
        desc = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/[BLU]DESCRIPTION.txt", 'r', encoding='utf-8').read()
        open_torrent = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/[BLU]{meta['clean_name']}.torrent", 'rb')
        nfo_file = meta.get('nfo_file', None) 
        files = {'torrent': ("placeholder.torrent", open_torrent, "application/x-bittorrent")}
        if nfo_file:
            open_nfo = open(nfo_file, 'rb') 
            files['nfo'] = open_nfo       
        data = {
            'name' : blu_name,
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
            'User-Agent': f'Uploadrr ({platform.system()} {platform.release()})'
        }
        params = {
            'api_token': self.config['TRACKERS'][self.tracker]['api_key'].strip()
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


    async def get_cat_id(self, category_name, edition):
        category_id = {
            'MOVIE': '1', 
            'TV': '2', 
            'FANRES': '3'
            }.get(category_name, '0')
        if category_name == 'MOVIE' and 'FANRES' in edition:
            category_id = '3'
        return category_id

    async def get_type_id(self, type):
        type_id = {
            'DISC': '1', 
            'REMUX': '3',
            'WEBDL': '4', 
            'WEBRIP': '5', 
            'HDTV': '6',
            'ENCODE': '12'
            }.get(type, '0')
        return type_id

    async def get_res_id(self, resolution):
        resolution_id = {
            '8640p':'10', 
            '4320p': '11', 
            '2160p': '1', 
            '1440p' : '2',
            '1080p': '2',
            '1080i':'3', 
            '720p': '5',  
            '576p': '6', 
            '576i': '7',
            '480p': '8', 
            '480i': '9'
            }.get(resolution, '10')
        return resolution_id

    async def derived_dv_layer(self, meta):
        name = meta['name']
        desc_header = ""
        # Exit if not DV + HDR
        if not all([x in meta['hdr'] for x in ['HDR', 'DV']]):
            return name, desc_header
        import cli_ui
        console.print("[bold yellow]Generating the required description addition for Derived DV Layers. Please respond appropriately.")
        ask_comp = True
        if meta['type'] == "WEBDL":
            if cli_ui.ask_yes_no("Is the DV Layer sourced from the same service as the video?"):
                ask_comp = False
                desc_header = "[code]This release contains a derived Dolby Vision profile 8 layer. Comparisons not required as DV and HDR are from same provider.[/code]"
        
        if ask_comp:
            while desc_header == "":
                desc_input = cli_ui.ask_string("Please provide comparisons between HDR masters. (link or bbcode)", default="")
                desc_header = f"[code]This release contains a derived Dolby Vision profile 8 layer. Comparisons between HDR masters: {desc_input}[/code]"
        
        if "hybrid" not in name.lower():
            if "REPACK" in name:
                name = name.replace('REPACK', 'Hybrid REPACK')
            else:
                name = name.replace(meta['resolution'], f"Hybrid {meta['resolution']}")
        return name, desc_header


    async def search_existing(self, meta):
        dupes = {}
        console.print("[yellow]Searching for existing torrents on site...")
        params = {
            'api_token' : self.config['TRACKERS'][self.tracker]['api_key'].strip(),
            'tmdbId' : meta['tmdb'],
            'categories[]' : await self.get_cat_id(meta['category'], meta.get('edition', '')),
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
        except Exception as e:
            console.print(f'[bold red]Unable to search for existing torrents on site. Either the site is down or your API key is incorrect. Error: {e}')
            await asyncio.sleep(5)

        return dupes