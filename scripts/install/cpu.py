import os
import sys

from common import run_installer


def main():
    env = os.environ.copy()
    if len(sys.argv) >= 4 and sys.argv[3]:
        env["ZIG_VERSION"] = sys.argv[3]
    run_installer("zig", env=env)


if __name__ == "__main__":
    main()
