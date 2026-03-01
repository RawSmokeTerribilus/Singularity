import bencode # Necesitarás instalarlo: pip install bencode.py
import hashlib

def analizar_torrent(ruta):
    with open(ruta, 'rb') as f:
        data = bencode.decode(f.read())
        info = data['info']
        info_encoded = bencode.encode(info)
        info_hash = hashlib.sha1(info_encoded).hexdigest()
        print(f"Archivo: {ruta}")
        print(f"InfoHash: {info_hash}")
        print(f"Campos en 'info': {info.keys()}")
        print(f"Announce: {data['announce']}\n")

analizar_torrent("[MILNU]Cowboy Bebop S01 1080p HDTV DD 5.1 x265.torrent")
analizar_torrent("[Milnueve]Cowboy.Bebop.S01.1080p.HDTV.DD.5.1.x265.torrent")
