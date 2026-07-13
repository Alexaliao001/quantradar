#!/usr/bin/env bash
# rebuild_static.sh — SX6-3 一键重建静态站并同步 *-deploy
# Usage: bash ~/quantradar/scripts/rebuild_static.sh <moyu|portfolio|drama|all>
set -euo pipefail

PRODUCT="${1:-}"
HOME_DIR="${HOME}"
STATIC_HOST="${HOME_DIR}/quantradar/scripts/static_host_index.js"
PUSH="${PUSH:-1}"

die() { echo "ERROR: $*" >&2; exit 1; }
need() { command -v "$1" >/dev/null || die "missing $1"; }

need git
need pnpm
[[ -f "$STATIC_HOST" ]] || die "missing $STATIC_HOST"

sync_gh_pages() {
  local deploy="$1"
  local cname="$2"
  local msg="$3"
  local pub="$4"

  git -C "$deploy" fetch origin
  if git -C "$deploy" show-ref --verify --quiet refs/remotes/origin/gh-pages; then
    git -C "$deploy" checkout -B gh-pages origin/gh-pages
  else
    git -C "$deploy" checkout -B gh-pages
  fi

  # wipe tree except .git
  find "$deploy" -mindepth 1 -maxdepth 1 ! -name '.git' -exec rm -rf {} +
  cp -a "$pub"/. "$deploy"/
  [[ -n "$cname" ]] && printf '%s\n' "$cname" >"$deploy/CNAME"
  touch "$deploy/.nojekyll"
  if [[ -f "$deploy/index.html" ]]; then
    cp "$deploy/index.html" "$deploy/404.html"
  fi

  git -C "$deploy" add -A
  if git -C "$deploy" diff --cached --quiet; then
    echo "gh-pages: no changes"
  else
    git -C "$deploy" commit -m "$msg"
    if [[ "$PUSH" == "1" ]]; then
      git -C "$deploy" push origin gh-pages
    fi
  fi
  git -C "$deploy" checkout main
}

sync_render_main() {
  local deploy="$1"
  local pub="$2"
  local msg="$3"

  git -C "$deploy" checkout main
  git -C "$deploy" pull --ff-only origin main || true

  mkdir -p "$deploy/dist"
  rm -rf "$deploy/dist/public"
  cp -a "$pub" "$deploy/dist/public"
  cp "$STATIC_HOST" "$deploy/dist/index.js"

  # ensure lightweight package.json exists
  if [[ ! -f "$deploy/package.json" ]]; then
    cat >"$deploy/package.json" <<'JSON'
{
  "name": "static-host",
  "private": true,
  "type": "module",
  "scripts": {
    "build": "echo prebuilt",
    "start": "NODE_ENV=production node dist/index.js"
  },
  "engines": { "node": ">=20" }
}
JSON
  fi

  git -C "$deploy" add -f dist package.json render.yaml 2>/dev/null || git -C "$deploy" add -f dist package.json
  if git -C "$deploy" diff --cached --quiet; then
    echo "main: no changes"
  else
    git -C "$deploy" commit -m "$msg"
    if [[ "$PUSH" == "1" ]]; then
      git -C "$deploy" push origin main
    fi
  fi
}

rebuild_moyu() {
  local src="${HOME_DIR}/moyu-fortune"
  local deploy="${HOME_DIR}/moyu-fortune-deploy"
  [[ -d "$src" ]] || die "missing $src"
  [[ -d "$deploy" ]] || die "missing $deploy"
  echo "=== rebuild moyu ==="
  (cd "$src" && pnpm build)
  local pub
  if [[ -d "$src/dist/public" ]]; then pub="$src/dist/public"
  elif [[ -d "$src/dist" ]]; then pub="$src/dist"
  else die "moyu build output not found"; fi
  local sha
  sha=$(git -C "$src" rev-parse --short HEAD)
  sync_render_main "$deploy" "$pub" "deploy: moyu static from ${sha}"
  sync_gh_pages "$deploy" "chillworks.ai" "deploy: moyu gh-pages from ${sha}" "$pub"
}

rebuild_portfolio() {
  local src="${HOME_DIR}/rongjian-portfolio"
  local deploy="${HOME_DIR}/rongjian-portfolio-deploy"
  [[ -d "$src" ]] || die "missing $src"
  if [[ ! -d "$deploy" ]]; then
    git clone https://github.com/Alexaliao001/rongjian-portfolio-deploy.git "$deploy"
  fi
  echo "=== rebuild portfolio ==="
  (cd "$src" && PORTFOLIO_STATIC=1 pnpm exec vite build)
  local pub="$src/dist/public"
  [[ -d "$pub" ]] || die "missing $pub — use PORTFOLIO_STATIC=1 vite build"
  local sha
  sha=$(git -C "$src" rev-parse --short HEAD)
  sync_render_main "$deploy" "$pub" "deploy: portfolio SX static from ${sha}"
  sync_gh_pages "$deploy" "rj.fortunesite.one" "deploy: portfolio gh-pages from ${sha}" "$pub"
}

rebuild_drama() {
  local src="${HOME_DIR}/ai-drama-studio"
  local deploy="${HOME_DIR}/ai-drama-studio-deploy"
  [[ -d "$src" ]] || die "missing $src"
  [[ -d "$deploy" ]] || die "missing $deploy"
  echo "=== rebuild drama ==="
  (cd "$src" && pnpm build)
  local pub
  if [[ -d "$src/dist/public" ]]; then pub="$src/dist/public"
  elif [[ -d "$src/dist" ]]; then pub="$src/dist"
  else die "drama build output not found"; fi
  local sha
  sha=$(git -C "$src" rev-parse --short HEAD)
  sync_render_main "$deploy" "$pub" "deploy: drama static from ${sha}"
  sync_gh_pages "$deploy" "shorts.fortunesite.one" "deploy: drama gh-pages from ${sha}" "$pub"
}

usage() {
  cat <<EOF
Usage: $0 <moyu|portfolio|drama|all>

  PUSH=0  skip git push (dry sync + commit only)

Examples:
  bash $0 portfolio
  PUSH=0 bash $0 all
EOF
}

case "$PRODUCT" in
  moyu) rebuild_moyu ;;
  portfolio) rebuild_portfolio ;;
  drama) rebuild_drama ;;
  all)
    rebuild_moyu
    rebuild_portfolio
    rebuild_drama
    ;;
  *)
    usage
    exit 1
    ;;
esac

echo "DONE $PRODUCT"
echo "Verify: python3 ~/quantradar/scripts/sites_extreme_verify.py"
