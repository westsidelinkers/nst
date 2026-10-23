"""CPU and memory addon module."""

from __future__ import annotations

import time
from typing import Any

from nst.addons.base import AddonModule


def _read_text(path: str) -> str:
    try:
        with open(path) as f:
            return f.read()
    except Exception:
        return ""


def _parse_meminfo(text: str) -> dict:
    result: dict = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        key = parts[0].rstrip(":")
        try:
            val = float(parts[1])
        except ValueError:
            continue
        # values in kB
        result[key] = val
        if len(parts) >= 3 and parts[2].lower().startswith("k"):
            result[key + "_kb"] = val
    return result


class CpuMemAddon(AddonModule):
    name = "cpu_mem"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._data: dict = {}
        self._prev_cpu: tuple[float, float] | None = None
        self._prev_time: float | None = None

    def _cpu_usage(self) -> float:
        text = _read_text("/proc/stat")
        for line in text.splitlines():
            if line.startswith("cpu "):
                parts = line.split()
                if len(parts) < 2:
                    continue
                # user nice system idle iowait irq softirq steal guest guest_nice
                nums = []
                for x in parts[1:9]:
                    try:
                        nums.append(float(x))
                    except ValueError:
                        nums.append(0.0)
                # pad
                while len(nums) < 8:
                    nums.append(0.0)
                idle = nums[3] + nums[4]
                total = sum(nums)
                now = time.monotonic()
                if self._prev_cpu is not None and self._prev_time is not None:
                    prev_idle, prev_total = self._prev_cpu
                    d_idle = idle - prev_idle
                    d_total = total - prev_total
                    if d_total > 0:
                        usage = (1.0 - d_idle / d_total) * 100.0
                    else:
                        usage = 0.0
                else:
                    usage = 0.0
                self._prev_cpu = (idle, total)
                self._prev_time = now
                return max(0.0, min(100.0, usage))
        return 0.0

    def update(self, sample: Any = None) -> dict:
        data: dict = {}
        try:
            cpu_pct = self._cpu_usage()
            data["cpu_pct"] = round(cpu_pct, 1)
        except Exception:
            data["cpu_pct"] = 0.0

        try:
            if sample is not None:
                ct = getattr(sample, "cpu_temp_c", None)
                if ct is not None:
                    data["cpu_temp_c"] = float(ct)
            # thermal zones
            temps = []
            for i in range(8):
                txt = _read_text(f"/sys/class/thermal/thermal_zone{i}/temp")
                if txt.strip():
                    try:
                        temps.append(float(txt.strip()) / 1000.0)
                    except ValueError:
                        pass
            if temps:
                data.setdefault("cpu_temp_c", max(temps))
            # fallback thermal_zone0
            if "cpu_temp_c" not in data:
                txt = _read_text("/sys/class/thermal/thermal_zone0/temp")
                if txt.strip():
                    try:
                        data["cpu_temp_c"] = float(txt.strip()) / 1000.0
                    except ValueError:
                        pass
        except Exception:
            pass

        try:
            mem = _parse_meminfo(_read_text("/proc/meminfo"))
            total_kb = mem.get("MemTotal", 0.0)
            avail_kb = mem.get("MemAvailable", mem.get("MemFree", 0.0))
            used_kb = total_kb - avail_kb
            data["mem_total_mb"] = round(total_kb / 1024.0, 1)
            data["mem_used_mb"] = round(used_kb / 1024.0, 1)
            data["mem_avail_mb"] = round(avail_kb / 1024.0, 1)
            if total_kb > 0:
                data["mem_pct"] = round((used_kb / total_kb) * 100.0, 1)
            # loadavg
            la = _read_text("/proc/loadavg").split()
            if la:
                try:
                    data["load_1"] = float(la[0])
                except ValueError:
                    pass
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
        cpu = d.get("cpu_pct", 0)
        temp = d.get("cpu_temp_c", 0)
        mem = d.get("mem_pct", 0)
        text = f"CPU {cpu:.0f}%  {temp:.0f}°C   Mem {mem:.0f}%"
        return Gtk.Label(label=text, xalign=0)


__all__ = ["CpuMemAddon"]
