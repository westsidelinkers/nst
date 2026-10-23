import pytest
import os

pytestmark = pytest.mark.skipif(
    not (os.environ.get("WAYLAND_DISPLAY") or os.environ.get("DISPLAY")),
    reason="No display available"
)

def test_tile_grid_import():
    from nst.ui.tiles import TileGrid
    assert TileGrid is not None

def test_tile_grid_creates_six_tiles():
    from nst.ui.tiles import TileGrid
    import gi
    gi.require_version("Gtk", "4.0")
    from gi.repository import Gtk
    grid = TileGrid()
    assert len(grid.tiles) == 6
    assert "DOWN" in grid.tiles
    assert "CPU" in grid.tiles
    assert "DISK" in grid.tiles
