from nst.addons.base import AddonModule, load_modules
from nst.config import Config

def test_addon_base_interface():
    class DummyAddon(AddonModule):
        name = "dummy"
        def update(self, sample):
            return {"value": 42}
        def render(self):
            import gi
            gi.require_version("Gtk", "4.0")
            from gi.repository import Gtk
            return Gtk.Label(label="dummy")
    addon = DummyAddon()
    assert addon.update(None) == {"value": 42}
    assert addon.name == "dummy"

def test_load_modules():
    cfg = Config(modules_enabled=["cpu", "battery"])
    modules = load_modules(cfg)
    names = [m.name for m in modules]
    assert "cpu" in names
    assert "battery" in names

def test_load_modules_empty():
    cfg = Config(modules_enabled=[])
    modules = load_modules(cfg)
    assert modules == []
