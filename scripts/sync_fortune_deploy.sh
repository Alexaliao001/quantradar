#!/usr/bin/env bash
# sync_fortune_deploy.sh — private SSOT → public fortune-insight-deploy (Render)
# Usage:
#   bash ~/quantradar/scripts/sync_fortune_deploy.sh           # sync + commit + push
#   PUSH=0 bash ~/quantradar/scripts/sync_fortune_deploy.sh   # local only
#   COMMIT=0 bash ...                                         # sync working tree, no commit
set -euo pipefail

HOME_DIR="${HOME}"
SSOT="${HOME_DIR}/fortune-insight"
DEPLOY="${HOME_DIR}/fortune-insight-deploy"
PUSH="${PUSH:-1}"
COMMIT="${COMMIT:-1}"
MSG="${MSG:-deploy: sync from fortune-insight SSOT}"

die() { echo "ERROR: $*" >&2; exit 1; }
need() { command -v "$1" >/dev/null || die "missing $1"; }

need git
need rsync
[[ -d "$SSOT/.git" ]] || die "missing SSOT $SSOT"
[[ -d "$DEPLOY/.git" ]] || die "missing deploy $DEPLOY"

# Preserve Render host packaging + public README
HOST_PKG="$DEPLOY/package.json"
HOST_RENDER="$DEPLOY/render.yaml"
HOST_README="$DEPLOY/README.md"
[[ -f "$HOST_PKG" ]] || die "missing deploy package.json"
[[ -f "$HOST_RENDER" ]] || die "missing deploy render.yaml"
cp "$HOST_PKG" /tmp/fortune-deploy-package.json.bak
cp "$HOST_RENDER" /tmp/fortune-deploy-render.yaml.bak
[[ -f "$HOST_README" ]] && cp "$HOST_README" /tmp/fortune-deploy-README.md.bak || true

git -C "$DEPLOY" checkout main
git -C "$DEPLOY" pull --ff-only origin main || true

# Sync product sources (do not wipe .git / node_modules / dist entirely)
rsync -a --delete \
  --exclude '.git/' \
  --exclude 'node_modules/' \
  --exclude 'dist/' \
  --exclude '.env' \
  --exclude '.env.local' \
  --exclude 'data/' \
  --exclude '.DS_Store' \
  --exclude 'package.json' \
  --exclude 'render.yaml' \
  --exclude 'README.md' \
  "$SSOT"/ "$DEPLOY"/

# Restore deploy-specific host package + render + README
cp /tmp/fortune-deploy-package.json.bak "$DEPLOY/package.json"
cp /tmp/fortune-deploy-render.yaml.bak "$DEPLOY/render.yaml"
[[ -f /tmp/fortune-deploy-README.md.bak ]] && cp /tmp/fortune-deploy-README.md.bak "$DEPLOY/README.md"

# Ensure free-tarot + host land in dist for Render start
mkdir -p "$DEPLOY/dist/public"
if [[ -f "$SSOT/client/public/free-tarot.html" ]]; then
  cp "$SSOT/client/public/free-tarot.html" "$DEPLOY/dist/public/free-tarot.html"
fi
# Keep existing static SPA assets in dist/public if present; refresh host entry
mkdir -p "$DEPLOY/dist"
cp "$SSOT/server/host.mjs" "$DEPLOY/server/host.mjs"
cp "$SSOT/server/tarot_rules.mjs" "$DEPLOY/server/tarot_rules.mjs"
( cd "$DEPLOY" && npm run build )

git -C "$DEPLOY" add -A
if git -C "$DEPLOY" diff --cached --quiet; then
  echo "deploy: no changes"
else
  if [[ "$COMMIT" == "1" ]]; then
    git -C "$DEPLOY" commit -m "$MSG"
    if [[ "$PUSH" == "1" ]]; then
      git -C "$DEPLOY" push origin main
    fi
  fi
fi

echo "OK: SSOT → deploy synced (package.json/render.yaml preserved as host)"
