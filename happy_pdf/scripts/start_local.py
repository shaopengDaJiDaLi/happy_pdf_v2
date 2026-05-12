from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
FRONTEND_DIR = ROOT_DIR / "frontend"
FRONTEND_DIST = FRONTEND_DIR / "dist" / "index.html"
VENV_DIR = BACKEND_DIR / ".venv"


def command_name(name: str) -> str:
    windows_name = f"{name}.cmd" if os.name == "nt" else name
    resolved = shutil.which(windows_name) or shutil.which(name)
    if not resolved:
        raise SystemExit(f"Missing command: {name}. Please install it and retry.")
    return resolved


def venv_python() -> Path | None:
    if os.name == "nt":
        python = VENV_DIR / "Scripts" / "python.exe"
    else:
        python = VENV_DIR / "bin" / "python"
    return python if python.exists() else None


def selected_python() -> str:
    python = venv_python()
    if python:
        return str(python)
    if sys.version_info < (3, 10):
        raise SystemExit("Python 3.10+ is required.")
    return sys.executable


def find_free_port(start_port: int) -> int:
    port = start_port
    for _ in range(50):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("0.0.0.0", port))
            except OSError:
                port += 1
                continue
        return port
    raise SystemExit("No free port found. Set PORT=xxxx and retry.")


def lan_ip() -> str:
    ip = "127.0.0.1"
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            ip = sock.getsockname()[0]
    except OSError:
        pass
    return ip


def ensure_frontend_build() -> None:
    if FRONTEND_DIST.exists():
        return
    npm = command_name("npm")
    print("Frontend build not found; running npm install and npm run build...")
    subprocess.run([npm, "install"], cwd=FRONTEND_DIR, check=True)
    subprocess.run([npm, "run", "build"], cwd=FRONTEND_DIR, check=True)


def ensure_backend_dependencies(python: str) -> None:
    check = (
        "import importlib.util, sys; "
        "missing=[n for n in ('fastapi','uvicorn','fitz','PIL') "
        "if importlib.util.find_spec(n) is None]; "
        "print(','.join(missing)); "
        "sys.exit(1 if missing else 0)"
    )
    result = subprocess.run(
        [python, "-c", check],
        cwd=BACKEND_DIR,
        text=True,
        capture_output=True,
    )
    if result.returncode == 0:
        return
    missing = result.stdout.strip() or result.stderr.strip()
    print(f"Missing backend dependencies: {missing}")
    print("Run setup first:")
    if os.name == "nt":
        print(r"  .\setup.ps1")
    else:
        print("  python3 scripts/setup_local.py")
    raise SystemExit(1)


def ensure_data_dirs() -> None:
    for name in ("uploads", "documents", "renders", "crops", "edits", "outputs", "logs"):
        (BACKEND_DIR / "data" / name).mkdir(parents=True, exist_ok=True)


def main() -> int:
    python = selected_python()
    host = os.environ.get("HOST", "0.0.0.0")
    requested_port = int(os.environ.get("PORT", os.environ.get("HAPPY_PDF_PORT", "8000")))
    port = find_free_port(requested_port)
    if port != requested_port:
        print(f"Port {requested_port} is busy; using {port}.")

    ensure_frontend_build()
    ensure_backend_dependencies(python)
    ensure_data_dirs()

    print()
    print("happy_pdf is starting...")
    print(f"Local URL: http://127.0.0.1:{port}")
    print(f"LAN URL:   http://{lan_ip()}:{port}")
    print(f"API docs:  http://127.0.0.1:{port}/docs")
    print("Stop:      Ctrl+C")
    print()

    command = [
        python,
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        host,
        "--port",
        str(port),
    ]
    process = subprocess.Popen(command, cwd=BACKEND_DIR)
    try:
        return process.wait()
    except KeyboardInterrupt:
        process.terminate()
        return process.wait()


if __name__ == "__main__":
    raise SystemExit(main())
