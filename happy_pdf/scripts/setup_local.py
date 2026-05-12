from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
FRONTEND_DIR = ROOT_DIR / "frontend"
VENV_DIR = BACKEND_DIR / ".venv"


def run(command: list[str], cwd: Path | None = None) -> None:
    print("$ " + " ".join(command))
    subprocess.run(command, cwd=cwd, check=True)


def command_name(name: str) -> str:
    windows_name = f"{name}.cmd" if os.name == "nt" else name
    resolved = shutil.which(windows_name) or shutil.which(name)
    if not resolved:
        raise SystemExit(f"Missing command: {name}. Please install it and retry.")
    return resolved


def venv_python() -> Path:
    if os.name == "nt":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def ensure_python_version() -> None:
    if sys.version_info < (3, 10):
        raise SystemExit("Python 3.10+ is required.")


def ensure_env_file() -> Path:
    env_file = ROOT_DIR / ".env"
    backend_env_file = BACKEND_DIR / ".env"
    env_example = ROOT_DIR / ".env.example"

    if env_file.exists():
        print(".env already exists; keeping it unchanged.")
        return env_file
    if backend_env_file.exists():
        print("backend/.env already exists; keeping it unchanged.")
        print("Tip: new installs should prefer happy_pdf/.env for cross-platform use.")
        return backend_env_file
    if env_example.exists():
        shutil.copyfile(env_example, env_file)
        print("Created .env from .env.example. Fill API keys before real image editing.")
        return env_file
    return env_file


def ensure_backend() -> None:
    if not VENV_DIR.exists():
        run([sys.executable, "-m", "venv", str(VENV_DIR)])

    python = str(venv_python())
    requirements = BACKEND_DIR / "requirements.txt"
    run([python, "-m", "pip", "install", "--upgrade", "pip"])
    run([python, "-m", "pip", "install", "-r", str(requirements)])


def ensure_frontend(build: bool) -> None:
    npm = command_name("npm")
    run([npm, "install"], cwd=FRONTEND_DIR)
    if build:
        run([npm, "run", "build"], cwd=FRONTEND_DIR)


def print_next_steps(env_file: Path) -> None:
    if os.name == "nt":
        start_command = r".\start.ps1"
    else:
        start_command = "python3 scripts/start_local.py"
    print()
    print("Local setup finished.")
    print(f"Next: edit {env_file} and then run: {start_command}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Install happy_pdf local dependencies.")
    parser.add_argument(
        "--no-build",
        action="store_true",
        help="Install dependencies without building the frontend.",
    )
    args = parser.parse_args()

    ensure_python_version()
    env_file = ensure_env_file()
    ensure_backend()
    ensure_frontend(build=not args.no_build)
    print_next_steps(env_file)


if __name__ == "__main__":
    main()
