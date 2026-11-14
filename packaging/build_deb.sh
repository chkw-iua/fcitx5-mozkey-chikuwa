#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PKG_NAME="fcitx5-mozkey-chikuwa"
PKG_VERSION="${1:-0.1.0+git20261113}"
ARCH="${DEB_ARCH:-$(dpkg --print-architecture 2>/dev/null || echo "amd64")}"
MULTIARCH_DIR="${DEB_HOST_MULTIARCH:-$(dpkg-architecture -qDEB_HOST_MULTIARCH 2>/dev/null || echo "x86_64-linux-gnu")}"
OUT_DIR="${ROOT_DIR}/packaging/out"
STAGE_DIR="${OUT_DIR}/${PKG_NAME}_${PKG_VERSION}_${ARCH}"
DEB_PATH="${OUT_DIR}/${PKG_NAME}_${PKG_VERSION}_${ARCH}.deb"

BAZEL_BIN="${ROOT_DIR}/upstream/src/bazel-bin"
LLAMA_SERVER="${ROOT_DIR}/llama.cpp/build/bin/llama-server"
MODEL_DEFAULT_UPSTREAM="${ROOT_DIR}/upstream/src/win32/installer/zenz_runtime/models/zenz-v3.2-small-Q5_K_M.gguf"
MODEL_DEFAULT_LOCAL="${HOME}/.local/lib/mozkey/ZenzRuntime/models/zenz-v3.2-small-Q5_K_M.gguf"
MODEL_DEFAULT_SYS="/usr/lib/mozkey/ZenzRuntime/models/zenz-v3.2-small-Q5_K_M.gguf"
if [[ -n "${MOZKEY_MODEL_PATH:-}" ]]; then
  MODEL_SRC="${MOZKEY_MODEL_PATH}"
elif [[ -f "${MODEL_DEFAULT_UPSTREAM}" ]]; then
  MODEL_SRC="${MODEL_DEFAULT_UPSTREAM}"
elif [[ -f "${MODEL_DEFAULT_LOCAL}" ]]; then
  MODEL_SRC="${MODEL_DEFAULT_LOCAL}"
else
  MODEL_SRC="${MODEL_DEFAULT_SYS}"
fi

for required in \
  "${BAZEL_BIN}/server/mozc_server" \
  "${BAZEL_BIN}/gui/tool/mozc_tool" \
  "${BAZEL_BIN}/zenz_scorer/mozc_zenz_scorer" \
  "${BAZEL_BIN}/zenz_scorer/mozc_zenz_guard" \
  "${BAZEL_BIN}/unix/fcitx5/fcitx5-mozkey.so" \
  "${LLAMA_SERVER}" \
  "${MODEL_SRC}"; do
  if [[ ! -f "${required}" ]]; then
    echo "Missing required artifact: ${required}" >&2
    exit 1
  fi
done

rm -rf "${STAGE_DIR}"
mkdir -p \
  "${STAGE_DIR}/DEBIAN" \
  "${STAGE_DIR}/usr/lib/mozkey/ZenzRuntime/models" \
  "${STAGE_DIR}/usr/lib/${MULTIARCH_DIR}/fcitx5" \
  "${STAGE_DIR}/usr/share/fcitx5/addon" \
  "${STAGE_DIR}/usr/share/fcitx5/inputmethod" \
  "${STAGE_DIR}/etc/apparmor.d/abstractions/mozc.d"

install -m 755 "${BAZEL_BIN}/server/mozc_server" "${STAGE_DIR}/usr/lib/mozkey/mozc_server"
install -m 755 "${BAZEL_BIN}/gui/tool/mozc_tool" "${STAGE_DIR}/usr/lib/mozkey/mozc_tool"
install -m 755 "${BAZEL_BIN}/zenz_scorer/mozc_zenz_scorer" "${STAGE_DIR}/usr/lib/mozkey/ZenzRuntime/mozc_zenz_scorer"
install -m 755 "${BAZEL_BIN}/zenz_scorer/mozc_zenz_guard" "${STAGE_DIR}/usr/lib/mozkey/ZenzRuntime/mozc_zenz_guard"
install -m 755 "${LLAMA_SERVER}" "${STAGE_DIR}/usr/lib/mozkey/ZenzRuntime/llama-server"
install -m 644 "${MODEL_SRC}" "${STAGE_DIR}/usr/lib/mozkey/ZenzRuntime/models/zenz-v3.2-small-Q5_K_M.gguf"

