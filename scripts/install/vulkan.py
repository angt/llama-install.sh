import os
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import zipfile
from functools import wraps
from pathlib import Path
from urllib.request import Request, urlopen

from common import ROOT as REPO_ROOT, finish_install, is_current, run_installer
from versions import VULKAN_VERSION as DEFAULT_VERSION

ROOT = REPO_ROOT / "deps" / "vulkan"
DEST = ROOT.with_suffix(".tmp")
URL = "https://sdk.lunarg.com/sdk/download"
VERSION = DEFAULT_VERSION

# Headers, glslc, and the libraries glslc depends on are enough to build.
KEEP = ("bin", "include", "lib")


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


@retry
def install(file):
    req = Request(f"{URL}/{VERSION}/linux/{file}.tar.xz", headers={"User-Agent": "curl/8.0"})

    def members(tar):
        for member in tar:
            # Skip the version/arch directories at the top of the archive.
            parts = Path(member.name).parts
            if len(parts) > 3 and parts[2] in KEEP:
                member.name = str(Path(*parts[2:]))
                yield member

    with urlopen(req, timeout=300) as response, tarfile.open(fileobj=response, mode="r|*") as tar:
        tar.extractall(DEST, members=members(tar), filter="tar")


@retry
def install_mac():
    # The macOS zip wraps a Qt installer. Drive it headlessly and lift the
    # payload out of macOS/ to match the Linux SDK layout.
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        archive = tmp / "vulkansdk.zip"
        req = Request(f"{URL}/{VERSION}/mac/vulkansdk-macos-{VERSION}.zip",
                      headers={"User-Agent": "curl/8.0"})
        with urlopen(req, timeout=600) as response, open(archive, "wb") as file:
            shutil.copyfileobj(response, file)
        with zipfile.ZipFile(archive) as archive_zip:
            archive_zip.extractall(tmp)
        app = next(tmp.glob("*.app"))
        exe = next((app / "Contents" / "MacOS").iterdir())
        exe.chmod(0o755)
        root = tmp / "root"
        subprocess.run([exe, "in", "--root", root, "-c", "--al", "--da",
                        "com.lunarg.vulkan.core"], check=True)
        for name in KEEP:
            shutil.move(root / "macOS" / name, DEST / name)


def main():
    global VERSION

    env = os.environ.copy()
    if len(sys.argv) >= 4 and sys.argv[3]:
        env["ZIG_VERSION"] = sys.argv[3]
    run_installer("zig", env=env)
    requested = sys.argv[3] if len(sys.argv) >= 4 and sys.argv[3] else None
    VERSION = requested or os.getenv("VULKAN_VERSION", DEFAULT_VERSION)
    arch = detect_arch()
    os_name = detect_os()

    if os_name not in ("linux", "macos"):
        sys.exit(f"Vulkan builds are only supported on linux/macos hosts (got '{os_name}')")
    if os_name == "linux" and arch != "x86_64":
        sys.exit(f"LunarG only publishes x86_64 {os_name} SDKs (got '{arch}')")

    signature = f"{VERSION}|{arch}|{os_name}"
    if is_current(ROOT, signature, "include/vulkan/vulkan.h"):
        print(f" - Vulkan SDK {VERSION} found in {ROOT}")
        return

    print(f"Installing Vulkan SDK {VERSION} ({arch}/{os_name})...")
    shutil.rmtree(DEST, ignore_errors=True)
    DEST.mkdir(parents=True)

    if os_name == "macos":
        install_mac()
    else:
        install(f"vulkansdk-linux-{arch}-{VERSION}")

    if not (DEST / "include/vulkan/vulkan.h").exists():
        sys.exit("Installer finished but headers are missing - SDK layout changed?")
    finish_install(DEST, ROOT, signature)
    print(f" - Vulkan SDK {VERSION} ({arch}/{os_name})")


if __name__ == "__main__":
    main()
