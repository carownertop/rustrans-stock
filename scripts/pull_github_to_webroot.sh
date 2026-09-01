#!/usr/bin/env bash
# На VPS: подтянуть свежий снимок с GitHub (CI уже собрал Sheets → main)
# в оба каталога витрины хаба.
set -euo pipefail

REPO_RAW="https://raw.githubusercontent.com/carownertop/rustrans-stock/main"
WEB="${VPS_WEBROOT:-/var/www/rtl-view}"
STOCK="$WEB/stock"
SLUG="$WEB/Redx5imaAYtfi1"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

curl -fsSL -o "$TMP/data.json" "$REPO_RAW/data.json"
curl -fsSL -o "$TMP/index.html" "$REPO_RAW/index.html"

python3 - "$TMP/data.json" <<'PY'
import json, sys
p = sys.argv[1]
data = json.load(open(p, encoding="utf-8"))
updated = str(data.get("updated") or "")
if len(updated) < 8:
    raise SystemExit(f"bad data.json updated={updated!r}")
print("ok", updated)
PY

install -m 644 "$TMP/data.json" "$STOCK/data.json"
install -m 644 "$TMP/index.html" "$STOCK/index.html"
if [[ -d "$SLUG" ]]; then
  install -m 644 "$TMP/data.json" "$SLUG/data.json"
  install -m 644 "$TMP/index.html" "$SLUG/index.html"
fi
