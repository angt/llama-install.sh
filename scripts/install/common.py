import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

STAMP = ".llama-install"


def run_installer(name, *args, env=None):
    subprocess.run(
        [sys.executable, str(SCRIPTS / "install" / f"{name}.py"), *args],
        cwd=ROOT,
        env=env,
        check=True,
    )


def is_current(root, signature, *required):
    try:
        if (root / STAMP).read_text().strip() != signature:
            return False
    except FileNotFoundError:
        return False
    return all((root / path).exists() for path in required)


def finish_install(dest, root, signature):
    shutil.rmtree(root, ignore_errors=True)
    dest.rename(root)
    (root / STAMP).write_text(signature + "\n")


def write_exports(**values):
    path = os.getenv("LLAMA_INSTALL_ENV_FILE")
    if path:
        Path(path).write_text("".join(f"{key}={value}\n" for key, value in values.items()))
