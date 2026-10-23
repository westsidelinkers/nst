import pytest
import os

pytestmark = pytest.mark.skipif(
    not (os.environ.get("WAYLAND_DISPLAY") or os.environ.get("DISPLAY")),
    reason="No display available"
)

def test_panel_import():
    from nst.ui.panel import NetworkPanel
    assert NetworkPanel is not None

def test_css_provider_loads():
    from nst.ui.css import install_css
    import gi
    gi.require_version("Gtk", "4.0")
    gi.require_version("Gdk", "4.0")
    from gi.repository import Gtk, Gdk
    display = Gdk.Display.get_default()
    if display is None:
        pytest.skip("No display")
    provider = install_css(display)
    assert provider is not None
