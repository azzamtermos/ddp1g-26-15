#!/usr/bin/env bash
set -euo pipefail

APP_NAME="Rapihin Aja"
PKG_NAME="rapihin-aja"
VERSION="0.3.0"
MAINTAINER="Tim Rapihin Aja <dev@rapihin-aja.local>"

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

if [[ -x "$PROJECT_ROOT/.venv/bin/pyinstaller" ]]; then
    PYINSTALLER_BIN="$PROJECT_ROOT/.venv/bin/pyinstaller"
elif command -v pyinstaller >/dev/null 2>&1; then
    PYINSTALLER_BIN="$(command -v pyinstaller)"
else
    echo "Error: PyInstaller tidak ditemukan di .venv/bin/pyinstaller maupun PATH."
    echo "Silakan instal terlebih dahulu: .venv/bin/pip install pyinstaller"
    exit 1
fi

if ! command -v dpkg >/dev/null 2>&1 || ! command -v dpkg-deb >/dev/null 2>&1; then
    echo "Error: perintah dpkg / dpkg-deb tidak tersedia di sistem ini."
    exit 1
fi

ARCH="$(dpkg --print-architecture)"
echo "=== Memulai build $APP_NAME v$VERSION ($ARCH) ==="

rm -rf "$PROJECT_ROOT/build/deb_staging" "$PROJECT_ROOT/dist/$PKG_NAME"

"$PYINSTALLER_BIN" \
    --noconfirm \
    --clean \
    --onedir \
    --noconsole \
    --name "$PKG_NAME" \
    --add-data "data:data" \
    --add-data "ui/styles.qss:ui" \
    --add-data "assets:assets" \
    main.py

BUNDLE_DIR="$PROJECT_ROOT/dist/$PKG_NAME"
if [[ ! -x "$BUNDLE_DIR/$PKG_NAME" ]]; then
    echo "Error: hasil build PyInstaller tidak ditemukan di $BUNDLE_DIR/$PKG_NAME"
    exit 1
fi

STAGING_DIR="$PROJECT_ROOT/build/deb_staging/${PKG_NAME}_${VERSION}_${ARCH}"
rm -rf "$STAGING_DIR"

mkdir -p \
    "$STAGING_DIR/DEBIAN" \
    "$STAGING_DIR/opt/$PKG_NAME" \
    "$STAGING_DIR/usr/bin" \
    "$STAGING_DIR/usr/share/applications" \
    "$STAGING_DIR/usr/share/icons/hicolor/256x256/apps"

cp -a "$BUNDLE_DIR/." "$STAGING_DIR/opt/$PKG_NAME/"

cat <<EOF > "$STAGING_DIR/usr/bin/$PKG_NAME"
#!/usr/bin/env bash
exec /opt/$PKG_NAME/$PKG_NAME "\$@"
EOF
chmod 755 "$STAGING_DIR/usr/bin/$PKG_NAME"

cp "$PROJECT_ROOT/assets/icon.png" \
    "$STAGING_DIR/usr/share/icons/hicolor/256x256/apps/$PKG_NAME.png"

cat <<EOF > "$STAGING_DIR/usr/share/applications/$PKG_NAME.desktop"
[Desktop Entry]
Type=Application
Name=$APP_NAME
Comment=Alat perapi file otomatis yang aman, offline, dan mendukung pembatalan 1-klik
Exec=/usr/bin/$PKG_NAME
Icon=$PKG_NAME
Terminal=false
Categories=Utility;Office;
StartupWMClass=$PKG_NAME
EOF
chmod 644 "$STAGING_DIR/usr/share/applications/$PKG_NAME.desktop"

cat <<EOF > "$STAGING_DIR/DEBIAN/control"
Package: $PKG_NAME
Version: $VERSION
Section: utils
Priority: optional
Architecture: $ARCH
Maintainer: $MAINTAINER
Description: $APP_NAME - Perapi file otomatis offline dengan karantina duplikat aman dan Undo 1-klik
 Aplikasi desktop berbasis PyQt6 untuk mengelompokkan file secara otomatis,
 memberi saran nama file rapi secara offline, mengamankan duplikat ke karantina,
 serta menyediakan fitur pembatalan (Undo) yang aman.
EOF

chmod 755 "$STAGING_DIR/DEBIAN"
chmod 644 "$STAGING_DIR/DEBIAN/control"

OUTPUT_DEB="$PROJECT_ROOT/dist/${PKG_NAME}_${VERSION}_${ARCH}.deb"
if dpkg-deb --help 2>&1 | grep -q -- '--root-owner-group'; then
    dpkg-deb --root-owner-group --build "$STAGING_DIR" "$OUTPUT_DEB"
else
    dpkg-deb --build "$STAGING_DIR" "$OUTPUT_DEB"
fi

echo "=== Paket .deb berhasil dibuat: $OUTPUT_DEB ==="
