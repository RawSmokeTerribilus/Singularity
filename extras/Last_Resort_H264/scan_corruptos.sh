#!/bin/bash

# --- RECON CONFIG ---
TARGET_DIR="${1:-$PWD}"
# Logs con rutas absolutas
export OUT_MPEG4="$PWD/recon_mpeg4.txt"
export OUT_BROKEN="$PWD/recon_broken_timestamps.txt"

# Limpieza de zona de guerra
> "$OUT_MPEG4"
> "$OUT_BROKEN"

check_file() {
    local file="$1"
    
    # El comando que validamos: saca codecs y duration en una sola línea plana
    local info
    info=$(ffprobe -v error -show_entries format=duration:stream=codec_name -of default=noprint_wrappers=1:nokey=1 "$file" | tr '\n' ' ')
    
    # 1. ¿Está el archivo vacío o es totalmente ilegible?
    if [[ -z "$info" ]]; then
        echo "$file" >> "$OUT_BROKEN"
        return
    fi

    # 2. ¿Es tecnología legacy que queremos quemar (mpeg4/xvid/divx)?
    if [[ "$info" =~ mpeg4|xvid|divx|msmpeg4 ]]; then
        echo "$file" >> "$OUT_MPEG4"
        return
    fi

    # 3. EL CRITERIO DE LEPRA REAL:
    # Si no hay un número decimal (la duración) al final de la cadena, 
    # es que el índice del contenedor está truncado o corrupto.
    if [[ ! "$info" =~ [0-9]+\.[0-9]+ ]]; then
        echo "$file" >> "$OUT_BROKEN"
    fi
}

export -f check_file

echo "Iniciando Triaje Táctico (V3) en: $TARGET_DIR"
echo "Buscando lepra estructural y legacy MPEG4..."

find "$TARGET_DIR" -type f \( -iname "*.mkv" -o -iname "*.mp4" -o -iname "*.avi" \) -print0 | xargs -0 -I {} -P 8 bash -c 'check_file "$@"' _ {}

echo "------------------------------------------------"
echo "RECON FINALIZADO:"
echo "------------------------------------------------"
printf "MPEG4/Legacy detectados: %d\n" $(wc -l < "$OUT_MPEG4")
printf "Timestamps/Índices ROTOS: %d\n" $(wc -l < "$OUT_BROKEN")
echo "------------------------------------------------"
