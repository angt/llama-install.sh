import os
import subprocess
import sys
import venv
from pathlib import Path

from common import ROOT as REPO_ROOT, is_current, write_exports
from versions import ROCM_VERSION as DEFAULT_VERSION

ROOT = REPO_ROOT / "deps" / "rocm"
INDEX = "https://nightly.repo.amd.com/rocm/whl-next/"


def main():
    target_arch = sys.argv[1] if len(sys.argv) >= 2 else None
    target_os = sys.argv[2] if len(sys.argv) >= 3 else None
    if target_arch != "x86_64" or target_os not in ("linux", "windows"):
        sys.exit(f"ROCm builds are only supported on x86_64 linux/windows targets (got '{target_arch}/{target_os}')")

    requested = sys.argv[3] if len(sys.argv) >= 4 and sys.argv[3] else None
    version = requested or os.getenv("ROCM_VERSION", DEFAULT_VERSION)
    device = os.getenv("LLAMA_INSTALL_DEVICE", "")
    if device == "probe":
        package = "rocm[devel,libraries]"
    elif device.startswith("gfx"):
        package = f"rocm[devel,libraries,device-{device}]"
    else:
        package = "rocm[devel,libraries,device-all]"

    scripts = ROOT / ("Scripts" if os.name == "nt" else "bin")
    python = scripts / ("python.exe" if os.name == "nt" else "python")
    sdk = scripts / ("rocm-sdk.exe" if os.name == "nt" else "rocm-sdk")
    signature = f"{version}|{device or 'all'}|{target_arch}|{target_os}"

    if is_current(ROOT, signature, str(sdk.relative_to(ROOT))):
        print(f" - ROCm {version} ({device or 'all'}) found in {ROOT}")
    else:
        if not python.exists():
            print(f"Creating ROCm Python environment in {ROOT}...")
            venv.EnvBuilder(with_pip=True, clear=True).create(ROOT)
        print(f"Installing ROCm {version} ({device or 'all'})...")
        subprocess.run([
            python, "-m", "pip", "install",
            "--extra-index-url", INDEX, f"{package}=={version}",
        ], cwd=REPO_ROOT, check=True)
        subprocess.run([sdk, "init"], cwd=REPO_ROOT, check=True)
        (ROOT / ".llama-install").write_text(signature + "\n")

    rocm_path = Path(subprocess.check_output([sdk, "path", "--root"], text=True).strip())
    exports = {"ROCM_PATH": rocm_path}
    if target_os == "windows":
        exports["HIP_PATH"] = rocm_path
    write_exports(**exports)
    print(f" - ROCM_PATH={rocm_path}")


if __name__ == "__main__":
    main()
