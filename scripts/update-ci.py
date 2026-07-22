import json, re, os, sys
from urllib.request import urlopen
from pathlib import Path
from ruamel.yaml import YAML

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generate

updates = {}

with urlopen("https://ziglang.org/download/index.json") as r:
    updates["ZIG_VERSION"] = json.load(r)['master']['version']

with urlopen("https://vulkan.lunarg.com/sdk/latest/linux.txt") as r:
    updates["VULKAN_VERSION"] = r.read().decode().strip()

with urlopen("https://rocm.nightlies.amd.com/whl-multi-arch/rocm/") as r:
    updates["ROCM_VERSION"] = sorted(re.findall(r'rocm-(\d+\.\d+\.\d+a\d+)\.tar\.gz', r.read().decode()))[-1]

with urlopen("https://developer.download.nvidia.com/compute/cuda/redist/") as r:
    index = r.read().decode()

for code in sorted(set(generate.CUDA_ARCHS.values()) | set(generate.CUDA_BUILD_TOOLKIT.values())):
    major = f"{code[:-1]}.{code[-1]}"
    updates[f"CUDA_VERSION_{code}"] = max(re.findall(rf'redistrib_({major}\.[0-9.]+)\.json', index), key=lambda v: [*map(int, v.split('.'))])

for key, value in updates.items():
    print(f" - {key}: {value}")

yaml = YAML()
yaml.preserve_quotes = True
yaml.default_flow_style = False
yaml.width = 4096
yaml.indent(mapping=2, sequence=4, offset=2)

for path in Path(".github/workflows").glob("*.yml"):
    with open(path, 'r') as f:
        data = yaml.load(f)

    if env := data.get('jobs', {}).get('build', {}).get('env'):
        for key, value in updates.items():
            if key in env:
                env[key] = value

    with open(path, 'w') as f:
        yaml.dump(data, f)