install -m 755 "${BAZEL_BIN}/unix/fcitx5/fcitx5-mozkey.so" "${STAGE_DIR}/usr/lib/${MULTIARCH_DIR}/fcitx5/fcitx5-mozkey.so"
install -m 644 "${ROOT_DIR}/packaging/fcitx5/addon/mozkey.conf" "${STAGE_DIR}/usr/share/fcitx5/addon/mozkey.conf"
install -m 644 "${ROOT_DIR}/packaging/fcitx5/inputmethod/mozkey.conf" "${STAGE_DIR}/usr/share/fcitx5/inputmethod/mozkey.conf"
install -m 644 "${ROOT_DIR}/packaging/apparmor/mozkey" "${STAGE_DIR}/etc/apparmor.d/abstractions/mozc.d/mozkey"

mkdir -p "${STAGE_DIR}/usr/share/doc/${PKG_NAME}"
install -m 644 "${ROOT_DIR}/packaging/copyright" "${STAGE_DIR}/usr/share/doc/${PKG_NAME}/copyright"
install -m 644 "${ROOT_DIR}/LICENSE" "${STAGE_DIR}/usr/share/doc/${PKG_NAME}/LICENSE"

if grep -q "mozcdic_ut_daily_local" "${ROOT_DIR}/upstream/src/data/dictionary_oss/BUILD.bazel"; then
  install -m 644 "${ROOT_DIR}/upstream/src/data/installer/DICTIONARY_NOTICES.md" "${STAGE_DIR}/usr/share/doc/${PKG_NAME}/DICTIONARY_NOTICES.md"
  install -m 644 "${ROOT_DIR}/upstream/src/data/installer/SudachiDict-LEGAL.txt" "${STAGE_DIR}/usr/share/doc/${PKG_NAME}/SudachiDict-LEGAL.txt"
fi

cat > "${STAGE_DIR}/DEBIAN/conffiles" <<'EOF'
/etc/apparmor.d/abstractions/mozc.d/mozkey
EOF

cat > "${STAGE_DIR}/DEBIAN/control" <<EOF
Package: ${PKG_NAME}
Version: ${PKG_VERSION}
Section: utils
Priority: optional
Architecture: ${ARCH}
Conflicts: mozkey
Replaces: mozkey
Depends: fcitx5, libc6, libstdc++6, libgcc-s1, libgomp1, libssl3t64, libqt6core6t64, libqt6gui6, libqt6widgets6, libqt6dbus6, libfcitx5core7, libfcitx5config6, libfcitx5utils2
Maintainer: ${DEB_MAINTAINER:-fcitx5-mozkey-chikuwa contributors <275224335+chkw-iua@users.noreply.github.com>}
Description: Mozkey Japanese IME for Fcitx5 with Live Conversion and Zenz AI
 Coexists safely with stock fcitx5-mozc and mozc-server using a separate
 @tmp/.mozkey.* abstract socket namespace and /usr/lib/mozkey directory.
EOF

cat > "${STAGE_DIR}/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -e
if command -v systemctl >/dev/null 2>&1 && systemctl is-active --quiet apparmor; then
  systemctl reload apparmor || true
fi
EOF
chmod 755 "${STAGE_DIR}/DEBIAN/postinst"

dpkg-deb --build --root-owner-group "${STAGE_DIR}" "${DEB_PATH}"
rm -rf "${STAGE_DIR}"
echo "Built package: ${DEB_PATH}"
dpkg-deb -I "${DEB_PATH}"
