# Recordrr — POC capture spike (make-or-break)

Goal: prove a Playwright-driven **real Chrome** on a virtual display can capture
**clean ~1080p video, not a black frame**, off a soft target (Pluto / RTVE).
If this passes we build the orchestrator + adapters. If a service blanks it, that
service moves to the OBS+real-display fallback backend.

> Nothing here touches DRM keys. It records the decoded pixels Chrome already
> paints — same as a manual OBS browser capture.

## 0. Build the image (additive layers; zimg/VapourSynth forge untouched)

```bash
cd ~/scripts/Media-Management/RaW_Suite
# rebuild only re-runs the new Chrome/Xvfb layer + requirements; base stays cached
docker compose build
docker compose up -d
```

Set the output dir in `config/.env` (must be the real host path, the bind mount
preserves it inside the container):

```
RECORDRR_OUTPUT=/home/rawserver/Vídeos/PARA-IMPORTAR
```

## 1. Bring up display + audio + VNC (inside the container)

```bash
docker exec -it singularity_core python3 -m Recordrr.modules.display up --vnc
```

Prints the DISPLAY (`:99`), the audio monitor (`recordrr.monitor`), and the VNC
port (`5900`, localhost-only).

## 2. Launch real Chrome on the virtual display + log in once

```bash
docker exec -it -e DISPLAY=:99 singularity_core \
  python3 -m Recordrr.modules.browser https://www.pluto.tv/ poc
```

From your workstation, tunnel and open a VNC viewer to do the one-time login +
press play on an episode:

```bash
ssh -L 5900:127.0.0.1:5900 rawserver        # host already runs the container
# then connect a VNC viewer to 127.0.0.1:5900
```

The browser command keeps polling and prints `video_state` — confirm
`currentTime` is advancing and `width/height` ~1920x1080. The `poc` profile
persists the login for next time.

## 3. Capture 60 s and inspect

In a second terminal, while playback runs:

```bash
docker exec -it singularity_core python3 -m Recordrr.modules.capture \
  /home/rawserver/Vídeos/PARA-IMPORTAR/poc.mkv 60
```

It prints `ffprobe` at the end. **Verdict:**

- Open `poc.mkv` in mpv. Real frames + in-sync audio at ~1080p → **POC passes.**
- Black frame / downgraded res / no audio → capture-detection on that service →
  retry the same clip on the OBS+real-display fallback (next build step).

## 4. Tear down

```bash
docker exec -it singularity_core python3 -m Recordrr.modules.display down
```

## Knobs (all env, set in config/.env — nothing hardcoded)

| var | default | meaning |
|-----|---------|---------|
| `RECORDRR_W` / `RECORDRR_H` | 1920 / 1080 | Xvfb + capture geometry |
| `RECORDRR_FPS` | 30 | capture framerate |
| `RECORDRR_VCODEC` | h264_vaapi | `hevc_vaapi` to encode HEVC at capture time |
| `RECORDRR_QP` | 22 | VAAPI quality |
| `RECORDRR_VAAPI` | /dev/dri/renderD128 | GPU render node |
| `RECORDRR_OUTPUT` | — | host PARA-IMPORTAR path (set this) |
| `RECORDRR_BACKEND` | xvfb | `obs` to use the fallback backend (later) |
