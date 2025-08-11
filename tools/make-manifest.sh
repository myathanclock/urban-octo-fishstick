#!/usr/bin/env bash
set -euo pipefail

BIN_PATH="$1"        # e.g., releases/my_clock-1.4.3.bin
VERSION="$2"         # e.g., 1.4.3
ASSET_URL="$3"       # final download URL (from the Release asset)

SIZE=$(wc -c < "$BIN_PATH" | tr -d ' ')
SHA256=$(shasum -a 256 "$BIN_PATH" | awk '{print $1}')

cat > manifests/stable.json <<EOF
{
  "version": "$VERSION",
  "size": $SIZE,
  "sha256": "$SHA256",
  "url": "$ASSET_URL"
}
EOF

echo "Wrote manifests/stable.json"
