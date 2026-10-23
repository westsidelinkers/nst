import pytest
import os

pytestmark = pytest.mark.skipif(
    not (os.environ.get("WAYLAND_DISPLAY") or os.environ.get("DISPLAY")),
    reason="No display available"
)

def test_app_import():
    from nst.app import NstApplication
    assert NstApplication is not None

def test_app_creates_panel():
    from nst.app import NstApplication
    app = NstApplication()
    # do_activate requires a display; just check the class
    assert hasattr(app, "do_activate")
