#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_DIR="$ROOT_DIR/php-app"
BUILD_DIR="$ROOT_DIR/build/infinityfree"
PACKAGE="$ROOT_DIR/build/patrol-pro-infinityfree.zip"

rm -rf "$BUILD_DIR" "$PACKAGE"
mkdir -p "$BUILD_DIR/htdocs"

cp -R "$APP_DIR/api" "$BUILD_DIR/api"
cp -R "$APP_DIR/auth" "$BUILD_DIR/auth"
cp -R "$APP_DIR/config" "$BUILD_DIR/config"
cp -R "$APP_DIR/controllers" "$BUILD_DIR/controllers"
cp -R "$APP_DIR/models" "$BUILD_DIR/models"
cp -R "$APP_DIR/database" "$BUILD_DIR/database"
cp "$APP_DIR/.env.infinityfree.example" "$BUILD_DIR/.env.example"
cp -R "$APP_DIR/public/." "$BUILD_DIR/htdocs/"

find "$BUILD_DIR" -name '.DS_Store' -delete
find "$BUILD_DIR/htdocs/uploads/incidents" -type f ! -name '.gitkeep' -delete 2>/dev/null || true

(
    cd "$BUILD_DIR"
    zip -qr "$PACKAGE" .
)

printf '%s\n' "$PACKAGE"
