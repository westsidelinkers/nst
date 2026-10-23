"""OS updates addon module (rpm-ostree)."""

from __future__ import annotations

import json
import subprocess
import time
from typing import Any

from nst.addons.base import AddonModule


def _run(cmd: list[str], timeout: int = 30) -> str:
    try:
        res = subprocess.run(cmd, timeout=timeout, capture_output=True, text=True)
    except Exception:
        return ""
    out = getattr(res, "stdout", "") or ""
    err = getattr(res, "stderr", "") or ""
    return (out if isinstance(out, str) else str(out)) + "\n" + (err if isinstance(err, str) else str(err))


class OsUpdatesAddon(AddonModule):
    name = "os_updates"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._data: dict = {}
        self._cache_ttl: float = 1800.0
        try:
            if self.config is not None:
                self._cache_ttl = float(getattr(self.config, "os_updates_cache_ttl", self._cache_ttl))
        except Exception:
            pass
        self._cached_data: dict = {}
        self._last_attempt: float = 0.0

    def update(self, sample: Any = None) -> dict:
        now = time.monotonic()
        if self._last_attempt > 0 and (now - self._last_attempt) < self._cache_ttl:
            self._data = dict(self._cached_data)
            return dict(self._data)

        self._last_attempt = now
        data: dict = {"pending_updates": 0, "reboot_needed": False, "available": False}
        try:
            out = _run(["rpm-ostree", "status", "--json"])
            text = out.strip()
            if not text:
                self._data = data
                self._cached_data = dict(data)
                return dict(data)
            try:
                info = json.loads(text)
            except json.JSONDecodeError:
                # Maybe stdout has extra lines; try last JSON object.
                info = None
                for line in reversed(text.splitlines()):
                    line = line.strip()
                    if line.startswith("{"):
                        try:
                            info = json.loads(line)
                            break
                        except Exception:
                            continue
            if not isinstance(info, dict):
                self._data = data
                self._cached_data = dict(data)
                return dict(data)
            data["available"] = True
            # rpm-ostree status json: deployments list; check for pending.
            deployments = info.get("deployments") or []
            # If more than one deployment or a pending deployment.
            if len(deployments) > 1:
                data["pending_updates"] = len(deployments) - 1
            # Check for "transaction" / staged.
            if info.get("transaction") is not None:
                data["pending_updates"] = max(data["pending_updates"], 1)
            # Reboot needed if booted != pinned? Best effort: check "booted" marker.
            booted = None
            for d in deployments:
                if isinstance(d, dict) and d.get("booted"):
                    booted = d
            # If there is a newer deployment not booted -> reboot needed.
            if len(deployments) > 1 and booted is not deployments[0]:
                data["reboot_needed"] = True
            # Also inspect "cached" / "available" fields.
            if info.get("updates") or info.get("available"):
                try:
                    data["pending_updates"] = max(data["pending_updates"], int(info.get("updates", 0) or 0))
                except (TypeError, ValueError):
                    pass
        except Exception:
            pass
        self._data = data
        if data:
            self._cached_data = dict(data)
        if not data and self._cached_data:
            data = dict(self._cached_data)
            self._data = dict(data)
        return dict(self._data) if self._data else dict(data)

    def render(self) -> Any:
        import os
        if not (os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY')):
            return None
        try:
            import gi

            gi.require_version("Gtk", "4.0")
            from gi.repository import Gtk
        except Exception:
            return None
        d = self._data or {}
        pending = d.get("pending_updates", 0)
        reboot = d.get("reboot_needed", False)
        if not d.get("available", False):
            text = "OS updates  (rpm-ostree unavailable)"
        else:
            text = f"OS updates  pending {pending}"
            if reboot:
                text += "  reboot needed"
        return Gtk.Label(label=text, xalign=0)


__all__ = ["OsUpdatesAddon"]
