#!/usr/bin/env bash
# 停止占用 8000 / 5173 的进程并后台重启前后端；可选在浏览器中打开前端 URL。
# 用法: ./scripts/restart-dev.sh
#
# 环境变量:
#   FRONTEND_URL          默认 http://localhost:5173/
#   FRONTEND_PORT         等待就绪的端口，默认 5173
#   OPEN_BROWSER          设为 0 则不打开任何浏览器（默认 1）
#   OPEN_WITH_CURSOR_APP  设为 1 时用「open -a Cursor URL」（macOS），否则用系统默认浏览器
#   CURSOR_APP            默认 Cursor（仅当 OPEN_WITH_CURSOR_APP=1 时有效）
#
# 兼容旧变量: OPEN_CURSOR_BROWSER=0 等价于 OPEN_BROWSER=0
#
# 单独在终端打开前端（macOS）:
#   open "http://localhost:5173/"
# Linux:
#   xdg-open "http://localhost:5173/"

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT"

FRONTEND_URL="${FRONTEND_URL:-http://localhost:5173/}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
OPEN_BROWSER="${OPEN_BROWSER:-1}"
OPEN_WITH_CURSOR_APP="${OPEN_WITH_CURSOR_APP:-0}"
CURSOR_APP="${CURSOR_APP:-Cursor}"

if [[ "${OPEN_CURSOR_BROWSER:-}" == "0" ]]; then
  OPEN_BROWSER=0
fi

wait_for_port() {
  local port="$1" tries="${2:-20}"
  local i=0
  while ! lsof -i ":$port" >/dev/null 2>&1; do
    i=$((i + 1))
    if [[ "$i" -ge "$tries" ]]; then
      echo "警告: 端口 $port 在 ${tries}s 内未就绪，仍将尝试打开浏览器" >&2
      return 0
    fi
    sleep 0.5
  done
}

# 用系统默认浏览器打开 URL 很简单；只有「指定交给 Cursor.app」时才多几步
open_dev_url() {
  local url="$1"
  case "$(uname -s)" in
    Darwin)
      if [[ "$OPEN_WITH_CURSOR_APP" == "1" ]]; then
        command -v cursor >/dev/null 2>&1 && { cursor -r "$ROOT" 2>/dev/null || true; sleep 0.2; }
        open -a "$CURSOR_APP" "$url"
      else
        open "$url"
      fi
      ;;
    Linux)
      if [[ "$OPEN_WITH_CURSOR_APP" == "1" ]] && command -v cursor >/dev/null 2>&1; then
        cursor -r "$ROOT" "$url" 2>/dev/null || xdg-open "$url" 2>/dev/null || true
      else
        xdg-open "$url" 2>/dev/null || true
      fi
      ;;
    *) echo "请手动在浏览器打开: $url" >&2 ;;
  esac
}

stop_port() {
  local port="$1"
  local pids
  pids=$(lsof -ti ":$port" 2>/dev/null || true)
  if [[ -n "${pids:-}" ]]; then
    echo "Stopping process(es) on port $port: $pids"
    kill $pids 2>/dev/null || true
    sleep 1
    pids=$(lsof -ti ":$port" 2>/dev/null || true)
    if [[ -n "${pids:-}" ]]; then
      kill -9 $pids 2>/dev/null || true
    fi
  fi
}

stop_port 8000
stop_port 5173

mkdir -p "$ROOT/logs"

echo "Starting backend (uvicorn :8000)..."
(
  cd "$ROOT/backend"
  nohup python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 \
    >>"$ROOT/logs/backend-dev.log" 2>&1 &
  echo $! >"$ROOT/logs/backend-dev.pid"
)

echo "Starting frontend (vite :5173)..."
(
  cd "$ROOT/frontend"
  nohup npm run dev >>"$ROOT/logs/frontend-dev.log" 2>&1 &
  echo $! >"$ROOT/logs/frontend-dev.pid"
)

echo ""
echo "已启动:"
echo "  后端  http://0.0.0.0:8000   (PID $(cat "$ROOT/logs/backend-dev.pid"))"
echo "  前端  $FRONTEND_URL (PID $(cat "$ROOT/logs/frontend-dev.pid"))"
echo "  日志  $ROOT/logs/backend-dev.log"
echo "        $ROOT/logs/frontend-dev.log"

if [[ "$OPEN_BROWSER" != "0" ]]; then
  echo ""
  echo "等待前端端口 $FRONTEND_PORT 就绪后打开浏览器…"
  wait_for_port "$FRONTEND_PORT" 40
  open_dev_url "$FRONTEND_URL"
fi
