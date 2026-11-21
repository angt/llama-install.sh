import os
import platform
import shutil
import sys
import tarfile
import tempfile
import time
import zipfile
from functools import wraps
from pathlib import Path
from urllib.request import Request, urlopen

from common import ROOT as REPO_ROOT, finish_install, is_current
from versions import ZIG_VERSION as DEFAULT_VERSION

ROOT = REPO_ROOT / "deps" / "zig"
DEST = ROOT.with_suffix(".tmp")
URL = "https://zigmirror.com"


def retry(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        for i in reversed(range(5)):
            try:
                return func(*args, **kwargs)
            except Exception:
                if not i:
                    raise
                time.sleep(10)
    return wrapper


def detect_arch():
    machine = platform.machine().lower()
    if machine in ("x86_64", "amd64"):
        return "x86_64"
    if machine in ("aarch64", "arm64"):
        return "aarch64"
    return machine


def detect_os():
    system = platform.system().lower()
    return {"darwin": "macos"}.get(system, system)


def fetch(file):
    req = Request(f"{URL}/{file}", headers={"User-Agent": "curl/8.0"})
    return urlopen(req, timeout=60)


def strip_top(member_name):
    parts = Path(member_name).parts
    return str(Path(*parts[1:])) if len(parts) > 1 else None


@retry
def install_tar(file):
    def members(tar):
        for member in tar:
            name = strip_top(member.name)
            if name:
                member.name = name
                yield member

    with fetch(file) as response:
        with tarfile.open(fileobj=response, mode="r|*") as tar:
            tar.extractall(DEST, members=members(tar), filter="tar")


@retry
def install_zip(file):
    with fetch(file) as response, tempfile.NamedTemporaryFile(suffix=".zip") as tmp:
        shutil.copyfileobj(response, tmp)
        tmp.flush()
        with zipfile.ZipFile(tmp) as archive:
            for info in archive.infolist():
                name = strip_top(info.filename)
                if not name or info.is_dir():
                    continue
                target = DEST / name
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info) as src, open(target, "wb") as dst:
                    shutil.copyfileobj(src, dst)


def main():
    arch = sys.argv[1] if len(sys.argv) >= 2 and sys.argv[1] else detect_arch()
    os_name = detect_os()
    version = os.getenv("ZIG_VERSION", DEFAULT_VERSION)
    executable = "zig.exe" if os_name == "windows" else "zig"
    signature = f"{version}|{arch}|{os_name}"

    if is_current(ROOT, signature, executable):
        print(f" - Zig {version} found in {ROOT}")
        return

    if os_name == "windows":
        file = f"zig-{arch}-windows-{version}.zip"
        install = install_zip
    else:
        file = f"zig-{arch}-{os_name}-{version}.tar.xz"
        install = install_tar

    shutil.rmtree(DEST, ignore_errors=True)
    DEST.mkdir(parents=True)

    print(f"Installing Zig {version} ({arch}/{os_name})...")
    install(file)
    finish_install(DEST, ROOT, signature)
    print(f" - Zig {version} ({arch}/{os_name})")


if __name__ == "__main__":
    main()
