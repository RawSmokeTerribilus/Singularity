#!/usr/bin/env bash
# Recordrr dev-sync — push local Recordrr code into the RUNNING container without
# an image rebuild. Modules are re-read on each `python3 -m ...` call, so a sync
# is enough during iteration. For real deployment the code is baked via the
# Dockerfile COPY (rebuild) — this is the fast dev loop only.
#
# Usage:  bash Recordrr/dev-sync.sh [container_name]
set -euo pipefail
CONTAINER="${1:-singularity_core}"
SRC="$(cd "$(dirname "$0")" && pwd)"      # .../RaW_Suite/Recordrr
DEST="/app/Recordrr"

echo "Recordrr → $CONTAINER"

# Python code + launcher (baked path; cp overwrites in-place).
CODE=(
  __init__.py launcher.py
  config/__init__.py config/recordrr_config.py
  modules/__init__.py modules/display.py modules/capture.py modules/browser.py
  modules/metadata.py modules/adapter.py modules/orchestrator.py
  modules/audiodiag.py modules/layerdiag.py
)
for f in "${CODE[@]}"; do
  docker cp "$SRC/$f" "$CONTAINER:$DEST/$f" >/dev/null && echo "  ✓ $f"
done

# In-page assets (the injected control bar, etc.).
docker exec "$CONTAINER" mkdir -p "$DEST/assets" >/dev/null 2>&1 || true
shopt -s nullglob
for a in "$SRC"/assets/*; do
  docker cp "$a" "$CONTAINER:$DEST/assets/$(basename "$a")" >/dev/null \
    && echo "  ✓ assets/$(basename "$a")"
done

# Adapter JSON packs (volume-mounted dir; seed/update each).
for j in "$SRC"/config/adapters/*.json; do
  docker cp "$j" "$CONTAINER:$DEST/config/adapters/$(basename "$j")" >/dev/null \
    && echo "  ✓ config/adapters/$(basename "$j")"
done

echo "Done. Re-run the launcher (singularity → 9) to pick up changes."
