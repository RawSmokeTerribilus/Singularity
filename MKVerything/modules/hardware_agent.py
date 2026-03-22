import os
import subprocess

class HardwareAgent:
    def __init__(self):
        self.device = self._detect_hardware()
        # Mapeo de Encoders: [H264, HEVC]
        self.codecs = {
            "nvidia": ["h264_nvenc", "hevc_nvenc"],
            "intel":  ["h264_qsv", "hevc_qsv"],
            "amd":    ["h264_vaapi", "hevc_vaapi"],
            "cpu":    ["libx264", "libx265"]
        }

    def _detect_hardware(self):
        # 1. ¿Hay Nvidia?
        if os.path.exists("/dev/nvidia0"):
            return "nvidia"
        
        # 2. ¿Hay Intel o AMD? (Vía Render Node)
        if os.path.exists("/dev/dri/renderD128"):
            try:
                # Consultamos al sistema qué VGA tiene
                gpu_info = subprocess.check_output("lspci", shell=True).decode().lower()
                if "intel" in gpu_info: return "intel"
                if "amd" in gpu_info or "ati" in gpu_info: return "amd"
            except:
                return "cpu" # Ante la duda, seguridad
        return "cpu"

    def get_transcode_args(self, target_codec="h264"):
        idx = 0 if target_codec == "h264" else 1
        encoder = self.codecs[self.device][idx]

        if self.device == "nvidia":
            return f"-c:v {encoder} -preset p4 -tune hq -pix_fmt yuv420p"
        
        elif self.device in ["intel", "amd"]:
            # Validamos si el driver responde antes de intentar el encode
            try:
                subprocess.run(["vainfo"], capture_output=True, check=True)
                return f"-vaapi_device /dev/dri/renderD128 -vf 'format=nv12,hwupload' -c:v {encoder}"
            except:
                # Fallback de emergencia si el driver (Mesa) está capado como en RHEL
                return f"-c:v {self.codecs['cpu'][idx]} -preset medium -crf 22"
        
        return f"-c:v {encoder} -preset medium -crf 22"
