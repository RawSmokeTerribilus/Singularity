# ☣️ Chaos-Maker.py | Auditor de Estrés para MKV ☣️

Este script es una herramienta de **corrupción controlada** diseñada exclusivamente para entornos de desarrollo y pruebas de integridad.

---

## 📋 ÍNDICE / INDEX
1. [⚠️ ADVERTENCIA / WARNING](#-advertencia--warning)
2. [🇪🇸 Guía en Español](#-guía-en-español)
   * [Objetivo](#objetivo)
   * [Uso](#uso)
3. [🇺🇸 English Guide](#-english-guide)
   * [Purpose](#purpose)
   * [Usage](#usage)
4. [⚙️ Detalles Técnicos / Technical Details](#️-detalles-técnicos--technical-details)

---

## ⚠️ ADVERTENCIA / WARNING

> ### 💀 ¡PELIGRO! / DANGER! 💀
> **ESTE SCRIPT DAÑA PERMANENTEMENTE LOS ARCHIVOS.** > No existe una función de "deshacer". Está diseñado para **ROMPER** datos.
> 
> * **NUNCA** lo ejecutes sobre tu biblioteca personal.
> * **NUNCA** lo uses si no tienes una copia de seguridad externa.
> * **SOLO** para uso en carpetas de `/TESTING` aisladas.
>
> **THIS SCRIPT PERMANENTLY DAMAGES FILES.** > There is no "undo" function. It is designed to **BREAK** data.
> * **NEVER** run this on your personal library.
> * **NEVER** use it without an external backup.
> * **ONLY** for use in isolated `/TESTING` folders.

---

## 🇪🇸 Guía en Español

### Objetivo
El propósito de `chaos-maker.py` es verificar si tu sistema de auditoría (como el módulo *Verifier*) es realmente capaz de detectar errores de integridad en el stream de datos de un vídeo, incluso cuando los metadatos parecen correctos. 

Es útil para calibrar el rigor de tus herramientas de escaneo: si el "Chaos Maker" rompe un archivo y **MKVerything** lo localiza y arregla, el flujo de trabajo es sólido.

### Uso
1. Copia archivos `.mkv`, `.avi`, `.mp4`, una `.iso` de prueba y el script `chaos-maker.py` a una carpeta de trabajo limpia.
2. Ejecuta el script (por defecto actúa sobre la carpeta actual):
    ```bash
    python3 chaos-maker.py
    ```
3. El script inyectará ruido binario en puntos estratégicos del vídeo.
4. Ejecuta **MKVerything** en **GODmode** sobre la carpeta de pruebas. El programa debería: analizar, detectar los `.mkv` rotos, arreglarlos, convertir todo el legacy a `.mkv`, sacar un remux de la ISO a `.mkv` y volver a analizar todo arrojando cero fallos.

---

## 🇺🇸 English Guide

### Purpose
The goal of `chaos-maker.py` is to test if your auditing system (such as the *Verifier* module) is truly capable of detecting integrity errors within the video data stream, even when the metadata appears intact.

It is ideal for calibrating the rigor of your scanning tools: if "Chaos Maker" breaks a file and **MKVerything** successfully locates and fixes it, your workflow is solid.

### Usage
1. Copy test `.mkv`, `.avi`, `.mp4` files, a test `.iso`, and the `chaos-maker.py` script into a clean workspace folder.
2. Run the script (it targets the current directory by default):
    ```bash
    python3 chaos-maker.py
    ```
3. The script will inject binary noise at strategic points within the video.
4. Run **MKVerything** in **GODmode** on the test folder. It should: analyze and detect the broken `.mkv` files, fix them, convert all legacy files to `.mkv`, remux the ISO into an `.mkv`, and re-analyze everything, resulting in zero errors.

---

## ⚙️ Detalles Técnicos / Technical Details

* **Target:** Archivos `.mkv` (case-insensitive).
* **Method:** Inyección de **128KB** de ruido aleatorio (`os.urandom`).
* **Safety Margin:** El script salta los primeros **10MB** (aprox.) para mantener las cabeceras EBML intactas. Si el archivo es muy pequeño, el daño se ajusta proporcionalmente; si el Verifier no detecta error en archivos minúsculos, es porque la corrupción quedó por debajo del umbral crítico de datos.
* **Persistence:** Implementa `os.fsync()` para asegurar que el daño se escriba físicamente en el disco.
* **Dynamic Offset:** Si el archivo es pequeño (<20MB), el punto de ataque se ajusta automáticamente para evitar errores de escritura fuera de los límites del archivo.

---
_Creado para el proyecto MKVerything - RaW_Suite_
