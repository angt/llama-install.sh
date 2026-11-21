import io
import json
import os
import platform
import re
import shutil
import sys
import tarfile
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import wraps
from pathlib import Path
from urllib.request import urlopen

from common import ROOT as REPO_ROOT, finish_install, is_current, run_installer
from versions import CUDA_VERSIONS

URL = "https://developer.download.nvidia.com/compute/cuda/redist"
ROOT = REPO_ROOT / "deps" / "cuda"
DEST = ROOT.with_suffix(".tmp")
VERSION = None

COMPONENTS = [
    ("libcublas",      "target", None, None),
    ("cuda_cudart",    "target", None, None),
    ("cuda_nvml_dev",  "target", None, None),
    ("cuda_cccl",      "target", None, lambda m: "cccl" if "cccl" in m else "cuda_cccl"),
    ("cuda_crt",       "target", lambda m, t: "cuda_crt" in m, None),
    ("libnvvm",        "host",   lambda m, t: "libnvvm" in m, None),
    ("cuda_nvcc",      "host",   None, None),
    ("cuda_nvprune",   "host",   lambda m, t: t == "linux", None),
    ("cuda_cuobjdump", "host",   lambda m, t: t == "linux", None),
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
    if machine in ("x86_64", "amd64"):
        return "x86_64"
    if machine in ("aarch64", "arm64"):
        return "aarch64"
    return machine


def detect_os():
    system = platform.system().lower()
    return {"darwin": "macos"}.get(system, system)


def resolve_version(value=None):
    value = value or os.getenv("CUDA_CODE") or max(CUDA_VERSIONS, key=int)
    if value in CUDA_VERSIONS:
        return value, CUDA_VERSIONS[value]

    match = re.fullmatch(r"(\d+)\.(\d+)(?:\.(\d+))?", value)
    if match:
        code = match.group(1) + match.group(2)
        if code in CUDA_VERSIONS:
            return code, value if match.group(3) else CUDA_VERSIONS[code]

    codes = ", ".join(sorted(CUDA_VERSIONS))
    sys.exit(f"Unknown CUDA version '{value}' (expected a code in {codes}, or X.Y[.Z])")


def platform_key(arch, os_name):
    if os_name == "linux":
        return {"x86_64": "linux-x86_64", "aarch64": "linux-sbsa"}[arch]
    if os_name == "windows":
        return {"x86_64": "windows-x86_64", "aarch64": "windows-arm64"}[arch]
    sys.exit(f"Unsupported OS: {os_name}")


def strip_top(path):
    parts = Path(path).parts
    return str(Path(*parts[1:])) if len(parts) > 1 else ""


def _extract_zip(data, dest):
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for member in z.infolist():
            rel = strip_top(member.filename)
            if not rel or member.is_dir():
                continue
            target = dest / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            with z.open(member) as src, open(target, "wb") as dst:
                shutil.copyfileobj(src, dst)


def _extract_tar(data, dest):
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as tar:
        members = []
        for member in tar.getmembers():
            rel = strip_top(member.name)
            if not rel:
                continue
            member.name = rel
            members.append(member)
        tar.extractall(dest, members=members, filter="tar")


def collect_tasks(manifest, target_plat, host_plat, target_os):
    tasks = []
    for name, which, gate, key in COMPONENTS:
        if gate is not None and not gate(manifest, target_os):
            continue
        plat = target_plat if which == "target" else host_plat
        data = manifest[key(manifest) if key else name]
        label = f"{data['name']} version {data['version']} ({plat})"
        tasks.append((label, data[plat]["relative_path"]))
    return tasks


@retry
def download_manifest():
    with urlopen(f"{URL}/redistrib_{VERSION}.json", timeout=60) as r:
        return json.load(r)


@retry
def install_component(name, file):
    with urlopen(f"{URL}/{file}", timeout=120) as r:
        data = r.read()
    if file.endswith(".zip"):
        _extract_zip(data, DEST)
    else:
        _extract_tar(data, DEST)
    return f" - {name}"


def main():
    global VERSION

    arch = sys.argv[1] if len(sys.argv) >= 2 and sys.argv[1] else detect_arch()
    target_os = sys.argv[2] if len(sys.argv) >= 3 and sys.argv[2] else detect_os()
    requested = sys.argv[3] if len(sys.argv) >= 4 else None
    code, VERSION = resolve_version(requested)

    host_arch = detect_arch()
    host_os = detect_os()
    host_plat = platform_key(host_arch, host_os)
    target_plat = platform_key(arch, target_os)
    signature = f"{VERSION}|{arch}|{target_os}|{host_arch}|{host_os}"
    nvcc = "bin/nvcc.exe" if host_os == "windows" else "bin/nvcc"

    if is_current(ROOT, signature, "include/cuda_runtime.h", nvcc):
        print(f" - CUDA {VERSION} found in {ROOT}")
    else:
        cross = host_os != target_os
        print(f"Installing CUDA {VERSION} (arch={arch}, target={target_os}"
              f"{f', host={host_os}' if cross else ''})...")

        manifest = download_manifest()
        tasks = collect_tasks(manifest, target_plat, host_plat, target_os)
        shutil.rmtree(DEST, ignore_errors=True)
        DEST.mkdir(parents=True)

        with ThreadPoolExecutor(2) as pool:
            futures = [pool.submit(install_component, name, file) for name, file in tasks]
            for future in as_completed(futures):
                print(future.result())

        if target_os == "linux":
            (DEST / "lib64").symlink_to("lib")
        finish_install(DEST, ROOT, signature)

    env = os.environ.copy()
    env["CUDA_CODE"] = code
    env["CUDA_VERSION"] = VERSION
    run_installer("clang", "cuda", env=env)


if __name__ == "__main__":
    main()
