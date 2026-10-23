import sys

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
