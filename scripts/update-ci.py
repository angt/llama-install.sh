import json, re
from urllib.request import urlopen
from pathlib import Path
from ruamel.yaml import YAML

CUDA_MAJOR = "12.8"

updates = {}

with urlopen("https://ziglang.org/download/index.json") as r:
    updates["ZIG_VERSION"] = json.load(r)['master']['version']

with urlopen("https://vulkan.lunarg.com/sdk/latest/linux.txt") as r:
    updates["VULKAN_VERSION"] = r.read().decode().strip()

with urlopen("https://rocm.nightlies.amd.com/whl-multi-arch/rocm/") as r:
    updates["ROCM_VERSION"] = sorted(re.findall(r'rocm-(\d+\.\d+\.\d+a\d+)\.tar\.gz', r.read().decode()))[-1]

with urlopen("https://developer.download.nvidia.com/compute/cuda/redist/") as r:
    updates["CUDA_VERSION"] = max(re.findall(rf'redistrib_({CUDA_MAJOR}\.[0-9.]+)\.json', r.read().decode()), key=lambda v: [*map(int, v.split('.'))])

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
