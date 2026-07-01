import os
import platform
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"


def venv_python() -> Path:
    if platform.system() == "Windows":
        return VENV / "Scripts" / "python.exe"
    return VENV / "bin" / "python"


def create_venv():
    if venv_python().exists():
        return

    print("[setup] creating virtual environment...")
    subprocess.check_call([sys.executable, "-m", "venv", str(VENV)])


def install_requirements():
    python = venv_python()

    print("[setup] upgrading pip...")
    subprocess.check_call([str(python), "-m", "pip", "install", "--upgrade", "pip"])

    print("[setup] installing requirements...")
    subprocess.check_call([str(python), "-m", "pip", "install", "-r", str(ROOT / "requirements.txt")])


def run_app():
    python = venv_python()
    app = ROOT / "app.py"

    print("[run] starting TATEP Demo...")
    subprocess.check_call([str(python), str(app)])


def main():
    create_venv()
    install_requirements()
    run_app()


if __name__ == "__main__":
    main()
