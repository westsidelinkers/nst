"""Battery addon module (UPower-backed)."""

from __future__ import annotations

import re
import subprocess
from typing import Any

from nst.addons.base import AddonModule


def _run(cmd: list[str], timeout: int = 5) -> str:
    try:
        res = subprocess.run(cmd, timeout=timeout, capture_output=True, text=True)
    except Exception:
        return ""
    out = getattr(res, "stdout", "") or ""
    err = getattr(res, "stderr", "") or ""
    return (out if isinstance(out, str) else str(out)) + "\n" + (err if isinstance(err, str) else str(err))


class BatteryAddon(AddonModule):
    name = "battery"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._data: dict = {}

    def update(self, sample: Any = None) -> dict:
        data: dict = {}
        # Sample-provided basics.
        try:
            if sample is not None:
                bp = getattr(sample, "battery_pct", None)
                if bp is not None:
                    data["battery_pct"] = float(bp)
                bh = getattr(sample, "battery_health_pct", None)
                if bh is not None:
                    data["health_pct"] = float(bh)
                ob = getattr(sample, "on_battery", None)
                if ob is not None:
                    data["on_battery"] = bool(ob)
        except Exception:
            pass

        # sysfs health fallback.
        try:
            for bat in ("BAT0", "BAT1"):
                try:
                    with open(f"/sys/class/power_supply/{bat}/capacity") as f:
                        data.setdefault("battery_pct", float(f.read().strip()))
                except FileNotFoundError:
                    continue
                try:
                    with open(f"/sys/class/power_supply/{bat}/energy_full") as f:
                        full = float(f.read().strip())
                    with open(f"/sys/class/power_supply/{bat}/energy_full_design") as f:
                        design = float(f.read().strip())
                    if design > 0:
                        data.setdefault("health_pct", (full / design) * 100.0)
                except FileNotFoundError:
                    pass
                break
        except Exception:
            pass

        # UPower enrichment.
        try:
            out = _run(["upower", "-e"])
            bat_path = None
            for line in out.splitlines():
                line = line.strip()
                if "battery" in line.lower():
                    bat_path = line
                    break
            if bat_path:
                info = _run(["upower", "-i", bat_path])
                for line in info.splitlines():
                    line = line.strip()
                    m = re.match(r"percentage:\s*(.+)", line, re.IGNORECASE)
                    if m and "battery_pct" not in data:
                        val = m.group(1).strip().rstrip("%")
                        try:
                            data["battery_pct"] = float(val)
                        except ValueError:
                            pass
                    m = re.match(r"capacity:\s*(.+)", line, re.IGNORECASE)
                    if m:
                        val = m.group(1).strip().rstrip("%")
                        try:
                            data["health_pct"] = float(val)
                        except ValueError:
                            pass
                    m = re.match(r"charge-cycles:\s*(.+)", line, re.IGNORECASE)
                    if m:
                        val = m.group(1).strip()
                        try:
                            data["charge_cycles"] = int(float(val))
                        except ValueError:
                            try:
                                data["charge_cycles"] = float(val)
                            except ValueError:
                                pass
                # charge threshold (some devices expose via upower or sysfs)
        except Exception:
            pass

        # charge threshold via sysfs
        try:
            for bat in ("BAT0", "BAT1"):
                for name in ("charge_control_end_threshold", "charge_stop_threshold"):
                    try:
                        with open(f"/sys/class/power_supply/{bat}/{name}") as f:
                            data.setdefault("charge_threshold", int(f.read().strip()))
                    except (FileNotFoundError, ValueError):
                        continue
        except Exception:
            pass

        # on_battery via AC
        try:
            if "on_battery" not in data:
                for ac in ("AC", "ACAD", "ADP0"):
                    try:
                        with open(f"/sys/class/power_supply/{ac}/online") as f:
                            data["on_battery"] = (f.read().strip() == "0")
                        break
                    except FileNotFoundError:
                        continue
        except Exception:
            pass

        self._data = data
        return dict(data)

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
        pct = d.get("battery_pct", 0)
        health = d.get("health_pct", 0)
        cycles = d.get("charge_cycles", "")
        thr = d.get("charge_threshold", "")
        text = f"Battery  {pct:.0f}%  health {health:.0f}%"
        if cycles != "":
            text += f"  cycles {cycles}"
        if thr != "":
            text += f"  thr {thr}%"
        return Gtk.Label(label=text, xalign=0)


__all__ = ["BatteryAddon"]
