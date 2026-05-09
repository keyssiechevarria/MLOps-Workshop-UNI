"""Runner de tareas en Python (reemplazo portable del Makefile).

Uso rapido:
    python make.py help
    python make.py setup
    python make.py train
    python make.py clean
    python make.py clean-class
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def run(cmd: list[str], cwd: Path | None = None) -> None:
    """Ejecuta un comando y falla si retorna codigo distinto de 0."""
    print("$", " ".join(str(part) for part in cmd))
    subprocess.run(cmd, cwd=cwd or ROOT, check=True)


def python_in_venv(venv_dir: Path) -> Path:
    if sys.platform.startswith("win"):
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def pip_in_venv(venv_dir: Path) -> Path:
    if sys.platform.startswith("win"):
        return venv_dir / "Scripts" / "pip.exe"
    return venv_dir / "bin" / "pip"


def setup() -> None:
    venv_dir = ROOT / "venv"
    run([sys.executable, "-m", "venv", str(venv_dir)])

    pip_exe = pip_in_venv(venv_dir)
    run([str(pip_exe), "install", "--upgrade", "pip"])
    run([str(pip_exe), "install", "-r", "requirements.txt"])

    if sys.platform.startswith("win"):
        print("Entorno listo. Activa con: venv\\Scripts\\Activate.ps1")
    else:
        print("Entorno listo. Activa con: source venv/bin/activate")


def train() -> None:
    run([sys.executable, "src/train.py", "--config", "configs/params.yaml"])


def predict() -> None:
    predict_file = ROOT / "src" / "predict.py"
    if not predict_file.exists():
        raise FileNotFoundError(
            "No existe src/predict.py. Ajusta este comando o crea el script de prediccion."
        )
    run([sys.executable, "src/predict.py", "--model", "models/modelo_concreto.joblib"])


def api() -> None:
    run([
        "uvicorn",
        "app:app",
        "--reload",
        "--host",
        "0.0.0.0",
        "--port",
        "8000",
    ], cwd=ROOT / "despliegue")


def docker_prepare() -> None:
    source_model = ROOT / "models" / "modelo_concreto.joblib"
    target_dir = ROOT / "despliegue" / "modelo"
    target_dir.mkdir(parents=True, exist_ok=True)
    if not source_model.exists():
        raise FileNotFoundError(f"No existe el modelo: {source_model}")
    shutil.copy2(source_model, target_dir / source_model.name)
    print("Modelo copiado a despliegue/modelo/")


def docker() -> None:
    docker_prepare()
    run(["docker", "build", "-t", "concreto-api", "./despliegue"])
    print("Imagen construida: concreto-api")


def run_container() -> None:
    run(["docker", "run", "-p", "8000:8000", "concreto-api"])


def _delete_if_exists(path: Path) -> None:
    if not path.exists() and not path.is_symlink():
        return
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink()


def clean() -> None:
    for pattern in ("models/*.joblib", "models/*.json"):
        for file_path in ROOT.glob(pattern):
            _delete_if_exists(file_path)

    _delete_if_exists(ROOT / "__pycache__")
    _delete_if_exists(ROOT / "src" / "__pycache__")
    _delete_if_exists(ROOT / ".ipynb_checkpoints")
    _delete_if_exists(ROOT / "notebooks" / ".ipynb_checkpoints")

    print("Archivos generados eliminados.")


def clean_class() -> None:
    # Reiniciar DVC
    _delete_if_exists(ROOT / ".dvc")
    _delete_if_exists(ROOT / ".dvc_remote")

    # Limpiar modelos dejando models/.gitkeep
    models_dir = ROOT / "models"
    if models_dir.exists():
        for item in models_dir.iterdir():
            if item.name == ".gitkeep":
                continue
            _delete_if_exists(item)

    # Eliminar notebooks completos de los modulos 02 y 03
    _delete_if_exists(ROOT / "notebooks" / "02_training.ipynb")
    _delete_if_exists(ROOT / "notebooks" / "03_training_mlflow.ipynb")

    # Limpiar reports dejando reports/figures/.gitkeep
    reports_dir = ROOT / "reports"
    figures_dir = reports_dir / "figures"
    keep_file = figures_dir / ".gitkeep"

    if reports_dir.exists():
        for item in reports_dir.iterdir():
            if item == figures_dir:
                continue
            _delete_if_exists(item)

    if figures_dir.exists():
        for item in figures_dir.iterdir():
            if item == keep_file:
                continue
            _delete_if_exists(item)

    # Borrar entornos virtuales locales
    _delete_if_exists(ROOT / "venv")
    _delete_if_exists(ROOT / ".venv")

    print("Entorno reiniciado para clase (DVC, modelos, notebooks completos, reportes y venv).")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Tareas del taller MLOps sin Make.")
    parser.add_argument(
        "command",
        choices=[
            "setup",
            "train",
            "predict",
            "api",
            "docker-prepare",
            "docker",
            "run",
            "clean",
            "clean-class",
            "reset-env",
            "help",
        ],
        help="Comando a ejecutar",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    commands = {
        "setup": setup,
        "train": train,
        "predict": predict,
        "api": api,
        "docker-prepare": docker_prepare,
        "docker": docker,
        "run": run_container,
        "clean": clean,
        "clean-class": clean_class,
        "reset-env": clean_class,
        "help": lambda: parser.print_help(),
    }

    commands[args.command]()


if __name__ == "__main__":
    main()
