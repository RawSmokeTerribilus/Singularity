import asyncio
import requests
import json
from typing import List, Dict, Any, Optional
import re
from datetime import timedelta
from urllib.parse import urlencode
from src.console import console, log
from rich.prompt import Confirm

class MusicBrainzAPI:
    """A class to interact with the MusicBrainz Web Service."""

    BASE_URL = "https://musicbrainz.org/ws/2/"

    def __init__(self, user_agent: str):
        """Initialize with a user agent string and optionally set debug mode."""
        self.headers = {'User-Agent': user_agent} 
     
    async def _async_request(self, endpoint: str, params: Dict[str, str] = {}) -> Dict[str, Any]:
        """Make an asynchronous GET request to the MusicBrainz API."""
        def sync_request():
            url = self.BASE_URL + endpoint
            try:
                response = requests.get(url, headers=self.headers, params=params)
                response.raise_for_status()
                return response.json()
            except requests.RequestException as e:
                log.error(f"Error fetching data from MusicBrainz: {e}")
                return None

        full_url = f"{self.BASE_URL}{endpoint}?{urlencode(params)}"
        log.dinfo(f"Querying URL: {full_url}")

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, sync_request)

    async def search_artists(self, artist_name: str, limit: int = 25, offset: int = 0) -> Dict[str, Any]:
        """Search for artists asynchronously."""
        params = {"query": f"artist:{artist_name}", "fmt": "json", "limit": str(limit), "offset": str(offset)}
        return await self._async_request("artist", params=params)

    async def search_releases(self, title: str, artist: str = "", limit: int = 100, offset: int = 0) -> Dict[str, Any]:
        """Search for releases (albums) asynchronously."""
        query = f"release:{title}"
        if artist:
            query += f"ANDartist:{artist}"
        params = {"query": query, "fmt": "json", "limit": str(limit), "offset": str(offset)}
        return await self._async_request("release", params=params)

    async def search_by_barcode(self, barcode: str) -> Dict[str, Any]:
        """Search for a release by its barcode asynchronously."""
        params = {"query": f"barcode:{barcode}", "fmt": "json"}
        return await self._async_request("release", params=params)

    async def get_release_by_id(self, mbid: str, includes: Optional[List[str]] = None) -> Dict[str, Any]:
        """Fetch a release by its MBID asynchronously."""
        endpoint = f"release/{mbid}"
        params = {"fmt": "json"}
        if includes:
            params["inc"] = "+".join(includes)
        return await self._async_request(endpoint, params)

    async def get_image_list(self, mbid: str) -> Dict[str, Any]:
        """Fetch the cover art for a release asynchronously."""
        endpoint = f"release/{mbid}/cover-art"
        return await self._async_request(endpoint, {"fmt": "json"})

    async def search_musicbrainz_by_barcode(self, barcode: str, meta: Dict[str, Any]) -> None:
        """Asynchronously search MusicBrainz by barcode and populate meta dictionary."""
        releases = await self.search_by_barcode(barcode)
        log.dinfo("Search by barcode response: %s", releases)  # Debug
        if releases and 'releases' in releases and releases['releases']:
            best_release = releases['releases'][0]
            log.dinfo("Best release found: %s", best_release)  # Debug
            meta['mbid'] = best_release.get('id', '')
            meta['artist'] = best_release['artist-credit'][0]['name']
            meta['album'] = best_release.get('title', '')
            await self.fetch_musicbrainz_mbid(meta['mbid'], meta)
        else:
            log.info(f"No MusicBrainz releases found for barcode {barcode}")

    async def search_by_catalog_number(self, catalog_number: str, meta: Dict[str, Any]) -> None:
        if catalog_number.isdigit():  # Check if it might be a barcode
            releases = await self.search_by_barcode(catalog_number)
            if releases and 'releases' in releases and releases['releases']:
                # Process as barcode results
                meta['mbid'] = releases['releases'][0].get('id', '')
                await self.fetch_musicbrainz_mbid(meta['mbid'], meta)
                return  # Exit the method if a match was found

        # If barcode search did not yield results or not all digits, proceed with catalog number search
        params = {"query": f"catno:{catalog_number}", "fmt": "json"}
        releases = await self._async_request("release", params=params)
        if releases and "releases" in releases and releases["releases"]:
            best_release = releases["releases"][0]  # Assuming the first result is the best match
            meta["mbid"] = best_release.get("id", "")
            await self.fetch_musicbrainz_mbid(meta["mbid"], meta)
        else:
            log.info(f"No MusicBrainz releases found for catalog number {catalog_number}")

    async def search_releases_by_title_artist(self, release_title: str, artist_name: str, track_count: int, meta: Dict[str, Any]) -> None:
        log.info(f'[blue]Artist:[/blue] {artist_name}\n[blue]Album:[/blue] {release_title}\n[blue]Tracks:[/blue] {track_count}')
        search_results = await self.search_releases(release_title, artist=artist_name, limit=100)

        if 'releases' in search_results:
            artist_names = [name.strip().lower() for name in artist_name.split('&')]

            # First, filter for exact track-count matches
            exact_matches = []
            for release in search_results['releases']:
                track_match = 'track-count' in release and int(release['track-count']) == track_count
                artist_match = any(
                    any(artist_name in ac['name'].lower() for artist_name in artist_names)
                    for ac in release.get('artist-credit', [])
                )

                if track_match and artist_match:
                    exact_matches.append(release)

            # Fallback: Flexible matches based on artist
            if not exact_matches:
                approximate_matches = []
                for release in search_results['releases']:
                    artist_match = any(
                        any(artist_name in ac['name'].lower() for artist_name in artist_names)
                        for ac in release.get('artist-credit', [])
                    )
                    if artist_match:
                        approximate_matches.append(release)

                if approximate_matches:
                    closest_release = min(
                        approximate_matches,
                        key=lambda x: abs(int(x.get('track-count', 0)) - track_count)
                    )
                    # Confirm if fuzzy match
                    if not meta.get('unattended', False):
                        release_url = f"https://musicbrainz.org/release/{closest_release['id']}"
                        console.print(
                            f"[yellow]Closest match found:[/yellow]\n"
                            f"[blue]Title:[/blue] {closest_release['title']}\n"
                            f"[blue]Artist(s):[/blue] {', '.join(ac['name'] for ac in closest_release['artist-credit'])}\n"
                            f"[blue]Tracks:[/blue] {closest_release.get('track-count', 'Unknown')}\n"
                            f"[blue]URL:[/blue] {release_url}\n"
                            f"Is this the correct release? [y/N]"
                        )
                        if Confirm.ask("[cyan]Is this the correct release?[/cyan]"):
                            exact_matches = [closest_release]

            # Choose the best match from filtered results
            if exact_matches:
                correct_release = exact_matches[0]
                log.dinfo(f"Correct release: {correct_release}")
                meta['mbid'] = correct_release.get('id', '')
                await self.fetch_musicbrainz_mbid(meta['mbid'], meta)
            else:
                log.info(f"No suitable match for {release_title} by {artist_name} with {track_count} tracks.")
        else:
            log.info(f"No MusicBrainz releases found for {release_title} by {artist_name}")


    async def fetch_musicbrainz_mbid(self, mbid: str, meta: Dict[str, Any]) -> Dict[str, Any]:
        """Asynchronously fetch detailed release information by MBID and populate meta dictionary."""
        release = await self.get_release_by_id(mbid, includes=["recordings", "work-level-rels", "genres", "labels", "url-rels", "release-groups"])
        if release:
            # Fill meta with basic album info
            meta['album'] = release.get('title', meta.get('album'))
            meta['release_date'] = release.get('date', '')
            edition = release.get('disambiguation', '').strip().title()
            corrections = {
                'itunes': 'iTunes', 
                ' for ': ' for ',
                'Cd ': 'CD ',
                'Th ': 'th ',
            }
            for original, correction in corrections.items():
                edition = re.sub(r'\b' + re.escape(original) + r'\b', correction, edition, flags=re.IGNORECASE)
            edition = re.sub(r'(\d)Th', r'\1th', edition)
            manual_edition = meta.get('manual_edition')
            meta['edition'] = manual_edition if manual_edition else edition
            if meta['barcode'] in ['', None, 0] or 'barcode' not in meta:
                meta['barcode'] = release.get('barcode', '')

            media_format = release.get('media', [{}])[0].get('format', '')
            if not meta.get('source'):
                meta['source'] = media_format.replace('Digital Media', 'WEB')   

            meta['tracklist'] = {}
            for medium in release.get('media', []):
                disc_number = medium.get('position', '1')
                meta['tracklist'][f'Disc {disc_number}'] = {}

                for track in medium.get('tracks', []):
                    milliseconds = int(track['recording']['length'])
                    duration = timedelta(milliseconds=milliseconds)
                    minutes, seconds = divmod(duration.seconds, 60)
                    time = f"{minutes:02d}:{seconds:02d}"
                    padding = track['number'].zfill(len(str(len(medium['tracks']))))
                    key = f"{padding}. {track['recording']['title']}"
                    meta['tracklist'][f'Disc {disc_number}'][key] = time

            if release.get('status'):
                status = release['status'].lower()
                if status in ['bootleg', 'unofficial', 'promotion', 'withdrawn']:
                    meta['keywords'] = (meta.get('keywords', '') + f", {status}").strip()

            # Check for release group types and add to keywords
            if 'release-group' in release:
                if release['release-group'].get('primary-type'):
                    release_group_type = release['release-group']['primary-type'].lower()
                    if release_group_type in ['compilation', 'live']:
                        meta['keywords'] = (meta.get('keywords', '') + f", {release_group_type}").strip()

                # Check for secondary types as well
                if 'secondary-types' in release['release-group']:
                    for secondary_type in release['release-group']['secondary-types']:
                        if secondary_type.lower() in ['compilation', 'live']:
                            meta['keywords'] = (meta.get('keywords', '') + f", {secondary_type.lower()}").strip()

            # Fetch genres and append to keywords
            genres = release.get('genres', [])
            if genres:
                genre_names = [genre['name'] for genre in genres]
            else:
                genres = set()
                for medium in release.get('media', []):
                    for track in medium.get('tracks', []):
                        if 'genres' in track['recording']:
                            genres.update([genre['name'] for genre in track['recording']['genres']])
                genre_names = list(genres)

            # Combine existing keywords with genres
            if genre_names:
                current_keywords = meta.get('keywords', '').split(', ')
                current_keywords.extend(genre_names)
                meta['keywords'] = ', '.join(set(current_keywords)).strip()

            # Fetch cover images
            cover_list = await self.get_image_list(mbid)  # Await the coroutine here
            if "images" in cover_list and cover_list["images"]:
                for image in cover_list["images"]:
                    if image.get("approved") and "Front" in image.get("types", []):
                        meta['album_cover'] = image["thumbnails"].get("500") or image["thumbnails"].get("large")
                    if image.get("approved") and "Back" in image.get("types", []):
                        meta['album_back'] = image["thumbnails"].get("500") or image["thumbnails"].get("large")

            # Extract the catalogue number (from label-info)
            label_info = release.get("label-info", [])
            for label in label_info:
                catalog_number = label.get("catalog-number")
                if catalog_number:
                    meta['catalog_number'] = catalog_number
                    break  # Stop after finding the first valid catalogue number

        if 'release-group' in release:
            mbgid = release['release-group']['id']
            release_group = await self.get_release_group_by_id(mbgid)
            all_relations = release.get('relations', []) + release_group.get('relations', [])
            self.process_relations(all_relations, meta)
        else:
            self.process_relations(release.get('relations', []), meta)
        return meta

    def process_relations(self, relations: List[Dict[str, Any]], meta: Dict[str, Any]) -> None:
        """Process relations from either release or release-group and update meta dictionary."""
        for relation in relations:
            if relation.get("type") == "discogs" and "url" in relation:
                discogs_url = relation["url"].get("resource")
                if discogs_url:
                    meta['discogs_url'] = discogs_url
                    match = re.search(r"discogs\.com/release/(\d+)", discogs_url)
                    if match:
                        meta['discogs_id'] = match.group(1)
            elif relation.get("type") == "allmusic" and "url" in relation:
                allmusic_url = relation["url"].get("resource")
                if allmusic_url:
                    meta['allmusic'] = allmusic_url
            elif relation.get("type") == "wikidata" and "url" in relation:
                wikidata_url = relation["url"].get("resource")
                if wikidata_url:
                    meta['wikidata'] = wikidata_url
            elif (relation.get("type") in ["lyrics", "genius"]) and "url" in relation:
                genius_url = relation["url"].get("resource")
                if genius_url and 'genius.com' in genius_url:
                    meta['genius'] = genius_url     

    async def get_release_group_by_id(self, mbgid: str) -> Dict[str, Any]:
        """Fetch a release-group by its MBID asynchronously, including URL relations."""
        endpoint = f"release-group/{mbgid}"
        params = {"fmt": "json", "inc": "url-rels"}
        return await self._async_request(endpoint, params)

    async def get_image_list(self, mbid: str) -> Dict[str, Any]:
        cover_aa = "http://coverartarchive.org/release/"
        url = f"{cover_aa}{mbid}"
        log.dinfo(f"Querying Cover Art Archive: {url}") 

        def sync_request():
            try:
                response = requests.get(url)
                response.raise_for_status()
                return response.json() 
            except requests.RequestException as e:
                log.error(f"Error fetching cover art: {e}")
                return {}

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, sync_request)
