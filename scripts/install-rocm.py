import glob
import os
import subprocess
import sys
import sysconfig
from pathlib import Path

VERSION = os.getenv("ROCM_VERSION", "7.15.0a20260723")

def detect_gfx():
    filt = os.getenv("FILTER", "")
    if "-" in filt:
        return filt.rsplit("-", 1)[-1]
    if len(sys.argv) >= 2:
        arg = sys.argv[1]
        if "-" in arg:
            return arg.rsplit("-", 1)[-1]
        return arg
    return "all"

def pip_install(extras):
    pkg = f"rocm[{extras}]=={VERSION}"
    print(f"Installing {pkg} ...")
    subprocess.run(
        [sys.executable, "-m", "pip", "install",
         "--extra-index-url", "https://rocm.nightlies.amd.com/whl-multi-arch/",
         pkg],
        check=True,
    )
    print(f" - {pkg}")

def rocm_sdk_init():
    print("Running rocm-sdk init ...")
    subprocess.run(["rocm-sdk", "init"], check=True)
    print(" - rocm-sdk init")

def github_env(name, value):
    env_file = os.getenv("GITHUB_ENV")
    if env_file:
        with open(env_file, "a", encoding="utf-8") as f:
            f.write(f"{name}={value}\n")

def find_device_lib_path():
    """Return the first amdgcn/bitcode directory found in the Python site-packages."""
    site = Path(sysconfig.get_paths()["purelib"])
    # 1) obvious exact candidates
    candidates = [
        site / "_rocm_sdk_devel" / "lib" / "amdgcn" / "bitcode",
        site / "_rocm_sdk_core"   / "lib" / "amdgcn" / "bitcode",
    ]
    # 2) glob-based fallback
    for pattern in [
        str(site / "_rocm_sdk_device_*" / "lib" / "amdgcn" / "bitcode"),
        str(site / "rocm_sdk_device_*"   / "lib" / "amdgcn" / "bitcode"),
        str(site / "*" / "lib" / "amdgcn" / "bitcode"),
    ]:
        dirs = glob.glob(pattern)
        if dirs:
            candidates.append(Path(dirs[0]))
    # 3) recursive fallback: any amdgcn/bitcode under site-packages
    try:
        for p in site.rglob("amdgcn/bitcode"):
            if p.is_dir():
                candidates.append(p)
                break
    except Exception:
        pass

    for path in candidates:
        if path.is_dir():
            print(f"  -> using device-lib path: {path}")
            return str(path)
    # debug: show what exists under site-packages
    for p in site.iterdir():
        if p.is_dir() and "rocm" in p.name.lower():
            print(f"  -> rocm dir found: {p.name}")
    print("  -> WARNING: no amdgcn/bitcode directory found")
    return None

def main():
    gfx = detect_gfx()
    if gfx == "probe":
        extras = "devel,libraries"
    elif gfx.startswith("gfx"):
        extras = f"devel,libraries,device-{gfx}"
    else:
        extras = "devel,libraries,device-all"

    pip_install(extras)
    rocm_sdk_init()

    rocm_path = subprocess.run(
        ["rocm-sdk", "path", "--root"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    print(f"ROCM_PATH={rocm_path}")
    github_env("ROCM_PATH", rocm_path)

    devlib = find_device_lib_path()
    if devlib:
        print(f"ROCM_DEVICE_LIB_PATH={devlib}")
        github_env("ROCM_DEVICE_LIB_PATH", devlib)

if __name__ == "__main__":
    main()
