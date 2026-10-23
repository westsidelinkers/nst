import sys
from nst.config import load_config

def main():
    config = load_config(sys.argv[1] if len(sys.argv) > 1 else None)
    print(f"nst config loaded: probe every {config.probe_interval_hours}h, t0 every {config.t0_interval_seconds}s")

if __name__ == "__main__":
    main()
