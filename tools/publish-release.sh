#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <version> <path-to-bin>"
  exit 1
fi

VERSION="$1"          # e.g., 1.4.3  (tag = v1.4.3)
BIN="$2"              # e.g., releases/my_clock-1.4.3.bin
REPO="myathanclock/urban-octo-fishstick"

TAG="v$VERSION"
NAME="$(basename "$BIN")"

# 1) Create (or replace) GitHub release and upload asset
gh release delete "$TAG" -R "$REPO" -y >/dev/null 2>&1 || true
gh release create "$TAG" "$BIN" -R "$REPO" -t "$TAG" -n "Firmware $VERSION"

# 2) Construct the asset URL
ASSET_URL="https://github.com/$REPO/releases/download/$TAG/$NAME"

# 3) Update manifest
./tools/make-manifest.sh "$BIN" "$VERSION" "$ASSET_URL"

# 4) Commit & push manifest
git add manifests/stable.json
git commit -m "Update manifest for $VERSION"
git push

echo "Done. Manifest points to: $ASSET_URL"
