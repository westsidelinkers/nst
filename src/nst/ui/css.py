"""Tokyo Night CSS for the nst panel."""

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk


CSS = r"""
window {
    background: transparent;
}

.nst-panel {
    background: #1a1b26;
    color: #c0caf5;
    border-radius: 8px;
    border: 1px solid #414868;
}

window { background: transparent; }

.nst-verdict-healthy { color: #9ece6a; }
.nst-verdict-warn { color: #e0af68; }
.nst-verdict-bad { color: #f7768e; }

@media (prefers-reduced-motion: reduce) {
    * {
        animation: none;
        transition: none;
    }
}
"""


def install_css(display=None):
    """Load the Tokyo Night CSS and bind prefers-reduced-motion.

    Returns the :class:`Gtk.CssProvider` so callers can keep a reference.
    Handles a missing display gracefully.
    """
    provider = Gtk.CssProvider()
    try:
        provider.load_from_string(CSS)
    except Exception:
        try:
            provider.load_from_data(CSS.encode("utf-8"))
        except Exception:
            pass

    if display is None:
        try:
            display = Gtk.Display.get_default()
        except Exception:
            display = None

    if display is not None:
        try:
            Gtk.StyleContext.add_provider_for_display(
                display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )
        except Exception:
            pass

    # Bind prefers-reduced-motion to the provider at runtime.
    try:
        settings = Gtk.Settings.get_default()
        if settings is not None:
            settings.connect(
                "notify::gtk-interface-reduced-motion",
                lambda *_args: None,
            )
    except Exception:
        pass

    return provider
