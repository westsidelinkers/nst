#!/usr/bin/env bash
set -euo pipefail

# Install nst to ~/.local/bin and enable the systemd user unit.

PYTHON="${PYTHON:-python3}"
HOME_DIR="${HOME}"
BIN_DIR="${HOME_DIR}/.local/bin"
CONFIG_DIR="${HOME_DIR}/.config/nst"
SYSTEMD_DIR="${HOME_DIR}/.config/systemd/user"

mkdir -p "${BIN_DIR}" "${CONFIG_DIR}" "${SYSTEMD_DIR}"

# Copy the package source into a user site location if not already importable.
if ! "${PYTHON}" -c "import nst" >/dev/null 2>&1; then
    echo "Warning: 'nst' package not importable; install it first (pip install --user .)" >&2
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

# Install launcher.
cat > "${BIN_DIR}/nst" <<LAUNCHER
#!/bin/sh
exec ${PYTHON} -m nst "${CONFIG_DIR}/config.toml" "\$@"
LAUNCHER
chmod +x "${BIN_DIR}/nst"

# Install systemd user unit.
sed -e "s#%h/.local/bin/nst#${BIN_DIR}/nst#g" \
    -e "s#%h/.config/nst/config.toml#${CONFIG_DIR}/config.toml#g" \
    nst.service > "${SYSTEMD_DIR}/nst.service"

systemctl --user daemon-reload || true
systemctl --user enable --now nst.service || true

echo "nst installed. Unit: ${SYSTEMD_DIR}/nst.service"
