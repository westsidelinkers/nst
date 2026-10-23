"""Autostart and packaging helpers for nst."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

_SYSTEMD_UNIT_TEMPLATE = """[Unit]
Description=Network Status Tool
After=sway-session.target
Wants=sway-session.target

[Service]
Type=simple
ExecStartPre=/bin/sh -c 'until swaymsg -t get_outputs >/dev/null 2>&1; do sleep 0.5; done'
ExecStart={binary_path} {config_path}
Restart=on-failure
RestartSec=5

[Install]
WantedBy=sway-session.target
"""


def generate_systemd_unit(binary_path: str, config_path: str) -> str:
    """Generate a systemd user unit string for nst."""
    return _SYSTEMD_UNIT_TEMPLATE.format(
        binary_path=binary_path,
        config_path=config_path,
    )


def generate_sway_exec(binary_path: str) -> str:
    """Generate a sway ``exec`` line that waits for compositor readiness."""
    return (
        "exec sh -c 'until swaymsg -t get_outputs >/dev/null 2>&1; "
        f"do sleep 0.5; done; exec {binary_path}'"
    )


def _config_path(config: Any) -> Path:
    home = Path.home()
    default = home / ".config" / "nst" / "config.toml"
    if isinstance(config, (str, Path)):
        return Path(config)
    # Config object: allow an explicit path attribute if present.
    for attr in ("config_path", "path", "config_file"):
        value = getattr(config, attr, None)
        if value:
            return Path(value)
    return default


def install(config: Any = None) -> None:
    """Install nst to ~/.local/bin, create the systemd user unit, enable it."""
    home = Path.home()
    bin_dir = home / ".local" / "bin"
    config_dir = home / ".config" / "nst"
    systemd_dir = home / ".config" / "systemd" / "user"

    bin_dir.mkdir(parents=True, exist_ok=True)
    config_dir.mkdir(parents=True, exist_ok=True)
    systemd_dir.mkdir(parents=True, exist_ok=True)

    binary_path = bin_dir / "nst"
    config_path = _config_path(config)

    # Ensure a default config exists when none is provided.
    if not config_path.exists():
        try:
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text("# nst configuration\n", encoding="utf-8")
        except OSError:
            pass

    # Install a launcher script. Prefer an existing installed entry point if
    # available; otherwise wrap `python -m nst`.
    python = shutil.which("python3") or shutil.which("python") or "python3"
    launcher = (
        "#!/bin/sh\n"
        f'exec {python} -m nst "{config_path}" "$@"\n'
    )
    binary_path.write_text(launcher, encoding="utf-8")
    try:
        binary_path.chmod(0o755)
    except OSError:
        pass

    # Create systemd user unit.
    unit_path = systemd_dir / "nst.service"
    unit_content = generate_systemd_unit(str(binary_path), str(config_path))
    unit_path.write_text(unit_content, encoding="utf-8")

    # Reload and enable the unit (best effort).
    try:
        subprocess.run(
            ["systemctl", "--user", "daemon-reload"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        pass
    try:
        subprocess.run(
            ["systemctl", "--user", "enable", "--now", "nst.service"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        pass

    # Also drop a sway exec snippet for convenience.
    try:
        sway_config_dir = home / ".config" / "sway"
        sway_config_dir.mkdir(parents=True, exist_ok=True)
        sway_exec_path = sway_config_dir / "nst-exec.conf"
        sway_exec_path.write_text(
            generate_sway_exec(str(binary_path)) + "\n", encoding="utf-8"
        )
    except OSError:
        pass
