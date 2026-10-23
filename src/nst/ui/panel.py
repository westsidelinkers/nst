"""GTK4 layer-shell panel window."""

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from nst.ui.tiles import TileGrid

# Layer-shell is optional at import time; keep the module importable even
# when the library/version is unavailable or conflicts with the loaded Gtk.
try:
    from ctypes import CDLL

    CDLL("libgtk-layer-shell.so.0")
    gi.require_version("GtkLayerShell", "0.1")
    from gi.repository import GtkLayerShell
except Exception:  # pragma: no cover - environment dependent
    GtkLayerShell = None


class NetworkPanel(Gtk.Window):
    """Transparent layer-shell panel window."""

    def __init__(self, application=None, **kwargs):
        if application is not None:
            kwargs["application"] = application
        super().__init__(**kwargs)

        self.set_decorated(False)
        self.set_default_size(434, 172)

        self._sample = None
        self._verdict = None

        self.tile_grid = TileGrid()
        self.tiles = self.tile_grid.tiles

        try:
            self.set_child(self.tile_grid)
        except Exception:
            pass

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

    def show_collapsed(self):
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
        self.present()

    def show_expanded(self):
        self.set_default_size(560, 520)
        ls = self._layer_shell()
        if ls is not None:
            try:
                ls.set_keyboard_mode(self, ls.KeyboardMode.ON_DEMAND)
            except Exception:
                pass
        self.present()

    def update(self, sample=None):
        self._sample = sample
        if getattr(self, "tile_grid", None) is not None:
            try:
                self.tile_grid.update(sample, self._verdict)
            except Exception:
                pass

    def set_verdict(self, verdict=None):
        self._verdict = verdict
        if getattr(self, "tile_grid", None) is not None:
            try:
                self.tile_grid.update(self._sample, verdict)
            except Exception:
                pass
