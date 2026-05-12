#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIST="$ROOT_DIR/frontend/dist/index.html"

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-${HAPPY_PDF_PORT:-8000}}"

if [[ -x "$BACKEND_DIR/.venv/bin/python" ]]; then
  PYTHON="$BACKEND_DIR/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON="python"
else
  echo "未找到 Python，请先安装 Python 3.10+。"
  exit 1
fi

find_free_port() {
  local port="$1"
  for _ in $(seq 1 50); do
    if ! "$PYTHON" - "$port" <<'PY' >/dev/null 2>&1
import socket
import sys

port = int(sys.argv[1])
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", port))
PY
    then
      port=$((port + 1))
      continue
    fi
    echo "$port"
    return 0
  done
  return 1
}

LAN_IP="$("$PYTHON" - <<'PY'
import socket

ip = "127.0.0.1"
try:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
except Exception:
    pass
print(ip)
PY
)"

SELECTED_PORT="$(find_free_port "$PORT")" || {
  echo "未找到可用端口，请设置 PORT=xxxx 后重试。"
  exit 1
}

if [[ "$SELECTED_PORT" != "$PORT" ]]; then
  echo "端口 $PORT 已被占用，自动改用 $SELECTED_PORT。"
fi

if [[ ! -f "$FRONTEND_DIST" ]]; then
  echo "未找到前端构建产物，正在执行 npm install 和 npm run build..."
  (cd "$ROOT_DIR/frontend" && npm install && npm run build)
fi

"$PYTHON" - <<'PY'
import importlib.util
import sys

missing = [name for name in ("fastapi", "uvicorn", "fitz", "PIL") if importlib.util.find_spec(name) is None]
if missing:
    print("缺少后端依赖：" + ", ".join(missing))
    print("请先执行：cd backend && pip install -r requirements.txt")
    sys.exit(1)
PY

mkdir -p \
  "$BACKEND_DIR/data/uploads" \
  "$BACKEND_DIR/data/documents" \
  "$BACKEND_DIR/data/renders" \
  "$BACKEND_DIR/data/crops" \
  "$BACKEND_DIR/data/edits" \
  "$BACKEND_DIR/data/outputs" \
  "$BACKEND_DIR/data/logs"

echo
echo "happy_pdf 正在启动..."
echo "本机访问:   http://127.0.0.1:$SELECTED_PORT"
echo "局域网访问: http://$LAN_IP:$SELECTED_PORT"
echo "API 文档:   http://127.0.0.1:$SELECTED_PORT/docs"
echo "停止服务:   Ctrl+C"
echo

cd "$BACKEND_DIR"
exec "$PYTHON" -m uvicorn app.main:app --host "$HOST" --port "$SELECTED_PORT"
