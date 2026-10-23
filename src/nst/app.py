"""Application entry point and main loop for the network status panel."""

from __future__ import annotations

import logging
import os
import signal
import sys
import threading
import time
from typing import Any, Optional

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib, Gdk

from nst.config import Config, load_config
from nst.ui.panel import NetworkPanel
from nst.ui.css import install_css
from nst.measurement.t0_passive import T0Monitor, T0Sample
from nst.measurement.t1_probe import run_probe, ProbeResult
from nst.measurement.verdict import Verdict, VerdictSignals, compute_verdict
from nst.addons.base import load_modules

try:
    from nst.ui.heartbeat import HeartbeatGraph
except Exception:  # pragma: no cover - environment dependent
    HeartbeatGraph = None

logger = logging.getLogger("nst")

_DEFAULT_APP_ID = "org.nst.NetworkStatusPanel"


def _attr(obj: Any, *names: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        for name in names:
            if name in obj and obj[name] is not None:
                return obj[name]
        return default
    for name in names:
        if hasattr(obj, name):
            value = getattr(obj, name)
            if value is not None:
                return value
    return default


class NstApplication(Gtk.Application):
    """GTK4 application hosting the network status panel."""

    def __init__(
        self,
        config: Any = None,
        config_path: Optional[str] = None,
        application_id: str = _DEFAULT_APP_ID,
        **kwargs: Any,
    ) -> None:
        super().__init__(application_id=application_id, **kwargs)

        # Allow config to be passed as a path string.
        if isinstance(config, str):
            config_path = config
            config = None
        if config is None and config_path is not None:
            try:
                config = load_config(config_path)
            except Exception as exc:
                logger.warning("Failed to load config %s: %s", config_path, exc)
                config = None
        if config is None:
            try:
                config = load_config(None)
            except Exception:
                config = Config()

        self.config = config

        # State.
        self.panel: Optional[NetworkPanel] = None
        self.expanded_panel = None
        self.t0_monitor: Optional[T0Monitor] = None
        self.modules: list = []
        self.heartbeat = None
        self.heartbeat_graph = None
        self.verdict: Any = None
        self.probe_result: Any = None
        self.probe_history: list = []
        self.devices: list = []
        self._last_sample: Any = None

        self._quitting = False
        self._probe_timer_id = None
        self._probe_thread: Optional[threading.Thread] = None
        self._css_installed = False

        # Signal handling.
        try:
            self.connect("shutdown", lambda *_: self.on_quit())
        except Exception:
            pass
        try:
            GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, self._handle_signal)
        except Exception:
            pass
        try:
            GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, self._handle_signal)
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    # Signal handling
    # ------------------------------------------------------------------ #
    def _handle_signal(self, *args: Any) -> bool:
        try:
            self.quit()
        except Exception:
            pass
        return False

    # ------------------------------------------------------------------ #
    # Activation
    # ------------------------------------------------------------------ #
    def do_activate(self) -> None:
        # Handle missing display gracefully.
        try:
            display = Gdk.Display.get_default()
        except Exception:
            display = None
        if display is None:
            logger.warning("No display available; cannot activate application")
            return

        if self.panel is not None:
            try:
                self.panel.present()
            except Exception:
                pass
            return

        # Install CSS.
        if not self._css_installed:
            try:
                install_css(display)
                self._css_installed = True
            except Exception as exc:
                logger.debug("CSS install failed: %s", exc)

        # Create panel.
        try:
            self.panel = NetworkPanel(application=self)
        except Exception as exc:
            logger.error("Failed to create panel: %s", exc)
            self.panel = None
            return

        self.expanded_panel = getattr(self.panel, "expanded_panel", None) or getattr(self.panel, "expanded", None)
        try:
            self.heartbeat = getattr(self.expanded_panel, "heartbeat", None) if self.expanded_panel is not None else None
        except Exception:
            self.heartbeat = None
        self.heartbeat_graph = self.heartbeat

        # Load addon modules.
        try:
            self.modules = load_modules(self.config)
        except Exception as exc:
            logger.debug("load_modules failed: %s", exc)
            self.modules = []

        # Start T0 monitor.
        try:
            interval = getattr(self.config, "t0_interval_seconds", 2)
            self.t0_monitor = T0Monitor(config=self.config, interval_seconds=interval)
            self.t0_monitor.start(self.on_t0_sample)
        except Exception as exc:
            logger.debug("T0 monitor start failed: %s", exc)
            self.t0_monitor = None

        # Schedule T1 probe.
        try:
            self._schedule_probe()
        except Exception as exc:
            logger.debug("Probe scheduling failed: %s", exc)

        # Wire addon actions to panel if possible.
        try:
            if self.expanded_panel is not None:
                self.expanded_panel.on_run_speed_test = self.run_probe_now
        except Exception:
            pass

        # Show panel.
        try:
            self.panel.show_collapsed()
        except Exception:
            try:
                self.panel.present()
            except Exception:
                pass

    def _schedule_probe(self) -> None:
        if self._quitting:
            return
        # Run first probe after a short delay to let T0 settle.
        try:
            self._probe_timer_id = GLib.timeout_add_seconds(5, self._probe_tick)
        except Exception:
            try:
                self._probe_thread = threading.Thread(target=self._probe_worker, daemon=True)
                self._probe_thread.start()
            except Exception:
                pass

    def _probe_tick(self) -> bool:
        if self._quitting:
            return False
        self._probe_worker()
        # Repeat every probe_interval_hours.
        try:
            hours = int(getattr(self.config, "probe_interval_hours", 8))
        except Exception:
            hours = 8
        if hours < 1:
            hours = 1
        # Use a one-shot reschedule to avoid overlapping.
        try:
            GLib.timeout_add_seconds(hours * 3600, self._probe_tick)
        except Exception:
            pass
        return False

    def _probe_worker(self) -> None:
        if self._quitting:
            return
        monitor = self.t0_monitor
        try:
            if monitor is not None:
                monitor.pause_for_probe()
        except Exception:
            pass
        result = None
        try:
            hosts = getattr(self.config, "probe_hosts", ["cacheFly", "cloudflare"])
            connections = getattr(self.config, "probe_connections", 8)
            size_mb = getattr(self.config, "probe_size_mb", 5)
            result = run_probe(
                hosts=hosts,
                connections=connections,
                size_mb=size_mb,
            )
        except Exception as exc:
            logger.debug("Probe failed: %s", exc)
            result = ProbeResult(success=False, error=str(exc))
        finally:
            try:
                if monitor is not None:
                    monitor.resume_from_probe()
            except Exception:
                pass
        if result is not None:
            try:
                GLib.idle_add(self.on_probe_complete, result)
            except Exception:
                try:
                    self.on_probe_complete(result)
                except Exception:
                    pass

    def run_probe_now(self) -> None:
        thread = threading.Thread(target=self._probe_worker, daemon=True)
        thread.start()

    # ------------------------------------------------------------------ #
    # Callbacks
    # ------------------------------------------------------------------ #
    def on_t0_sample(self, sample: Any) -> Any:
        # Update addon modules.
        for module in list(self.modules):
            try:
                module.update(sample)
            except Exception:
                pass

        # Compute verdict from sample.
        try:
            signals = VerdictSignals(
                throughput_mbps=None,
                ping_avg_ms=_to_float(_attr(sample, "ping_avg_ms", default=0.0)),
                jitter_ms=_to_float(_attr(sample, "jitter_ms", default=0.0)),
                signal_dbm=_to_float(_attr(sample, "signal_dbm", default=0.0)),
                rx_dropped_rate=_to_float(_attr(sample, "rx_dropped_rate", default=0.0)),
            )
            self.verdict = compute_verdict(signals)
        except Exception as exc:
            logger.debug("Verdict compute failed: %s", exc)

        self._last_sample = sample

        # Update panel.
        if self.panel is not None:
            try:
                self.panel.update(
                    sample=sample,
                    verdict=self.verdict,
                    probe_result=self.probe_result,
                    devices=self.devices,
                )
            except Exception:
                try:
                    self.panel.update(sample, self.verdict, self.probe_result, self.devices)
                except Exception:
                    pass

        # Heartbeat update (expanded panel handles via panel.update, but ensure).
        try:
            hb = self.heartbeat
            if hb is not None and hasattr(hb, "add_sample"):
                value = _attr(sample, "rx_bps", "rx_mbps", default=0.0)
                try:
                    value = float(value) / 1e6 if value is not None else 0.0
                except Exception:
                    value = 0.0
                hb.add_sample(value)
        except Exception:
            pass

        # GLib idle callbacks should not repeat.
        return False

    def on_probe_complete(self, result: Any) -> Any:
        self.probe_result = result
        try:
            self.probe_history.append(result)
        except Exception:
            pass

        # Update verdict using probe throughput + last T0 latency.
        try:
            down = _attr(result, "down_mbps", default=None)
            sample = self._last_sample
            signals = VerdictSignals(
                throughput_mbps=_to_float(down, 0.0) if down is not None else None,
                ping_avg_ms=_to_float(_attr(sample, "ping_avg_ms", default=0.0)),
                jitter_ms=_to_float(_attr(sample, "jitter_ms", default=0.0)),
                signal_dbm=_to_float(_attr(sample, "signal_dbm", default=0.0)),
                rx_dropped_rate=_to_float(_attr(sample, "rx_dropped_rate", default=0.0)),
            )
            self.verdict = compute_verdict(signals)
        except Exception as exc:
            logger.debug("Probe verdict failed: %s", exc)

        if self.panel is not None:
            try:
                self.panel.update(
                    sample=self._last_sample,
                    verdict=self.verdict,
                    probe_result=self.probe_result,
                    devices=self.devices,
                )
            except Exception:
                try:
                    self.panel.set_verdict(self.verdict)
                except Exception:
                    pass

        return False

    def on_quit(self) -> None:
        if self._quitting:
            return
        self._quitting = True

        # Stop T0 monitor.
        if self.t0_monitor is not None:
            try:
                self.t0_monitor.stop()
            except Exception:
                pass
            self.t0_monitor = None

        # Cancel probe timer.
        if self._probe_timer_id is not None:
            try:
                GLib.source_remove(self._probe_timer_id)
            except Exception:
                pass
            self._probe_timer_id = None

        # Join probe thread.
        thread = self._probe_thread
        if thread is not None and thread.is_alive():
            try:
                thread.join(timeout=2)
            except Exception:
                pass

        # Save state (best effort; nothing persisted yet).
        logger.debug("nst shutting down")

    # ------------------------------------------------------------------ #
    # run override for graceful no-display handling
    # ------------------------------------------------------------------ #
    def run(self, *args: Any, **kwargs: Any) -> int:
        try:
            display = Gdk.Display.get_default()
        except Exception:
            display = None
        # If no display and no env display, warn but still delegate.
        if display is None and not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
            logger.warning("No display available; exiting")
            return 1
        return super().run(*args, **kwargs)


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        if isinstance(value, bool):
            return float(int(value))
        return float(value)
    except (TypeError, ValueError):
        return default
