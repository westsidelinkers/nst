#!/usr/bin/env bash
set -euo pipefail

# Install nst to ~/.local/bin and enable the systemd user unit.

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PYTHON="${PYTHON:-python3}"
HOME_DIR="${HOME}"
BIN_DIR="${HOME_DIR}/.local/bin"
CONFIG_DIR="${HOME_DIR}/.config/nst"
SYSTEMD_DIR="${HOME_DIR}/.config/systemd/user"

mkdir -p "${BIN_DIR}" "${CONFIG_DIR}" "${SYSTEMD_DIR}"

# Verify the source tree is importable with the selected interpreter.
if ! PYTHONPATH="${REPO_DIR}/src" "${PYTHON}" -c "import nst" >/dev/null 2>&1; then
    echo "Error: ${REPO_DIR}/src is not importable with ${PYTHON}" >&2
    exit 1
fi

# Ensure a default config exists.
if [[ ! -f "${CONFIG_DIR}/config.toml" ]]; then
    cat > "${CONFIG_DIR}/config.toml" <<'TOML'
[probe]
interval_hours = 8
hosts = ["cacheFly", "cloudflare"]
size_mb = 5
connections = 8

[t0]
interval_seconds = 2

[animation]
enabled = true
battery_threshold = 30

[modules]
enabled = ["throughput", "latency", "bufferbloat", "signal", "battery", "cpu", "memory", "disk", "public_ip", "os_updates", "ipv6", "devices"]
TOML
fi

# Install launcher. The package is not pip-installed, so point PYTHONPATH at
# the source tree in this repository.
cat > "${BIN_DIR}/nst" <<LAUNCHER
#!/bin/sh
export PYTHONPATH="${REPO_DIR}/src\${PYTHONPATH:+:\$PYTHONPATH}"
exec ${PYTHON} -m nst "${CONFIG_DIR}/config.toml" "\$@"
LAUNCHER
chmod +x "${BIN_DIR}/nst"

# Install systemd user unit.
sed -e "s#%h/.local/bin/nst#${BIN_DIR}/nst#g" "${REPO_DIR}/nst.service" > "${SYSTEMD_DIR}/nst.service"

# Refuse to start alongside a manually launched instance.
if ! systemctl --user is-active --quiet nst.service; then
    if pgrep -af "python3 -m nst" >/dev/null 2>&1; then
        echo "Error: a manual 'python3 -m nst' process is running. Stop it before starting nst.service:" >&2
        pgrep -af "python3 -m nst" >&2 || true
        exit 1
    fi
fi

systemctl --user daemon-reload
systemctl --user enable nst.service
if systemctl --user is-active --quiet nst.service; then
    systemctl --user restart nst.service
else
    systemctl --user start nst.service
fi
if ! systemctl --user is-active --quiet nst.service; then
    systemctl --user --no-pager status nst.service || true
    exit 1
fi

echo "nst installed. Unit: ${SYSTEMD_DIR}/nst.service"
