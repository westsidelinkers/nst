import os
import sys

_LAYER_SHELL_LIB = "/usr/lib64/libgtk4-layer-shell.so.0"
if os.path.exists(_LAYER_SHELL_LIB) and _LAYER_SHELL_LIB not in os.environ.get("LD_PRELOAD", "").split(os.pathsep):
    os.environ["LD_PRELOAD"] = _LAYER_SHELL_LIB + (os.pathsep + os.environ["LD_PRELOAD"] if os.environ.get("LD_PRELOAD") else "")
    os.execv(sys.executable, [sys.executable, "-m", "nst", *sys.argv[1:]])

from nst.app import NstApplication
from nst.config import load_config


def main(argv=None) -> int:
    if argv is None:
        argv = sys.argv
    config_path = argv[1] if len(argv) > 1 else None
    app = NstApplication(config_path=config_path)
    return app.run(argv)


if __name__ == "__main__":
    raise SystemExit(main())
