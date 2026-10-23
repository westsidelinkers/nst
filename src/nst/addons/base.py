"""Addon module framework.

Addon modules are small, self-contained panels that consume a ``T0Sample``
(or other data) and produce a dict of values plus a GTK widget for rendering.
"""

from __future__ import annotations

import importlib
from abc import ABC, abstractmethod
from typing import Any, Optional


class AddonModule(ABC):
    """Base class for all addon modules."""

    name: str = ""

    def __init__(self, config: Any = None, name: Optional[str] = None, **kwargs: Any) -> None:
        self.config = config
        if name is not None:
            self.name = name
        # Allow subclasses to store extra kwargs without breaking.
        for k, v in kwargs.items():
            setattr(self, k, v)

    @abstractmethod
    def update(self, sample: Any) -> dict:
        """Refresh internal state from *sample* and return a dict of values."""

    @abstractmethod
    def render(self) -> Any:
        """Return a ``Gtk.Widget`` representing the module."""

    def __repr__(self) -> str:
        return f"<{type(self).__name__} name={self.name!r}>"


# Registry mapping config module names -> (module path, class name).
_REGISTRY: dict[str, tuple[str, str]] = {
    "bufferbloat": ("nst.addons.bufferbloat", "BufferbloatAddon"),
    "public_ip": ("nst.addons.public_ip", "PublicIpAddon"),
    "battery": ("nst.addons.battery", "BatteryAddon"),
    "os_updates": ("nst.addons.os_updates", "OsUpdatesAddon"),
    "cpu": ("nst.addons.cpu_mem", "CpuMemAddon"),
    "memory": ("nst.addons.cpu_mem", "CpuMemAddon"),
    "cpu_mem": ("nst.addons.cpu_mem", "CpuMemAddon"),
    "wifi": ("nst.addons.wifi", "WifiAddon"),
    "signal": ("nst.addons.wifi", "WifiAddon"),
}


def load_modules(config: Any) -> list[AddonModule]:
    """Instantiate addon modules enabled in *config*.

    Unknown or unavailable module names are skipped. Duplicate modules (e.g.
    when both ``cpu`` and ``memory`` are enabled) are de-duplicated by class.
    """
    enabled = getattr(config, "modules_enabled", None)
    if enabled is None:
        try:
            enabled = list(config) if config is not None else []
        except Exception:
            enabled = []
    if not enabled:
        return []

    modules: list[AddonModule] = []
    seen_classes: set[type] = set()
    for key in enabled:
        key = str(key).strip()
        if not key or key not in _REGISTRY:
            continue
        mod_path, cls_name = _REGISTRY[key]
        try:
            mod = importlib.import_module(mod_path)
            cls = getattr(mod, cls_name)
        except Exception:
            continue
        if cls in seen_classes:
            continue
        seen_classes.add(cls)
        try:
            instance = cls(config=config, name=key)
        except Exception:
            try:
                instance = cls(config=config)
                if not getattr(instance, "name", ""):
                    instance.name = key
            except Exception:
                continue
        if not getattr(instance, "name", ""):
            instance.name = key
        modules.append(instance)
    return modules


__all__ = ["AddonModule", "load_modules"]
