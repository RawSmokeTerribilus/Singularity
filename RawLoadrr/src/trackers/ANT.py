# -*- coding: utf-8 -*-
import os
import asyncio
import requests
import json
import platform
from pathlib import Path
from pymediainfo import MediaInfo

from src.trackers.COMMON import COMMON
from src.console import console


class ANT():

    def __init__(self, config):
        self.config = config
        self.tracker = 'ANT'
        self.source_flag = 'ANT'
        self.search_url = 'https://anthelion.me/api.php'
        self.upload_url = 'https://anthelion.me/api.php'
        self.signature = None
        self.banned_groups = ['3LTON', '4yEo', 'ADE', 'AFG', 'AniHLS', 'AnimeRG', 'AniURL', 'AROMA', 'aXXo', 'Brrip', 'CHD', 'CM8', 
                            'CrEwSaDe', 'd3g', 'DDR', 'DNL', 'DeadFish', 'ELiTE', 'eSc', 'FaNGDiNG0', 'FGT', 'Flights', 'FRDS', 
                            'FUM', 'HAiKU', 'HD2DVD', 'HDS', 'HDTime', 'Hi10', 'ION10', 'iPlanet', 'JIVE', 'KiNGDOM', 'Leffe', 
                            'LiGaS', 'LOAD', 'MeGusta', 'MkvCage', 'mHD', 'mSD', 'NhaNc3', 'nHD', 'NOIVTC', 'nSD', 'Oj', 'Ozlem', 
                            'PiRaTeS', 'PRoDJi', 'RAPiDCOWS', 'RARBG', 'RetroPeeps', 'RDN', 'REsuRRecTioN', 'RMTeam', 'SANTi', 
                            'SicFoI', 'SPASM', 'SPDVD', 'STUTTERSHIT', 'TBS', 'Telly', 'TM', 'UPiNSMOKE', 'URANiME', 'WAF', 'xRed', 
                            'XS', 'YIFY', 'YTS', 'Zeus', 'ZKBL', 'ZmN', 'ZMNT']
        pass

    async def get_flags(self, meta):
        flags = []
        for each in ['Directors', 'Extended', 'Uncut', 'Unrated', '4KRemaster']:
            if each in meta['edition'].replace("'", ""):
                flags.append(each)
        for each in ['Dual-Audio', 'Atmos']:
            if each in meta['audio']:
                flags.append(each.replace('-', ''))
        if meta.get('has_commentary', False):
            flags.append('Commentary')
        if meta['3D'] == "3D":
            flags.append('3D')
        if "HDR" in meta['hdr']:
            flags.append('HDR10')
        if "DV" in meta['hdr']:
            flags.append('DV')
        if "Criterion" in meta.get('distributor', ''):
            flags.append('Criterion')
        if "REMUX" in meta['type']:
            flags.append('Remux')
        return flags

    ###############################################################
    # ####   STOP HERE UNLESS EXTRA MODIFICATION IS NEEDED    ### #
    ###############################################################

    async def upload(self, meta):
        common = COMMON(config=self.config)
        await common.edit_torrent(meta, self.tracker, self.source_flag)
        flags = await self.get_flags(meta)
        if meta['anon'] != 0 or self.config['TRACKERS'][self.tracker].get('anon', False):
            anon = 1
        else:
            anon = 0

        if meta['bdinfo'] is not None:
            bd_dump = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/BD_SUMMARY_00.txt", 'r', encoding='utf-8').read()
            bd_dump = f'[spoiler=BDInfo][pre]{bd_dump}[/pre][/spoiler]'
            path = Path(meta['bdinfo']['path']) / 'STREAM'
            longest_file = max(
                meta['bdinfo']['files'],
                key=lambda x: x.get('length', 0),
                default=None
            )
            if not longest_file:
                longest_file = meta['bdinfo']['files'][0]
            file_name = longest_file['file']
            base_name, extension = Path(file_name).stem, Path(file_name).suffix
            file_name = f"{base_name}{extension.lower()}"
            m2ts = path / file_name
            if m2ts.exists():
                media_info_output = str(MediaInfo.parse(m2ts, output="text", full=False))
                mi_dump = media_info_output.replace('\r\n', '\n')
            else:
                console.print(f"[red]File not found: {m2ts}")
                console.print(f"[yellow]Warning: No MediaInfo found for {m2ts}")
        else:
            mi_dump = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/MEDIAINFO.txt", 'r', encoding='utf-8').read()
        open_torrent = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/[{self.tracker}]{meta['clean_name']}.torrent", 'rb')
        files = {'file_input': open_torrent}
        data = {
            'api_key': self.config['TRACKERS'][self.tracker]['api_key'].strip(),
            'action': 'upload',
            'tmdbid': meta['tmdb'],
            'mediainfo': mi_dump,
            'flags[]': flags,
            'anonymous': anon,
            'screenshots': '\n'.join([x['raw_url'] for x in meta['image_list']][:4])
        }
        if meta['bdinfo'] is not None:
            data.update({
                'media': 'Blu-ray',
                'releasegroup': str(meta['tag'])[1:],
                'release_desc': bd_dump,
                'flagchangereason': "BDMV Uploaded with Uploadrr"})
        if meta['scene']:
            # ID of "Scene?" checkbox on upload form is actually "censored"
            data['censored'] = 1
        headers = {'User-Agent': f'Uploadrr ({platform.system()} {platform.release()})'}
        success = False
        
        if meta['debug'] is False:
            try:
                response = requests.post(url=self.upload_url, files=files, data=data, headers=headers)
                if response.status_code in [200, 201]:
                    response = response.json()
                    success = True
                    try:
                        console.print(response)
                    except Exception:
                        console.print("It may have uploaded, go check")
                        success = False  # Set success to False explicitly if printing fails
            except Exception as e:
                console.print(f"[red]Failed to upload file: {e}[/red]")
                success = False  # Set success to False explicitly if any exception occurs during upload
        else:
            console.print("[cyan]Request Data:")
            console.print(data)

        try:
            open_torrent.close()
        except Exception as e:
            console.print(f"[red]Failed to close torrent file: {e}[/red]")
        return success

    async def edit_desc(self, meta):
        return


    async def search_existing(self, meta):
        dupes = {}
        console.print("[yellow]Searching for existing torrents on site...")
        params = {
            'apikey': self.config['TRACKERS'][self.tracker]['api_key'].strip(),
            't': 'search',
            'o': 'json'
        }
        if str(meta['tmdb']) != "0":
            params['tmdb'] = meta['tmdb']
        elif int(meta['imdb_id'].replace('tt', '')) != 0:
            params['imdb'] = meta['imdb_id']
        try:
            response = requests.get(url='https://anthelion.me/api', params=params)
            response = response.json()
            for each in response['item']:
                largest = each['files'][0]
                for file in each['files']:
                    if int(file['size']) > int(largest['size']):
                        largest = file
                result = largest['name']
                size = largest['size']
                dupes[result] = size
        ## CvT: I have no access to ANT and don't know why their sorting dupes by size. I merely adapted the code to produce the dictionary needed for printout, as well as size comparing.        
        except Exception as e:
            console.print(f'[bold red]Unable to search for existing torrents on site. Either the site is down or your API key is incorrect. Error: {e}')
            await asyncio.sleep(5)

        return dupes