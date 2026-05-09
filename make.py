"""Runner de tareas en Python (reemplazo portable del Makefile).

Uso rápido:
    python make.py help           # Muestra la ayuda
    python make.py setup          # Instala dependencias
    python make.py train          # Entrena el modelo
    python make.py predict        # Ejecuta predicciones
    python make.py api            # Inicia la API (uvicorn)
    python make.py docker-prepare # Prepara archivos para Docker
    python make.py docker         # Construye imagen Docker
    python make.py run            # Ejecuta contenedor Docker
    python make.py clean          # Limpia archivos generados
    python make.py clean-class    # Reinicia el entorno completo
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def run(cmd: list[str], cwd: Path | None = None) -> None:
    """Ejecuta un comando y falla si retorna código distinto de 0."""
    print("$", " ".join(str(part) for part in cmd))
    subprocess.run(cmd, cwd=cwd or ROOT, check=True)


def python_in_venv(venv_dir: Path) -> Path:
    """Obtiene la ruta del intérprete Python en el venv (Windows/Unix)."""
    if sys.platform.startswith("win"):
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def pip_in_venv(venv_dir: Path) -> Path:
    """Obtiene la ruta del gestor pip en el venv (Windows/Unix)."""
    if sys.platform.startswith("win"):
        return venv_dir / "Scripts" / "pip.exe"
    return venv_dir / "bin" / "pip"


def _delete_if_exists(path: Path) -> None:
    """Elimina un archivo o directorio si existe."""
    if not path.exists() and not path.is_symlink():
        return
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink()


# ============================================================================
# COMANDOS: CONFIGURACIÓN E INSTALACIÓN
# ============================================================================

def setup() -> None:
    """
    COMANDO: setup
    CLI: python make.py setup
    
    Pasos:
      1. Crea un entorno virtual (venv) en el directorio raíz
      2. Actualiza pip a la última versión
      3. Instala todas las dependencias desde requirements.txt
      4. Muestra instrucciones para activar el venv
    """
    venv_dir = ROOT / "venv"
    run([sys.executable, "-m", "venv", str(venv_dir)])

    pip_exe = pip_in_venv(venv_dir)
    run([str(pip_exe), "install", "--upgrade", "pip"])
    run([str(pip_exe), "install", "-r", "requirements.txt"])

    if sys.platform.startswith("win"):
        print("✓ Entorno listo. Activa con: venv\\Scripts\\Activate.ps1")
    else:
        print("✓ Entorno listo. Activa con: source venv/bin/activate")


# ============================================================================
# COMANDOS: ENTRENAMIENTO Y ML
# ============================================================================

def train() -> None:
    """
    COMANDO: train
    CLI: python make.py train
    
    Pasos:
      1. Ejecuta el script de entrenamiento (src/train.py)
      2. Utiliza configuración desde configs/params.yaml
      3. Genera el modelo y guarda métricas
    """
    run([sys.executable, "src/train.py", "--config", "configs/params.yaml"])


# ============================================================================
# COMANDOS: PREDICCIÓN E INFERENCIA
# ============================================================================

def predict() -> None:
    """
    COMANDO: predict
    CLI: python make.py predict
    
    Pasos:
      1. Verifica que exista src/predict.py
      2. Carga el modelo entrenado (models/modelo_concreto.joblib)
      3. Ejecuta predicciones sobre los datos especificados
    """
    predict_file = ROOT / "src" / "predict.py"
    if not predict_file.exists():
        raise FileNotFoundError(
            "No existe src/predict.py. Ajusta este comando o crea el script de predicción."
        )
    run([sys.executable, "src/predict.py", "--model", "models/modelo_concreto.joblib"])


# ============================================================================
# COMANDOS: API Y DESPLIEGUE
# ============================================================================

def api() -> None:
    """
    COMANDO: api
    CLI: python make.py api
    
    Pasos:
      1. Inicia el servidor Uvicorn en modo desarrollo (--reload)
      2. Escucha en 0.0.0.0:8000 (accesible desde cualquier interfaz)
      3. Carga la aplicación desde despliegue/app.py
      4. Permite desarrollo interactivo con recarga automática
    """
    run([
        "uvicorn",
        "app:app",
        "--reload",
        "--host", "0.0.0.0",
        "--port", "8000",
    ], cwd=ROOT / "despliegue")


# ============================================================================
# COMANDOS: DOCKER
# ============================================================================

def docker_prepare() -> None:
    """
    COMANDO: docker-prepare
    CLI: python make.py docker-prepare
    
    Pasos:
      1. Verifica que existe el modelo entrenado
      2. Crea el directorio despliegue/modelo
      3. Copia el modelo a despliegue/modelo/ para incluirlo en la imagen
    """
    source_model = ROOT / "models" / "modelo_concreto.joblib"
    target_dir = ROOT / "despliegue" / "modelo"
    target_dir.mkdir(parents=True, exist_ok=True)
    
    if not source_model.exists():
        raise FileNotFoundError(f"No existe el modelo: {source_model}")
    
    shutil.copy2(source_model, target_dir / source_model.name)
    print("✓ Modelo copiado a despliegue/modelo/")


def docker() -> None:
    """
    COMANDO: docker
    CLI: python make.py docker
    
    Pasos:
      1. Ejecuta docker-prepare (prepara los archivos necesarios)
      2. Construye la imagen Docker con tag 'concreto-api'
      3. Usa el Dockerfile de despliegue/
      4. Imagen lista para ser ejecutada o publicada
    """
    docker_prepare()
    run(["docker", "build", "-t", "concreto-api", "./despliegue"])
    print("✓ Imagen construida: concreto-api")


def run_container() -> None:
    """
    COMANDO: run
    CLI: python make.py run
    
    Pasos:
      1. Ejecuta el contenedor Docker 'concreto-api'
      2. Mapea puerto 8000 (contenedor) → 8000 (host)
      3. La API será accesible en http://localhost:8000
      4. Usa Ctrl+C para detener el contenedor
    """
    run(["docker", "run", "-p", "8000:8000", "concreto-api"])


# ============================================================================
# COMANDOS: LIMPIEZA
# ============================================================================

def clean() -> None:
    """
    COMANDO: clean
    CLI: python make.py clean
    
    Pasos:
      1. Elimina modelos entrenados (*.joblib, *.json)
      2. Elimina cachés de Python (__pycache__)
      3. Elimina checkpoints de Jupyter (.ipynb_checkpoints)
      4. Mantiene el código fuente y datos intactos
    """
    for pattern in ("models/*.joblib", "models/*.json"):
        for file_path in ROOT.glob(pattern):
            _delete_if_exists(file_path)

    _delete_if_exists(ROOT / "__pycache__")
    _delete_if_exists(ROOT / "src" / "__pycache__")
    _delete_if_exists(ROOT / ".ipynb_checkpoints")
    _delete_if_exists(ROOT / "notebooks" / ".ipynb_checkpoints")

    print("✓ Archivos generados eliminados.")


def clean_class() -> None:
    """
    COMANDO: clean-class (alias: reset-env)
    CLI: python make.py clean-class
    CLI: python make.py reset-env
    
    Pasos:
      1. Reinicia la configuración de DVC (.dvc, .dvc_remote, *.csv.dvc)
      2. Elimina todos los modelos (excepto .gitkeep)
      3. Elimina notebooks completos (02_training.ipynb, 03_training_mlflow.ipynb)
      4. Limpia reportes y figuras (excepto .gitkeep)
      5. Borra entornos virtuales (venv, .venv)
      6. Útil para reiniciar el proyecto para una nueva clase/sesión
    """
    # Reiniciar DVC
    _delete_if_exists(ROOT / ".dvc")
    _delete_if_exists(ROOT / ".dvc_remote")
    
    # Eliminar archivos .csv.dvc
    for csv_dvc_file in ROOT.glob("**/*.csv.dvc"):
        _delete_if_exists(csv_dvc_file)

    # Limpiar modelos dejando models/.gitkeep
    models_dir = ROOT / "models"
    if models_dir.exists():
        for item in models_dir.iterdir():
            if item.name == ".gitkeep":
                continue
            _delete_if_exists(item)

    # Eliminar notebooks completos de los módulos 02 y 03
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

    print("✓ Entorno reiniciado para clase (DVC, modelos, notebooks, reportes y venv).")


# ============================================================================
# PARSER Y PUNTO DE ENTRADA
# ============================================================================

def build_parser() -> argparse.ArgumentParser:
    """Construye el parser de argumentos con todos los comandos disponibles."""
    parser = argparse.ArgumentParser(
        description="Tareas del taller MLOps sin Make.",
        epilog="Ejemplo: python make.py setup  |  python make.py train"
    )
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
    """Punto de entrada principal: parsea argumentos y ejecuta el comando."""
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
