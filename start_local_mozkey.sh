#!/usr/bin/env bash
set -euo pipefail

MULTIARCH_DIR="$(dpkg-architecture -qDEB_HOST_MULTIARCH 2>/dev/null || echo "x86_64-linux-gnu")"
export FCITX_ADDON_DIRS="${HOME}/.local/lib/fcitx5:/usr/lib/${MULTIARCH_DIR}/fcitx5"
export MOZKEY_SERVER_DIR="${HOME}/.local/lib/mozkey"

if [[ "${1:-}" == "--restart-server" ]]; then
  pkill -x -f "${HOME}/.local/lib/mozkey/mozc_server" || true
  pkill -x mozc_zenz_scorer || true
fi

echo "Starting fcitx5 with local Mozkey..."
echo "  FCITX_ADDON_DIRS=${FCITX_ADDON_DIRS}"
echo "  MOZKEY_SERVER_DIR=${MOZKEY_SERVER_DIR}"

fcitx5 -r -d
echo "Done! Add 'Mozkey' in Fcitx5 Configuration (fcitx5-configtool) to try it."
