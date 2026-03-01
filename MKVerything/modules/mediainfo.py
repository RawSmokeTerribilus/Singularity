import subprocess
import json
import logging

def get_technical_tags(file_path):
    """Extrae los metadatos técnicos para Sonarr/Radarr."""
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json", 
        "-show_streams", "-show_format", file_path
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0: return {}
    
    data = json.loads(res.stdout)
    tags = {
        "v_codec": "x264", "v_res": "1080p", "v_dyn": "SDR",
        "a_codec": "AC3", "a_chan": "2.0"
    }

    for s in data.get("streams", []):
        if s["codec_type"] == "video":
            tags["v_codec"] = "x265" if s["codec_name"] == "hevc" else "x264"
            tags["v_res"] = f"{s['height']}p"
            if "hdr" in s.get("color_transfer", ""): tags["v_dyn"] = "HDR"
            
        if s["codec_type"] == "audio":
            # Simplificación de nombres de codec para tus etiquetas
            codec = s["codec_name"].upper()
            tags["a_codec"] = "E-AC3" if "EAC3" in codec else codec
            tags["a_chan"] = f"{s['channels']}.1" if s['channels'] > 2 else "2.0"
            break # Nos quedamos con la primera pista de audio

    return tags
