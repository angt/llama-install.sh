import sys
import os
import io
import json
import time
import zipfile
import tarfile
import shutil
import platform
from urllib.request import urlopen
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import wraps

VERSION = os.getenv("CUDA_VERSION", "12.8.2")
URL = "https://developer.download.nvidia.com/compute/cuda/redist"

ROOT = Path.cwd() / "deps" / "cuda"
DEST = ROOT.with_suffix(".tmp")

TARGET_COMPONENTS = [
    "libcublas",
    "cuda_cudart",
    "cuda_cccl",
]

HOST_TOOLS_LINUX = [
    "cuda_nvprune",
    "cuda_cuobjdump",
]

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
    if machine in ["x86_64", "amd64"]:
        return "x86_64"
    if machine in ["aarch64", "arm64"]:
        return "aarch64"
    return machine

def detect_os():
    system = platform.system().lower()
    return {"darwin": "macos"}.get(system, system)

def platform_key(arch, os_name):
    if os_name == "linux":
        return {"x86_64": "linux-x86_64", "aarch64": "linux-sbsa"}[arch]

    if os_name == "windows":
        if arch != "x86_64":
            sys.exit(f"No Windows CUDA redist for {arch}")
        return "windows-x86_64"

    sys.exit(f"Unsupported OS: {os_name}")

def collect_tasks(manifest, target_plat, host_plat, target_os):
    tasks = []
    def add(component, plat):
        data = manifest[component]
        tasks.append((f"{data['name']} version {data['version']} ({plat})", data[plat]["relative_path"]))

    for c in TARGET_COMPONENTS:
        add(c, target_plat)

    if "cuda_crt" in manifest:
        add("cuda_crt", target_plat)

    add("cuda_nvcc", host_plat)

    if target_os == "linux":
        for c in HOST_TOOLS_LINUX:
            add(c, host_plat)

    return tasks

def strip_top(path):
    parts = Path(path).parts
    return str(Path(*parts[1:])) if len(parts) > 1 else ""

@retry
def download_manifest():
    with urlopen(f"{URL}/redistrib_{VERSION}.json", timeout=60) as r:
        return json.load(r)

@retry
def install_component(name, file):
    with urlopen(f"{URL}/{file}", timeout=120) as r:
        data = r.read()

    if file.endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            for member in z.infolist():
                rel = strip_top(member.filename)
                if not rel or member.is_dir():
                    continue
                target = DEST / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                with z.open(member) as src, open(target, "wb") as dst:
                    shutil.copyfileobj(src, dst)
    else:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as tar:
            members = []
            for member in tar.getmembers():
                rel = strip_top(member.name)
                if not rel:
                    continue
                member.name = rel
                members.append(member)
            tar.extractall(DEST, members=members, filter='tar')

    return f" - {name}"

def main():
    arch = sys.argv[1] if len(sys.argv) >= 2 else detect_arch()
    target_os = sys.argv[2] if len(sys.argv) >= 3 else os.getenv("CUDA_TARGET_OS", detect_os())

    host_os = detect_os()
    host_plat = platform_key(arch, host_os)
    target_plat = platform_key(arch, target_os)

    cross = host_os != target_os
    print(f"Installing CUDA {VERSION} (arch={arch}, target={target_os}"
          f"{f', host={host_os}' if cross else ''})...")

    manifest = download_manifest()
    tasks = collect_tasks(manifest, target_plat, host_plat, target_os)

    shutil.rmtree(DEST, ignore_errors=True)
    DEST.mkdir(parents=True)

    with ThreadPoolExecutor(2) as pool:
        futures = [pool.submit(install_component, name, file) for name, file in tasks]
        for f in as_completed(futures):
            print(f.result())

    DEST.rename(ROOT)

    if target_os == "linux":
        (ROOT / "lib64").symlink_to("lib")

if __name__ == "__main__":
    main()
