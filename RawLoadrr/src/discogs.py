import aiohttp
import re
from src.console import console, log
from typing import Optional, Dict, Any

class DiscogsAPI:
    BASE_URL = "https://api.discogs.com/releases/"

    def __init__(self, user_agent: str):
        self.user_agent = user_agent

    async def fetch_discogs_release(self, discogs_id: str) -> Optional[Dict[str, Any]]:
        """Fetch release metadata from Discogs using the release ID."""
        url = f"{self.BASE_URL}{discogs_id}"
        headers = {"User-Agent": self.user_agent}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                print(f"Discogs API Error: {response.status}")
                return None

    def extract_barcode(self, release_data: Dict[str, Any]) -> Optional[str]:
        """Extract barcode from Discogs release data."""
        identifiers = release_data.get("identifiers", [])
        for identifier in identifiers:
            if identifier.get("type") == "Barcode" and identifier.get("description", "").lower() == "scanned":
                return identifier.get("value")
            elif identifier.get("type") == "Barcode" and identifier.get("description", "").lower() == "text":
                return identifier.get("value").replace(" ", "")    
        return None

    def extract_metadata(self, release_data: Dict[str, Any], meta: Dict[str, Any]) -> None:
        """Extract relevant metadata from Discogs release data and populate meta."""        
        # formats = release_data.get("formats", [])
        # if formats and not meta.get('source'): 
        #     meta['source'] = formats[0].get("name", "").upper()
        genres = release_data.get("genres", [])
        styles = release_data.get("styles", [])
        
        new_keywords = ", ".join(genres + styles).replace(' & ', ' ')
        if new_keywords:  
            if meta.get('keywords'):
                meta['keywords'] += ", " + new_keywords
            else:
                meta['keywords'] = new_keywords 

        if not meta.get('tracklist'):
            tracklist = release_data.get("tracklist", [])
            if tracklist:
                meta['tracklist'] = {}               
                for track in tracklist:
                    position = track.get("position", "")
                    
                    if '-' in position:
                        disc_number, track_number = position.split('-', 1)
                        disc_number = f"Disc {disc_number}"  # Format as "Disc 1", "Disc 2", etc.
                    else:
                        disc_number = "Disc 1" 
                        track_number = position
                    
                    if disc_number not in meta['tracklist']:
                        meta['tracklist'][disc_number] = {}

                    # Format track title and add duration
                    track_title = track.get("title", "Unknown Track")
                    duration = track.get("duration", "") 
                    padding = str(track_number).zfill(len(str(len(tracklist))))  # Pad the track number
                    
                    key = f"{padding}. {track_title}"
                    
                    meta['tracklist'][disc_number][key] = duration

        if not meta.get('artist'):
            meta['artist'] = ", ".join(artist.get("name", "") for artist in release_data.get("artists", []))
        
        if not meta.get('album'):
            meta['album'] = release_data.get("title", "")

        if not meta.get('year'):
            meta['year'] = release_data.get("year", None)

        if not meta.get('discogs_id'):
            meta['discogs_id'] = release_data.get("id", None)

            
    async def fetch_master_data(self, master_id: str) -> Optional[Dict[str, Any]]:
        """Fetch master release metadata from Discogs using the master ID."""
        url = f"https://api.discogs.com/masters/{master_id}"
        headers = {"User-Agent": self.user_agent}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                log.error(f"Discogs API Error when fetching master data: {response.status}")
                return None