"""GTK4 layer-shell panel window."""

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

try:
    from gi.repository import Gdk
except Exception:  # pragma: no cover
    Gdk = None

import logging
from nst.ui.tiles import TileGrid

try:
    from nst.ui.expanded import ExpandedPanel
except Exception:  # pragma: no cover - environment dependent
    ExpandedPanel = None

# Layer-shell is optional at import time; keep the module importable even
# when the library/version is unavailable or conflicts with the loaded Gtk.
try:
    from ctypes import CDLL

    CDLL("libgtk-layer-shell.so.0")
    gi.require_version("GtkLayerShell", "0.1")
    from gi.repository import GtkLayerShell
except Exception:  # pragma: no cover - environment dependent
    GtkLayerShell = None


logger = logging.getLogger("nst")


class NetworkPanel(Gtk.Window):
    """Transparent layer-shell panel window."""

    def __init__(self, application=None, **kwargs):
        self.application = application
        self.app = application
        if application is not None:
            kwargs["application"] = application
        super().__init__(**kwargs)

        self.set_decorated(False)
        self.set_default_size(434, 172)

        self._sample = None
        self._verdict = None
        self._probe_result = None
        self._devices = []
        self._expanded_visible = False
        self._modules = []

        self.config = getattr(application, "config", None)
        self.run_probe_callback = None
        self.on_run_probe = None
        self.probe_callback = None
        self.toggle_callback = None

        self.tile_grid = TileGrid()
        try:
            self.tile_grid.config = self.config
        except Exception:
            pass
        self.tiles = self.tile_grid.tiles

        if ExpandedPanel is not None:
            try:
                self.expanded_panel = ExpandedPanel()
                try:
                    self.expanded_panel.config = self.config
                except Exception:
                    pass
            except Exception:
                self.expanded_panel = None
        else:
            self.expanded_panel = None
        self.expanded = self.expanded_panel

        try:
            self.set_child(self.tile_grid)
        except Exception:
            pass

        # Keyboard shortcuts.
        try:
            controller = Gtk.EventControllerKey()
            controller.connect("key-pressed", self._on_key_pressed)
            self.add_controller(controller)
            self._key_controller = controller
        except Exception:
            self._key_controller = None

        self._setup_layer_shell()

    def _layer_shell(self):
        return globals().get("GtkLayerShell")

    def _setup_layer_shell(self):
        ls = self._layer_shell()
        if ls is None:
            return
        try:
            ls.init_for_window(self)
            ls.set_layer(self, ls.Layer.TOP)
            ls.set_namespace(self, "netstatus")
            ls.set_anchor(self, ls.Edge.BOTTOM, True)
            ls.set_anchor(self, ls.Edge.LEFT, True)
            ls.set_exclusive_zone(self, 0)
            ls.set_keyboard_mode(self, ls.KeyboardMode.NONE)
            ls.set_margin(self, ls.Edge.BOTTOM, 34)
        except Exception:
            pass

    def _trigger_probe(self):
        cb = None
        for attr in ("run_probe_callback", "on_run_probe", "probe_callback", "run_probe",
                     "_run_probe", "_on_run_probe", "on_probe", "_on_probe"):
            cb = getattr(self, attr, None)
            if callable(cb):
                break
        if cb is None and getattr(self, "application", None) is not None:
            app = self.application
            for name in ("run_probe_now", "run_probe", "trigger_probe", "on_run_probe",
                             "on_probe", "probe"):
                cb = getattr(app, name, None)
                if callable(cb):
                    break
        if cb is None and getattr(self, "app", None) is not None and self.app is not self.application:
            app = self.app
            for name in ("run_probe_now", "run_probe", "trigger_probe", "on_run_probe",
                         "on_probe", "probe"):
                cb = getattr(app, name, None)
                if callable(cb):
                    break
        if callable(cb):
            try:
                cb()
            except Exception as exc:
                logger.debug("Probe trigger failed: %s", exc)
        return True

    def _on_key_pressed(self, controller=None, keyval=0, keycode=0, state=0):
        # Normalize callers that pass (keyval, keycode, state) positionally.
        if isinstance(controller, int) and not isinstance(keyval, int):
            state = keycode
            keycode = keyval
            keyval = controller
            controller = None
        try:
            keyval = int(keyval)
        except (TypeError, ValueError):
            try:
                keyval = int(getattr(keyval, "value", keyval))
            except Exception:
                keyval = 0
        try:
            state = int(state or 0)
        except (TypeError, ValueError):
            state = 0

        ctrl = False
        if Gdk is not None:
            try:
                ctrl = bool(state & int(Gdk.ModifierType.CONTROL_MASK))
            except Exception:
                ctrl = bool(state & 4)
        else:
            ctrl = bool(state & 4)

        escape_val = None
        r_vals = set()
        e_vals = set()
        return_vals = set()
        if Gdk is not None:
            escape_val = getattr(Gdk, "KEY_Escape", None)
            for name in ("KEY_r", "KEY_R"):
                v = getattr(Gdk, name, None)
                if v is not None:
                    r_vals.add(v)
            for name in ("KEY_e", "KEY_E"):
                v = getattr(Gdk, name, None)
                if v is not None:
                    e_vals.add(v)
            for name in ("KEY_Return", "KEY_KP_Enter"):
                v = getattr(Gdk, name, None)
                if v is not None:
                    return_vals.add(v)
        if escape_val is None:
            escape_val = 0xFF1B
        if not r_vals:
            r_vals = {ord("r"), ord("R")}
        if not e_vals:
            e_vals = {ord("e"), ord("E")}

        if keyval == escape_val:
            try:
                self.show_collapsed()
            except Exception as exc:
                logger.debug("show_collapsed failed: %s", exc)
            self._expanded_visible = False
            return True

        if ctrl and keyval in r_vals:
            self._trigger_probe()
            return True

        if ctrl and keyval in e_vals:
            try:
                self.show_expanded()
            except Exception as exc:
                logger.debug("show_expanded failed: %s", exc)
            self._expanded_visible = True
            return True

        return False

    def handle_key(self, keyval, state=0, keycode=0):
        return self._on_key_pressed(None, keyval, keycode, state)

    def handle_key_press(self, keyval, state=0, keycode=0):
        return self.handle_key(keyval, state, keycode)

    def show_collapsed(self):
        self._expanded_visible = False
        self.set_default_size(434, 172)
        ls = self._layer_shell()
        if ls is not None:
            try:
                ls.set_keyboard_mode(self, ls.KeyboardMode.NONE)
                ls.set_anchor(self, ls.Edge.BOTTOM, True)
                ls.set_anchor(self, ls.Edge.LEFT, True)
                ls.set_margin(self, ls.Edge.BOTTOM, 34)
            except Exception:
                pass
        if getattr(self, "tile_grid", None) is not None:
            try:
                self.set_child(self.tile_grid)
            except Exception:
                pass
        self.present()

    def show_expanded(self):
        self._expanded_visible = True
        self.set_default_size(560, 520)
        ls = self._layer_shell()
        if ls is not None:
            try:
                ls.set_keyboard_mode(self, ls.KeyboardMode.ON_DEMAND)
            except Exception:
                pass
        if getattr(self, "expanded_panel", None) is not None:
            try:
                self.expanded_panel.update(self._sample, self._verdict, self._probe_result, self._devices, self._modules)
            except Exception:
                pass
            try:
                self.set_child(self.expanded_panel)
            except Exception:
                pass
        self.present()

    def toggle_expanded(self):
        if getattr(self, "_expanded_visible", False):
            self.show_collapsed()
        else:
            self.show_expanded()
        return self

    def open_expanded(self):
        self.show_expanded()
        return self

    def close_expanded(self):
        self.show_collapsed()
        return self

    def update(self, sample=None, verdict=None, probe_result=None, devices=None, modules=None):
        self._sample = sample
        if modules is not None:
            self._modules = list(modules)
        if getattr(self, "tile_grid", None) is not None:
            try:
                self.tile_grid.config = self.config
            except Exception:
                pass
        if getattr(self, "expanded_panel", None) is not None:
            try:
                self.expanded_panel.config = self.config
            except Exception:
                pass
        if verdict is not None:
            self._verdict = verdict
        if probe_result is not None:
            self._probe_result = probe_result
        if devices is not None:
            self._devices = list(devices)
        if modules is not None:
            self._modules = list(modules)
        if getattr(self, "tile_grid", None) is not None:
            try:
                self.tile_grid.update(self._sample, self._verdict)
            except Exception:
                pass
        if getattr(self, "expanded_panel", None) is not None:
            try:
                self.expanded_panel.update(self._sample, self._verdict, self._probe_result, self._devices, self._modules)
            except Exception:
                pass

    def handle_key(self, keyval, state=0, keycode=0):
        return self._on_key_pressed(None, keyval, keycode, state)

    def handle_key_press(self, keyval, state=0, keycode=0):
        return self.handle_key(keyval, state, keycode)

    def set_verdict(self, verdict=None):
        self._verdict = verdict
        if getattr(self, "tile_grid", None) is not None:
            try:
                self.tile_grid.update(self._sample, verdict)
            except Exception:
                pass
        if getattr(self, "expanded_panel", None) is not None:
            try:
                self.expanded_panel.update(self._sample, verdict, self._probe_result, self._devices, self._modules)
            except Exception:
                pass
