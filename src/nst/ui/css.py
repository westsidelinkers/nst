"""Tokyo Night CSS for the nst panel."""

# Keep this module importable without GTK/GI at import time; GTK is only
# needed when actually installing the CSS provider.


CSS = r"""
window {
    background: transparent;
}

.nst-panel {
    background: transparent;
    color: #c0caf5;
    border-radius: 8px;
    border: 1px solid #414868;
    box-shadow: 0 0 12px rgba(122, 162, 247, 0.35);
    background-image: repeating-linear-gradient(
        to bottom,
        transparent 0px,
        transparent 2px,
        rgba(192, 202, 245, 0.04) 2px,
        rgba(192, 202, 245, 0.04) 4px
    );
    animation: nst-scanline 6s linear infinite;
}

window { background: transparent; }

.nst-verdict-healthy { color: #9ece6a; }
.nst-verdict-warn { color: #e0af68; }
.nst-verdict-bad { color: #f7768e; }

/* Musical bars */
.nst-bar {
    background: #414868;
    border-radius: 2px;
    min-height: 4px;
    transition: min-height 200ms ease-out;
    transform-origin: bottom;
}

.nst-bar--w-0 { min-width: 0px; }
.nst-bar--w-5 { min-width: 10px; }
.nst-bar--w-10 { min-width: 20px; }
.nst-bar--w-15 { min-width: 30px; }
.nst-bar--w-20 { min-width: 40px; }
.nst-bar--w-25 { min-width: 50px; }
.nst-bar--w-30 { min-width: 60px; }
.nst-bar--w-35 { min-width: 70px; }
.nst-bar--w-40 { min-width: 80px; }
.nst-bar--w-45 { min-width: 90px; }
.nst-bar--w-50 { min-width: 100px; }
.nst-bar--w-55 { min-width: 110px; }
.nst-bar--w-60 { min-width: 120px; }
.nst-bar--w-65 { min-width: 130px; }
.nst-bar--w-70 { min-width: 140px; }
.nst-bar--w-75 { min-width: 150px; }
.nst-bar--w-80 { min-width: 160px; }
.nst-bar--w-85 { min-width: 170px; }
.nst-bar--w-90 { min-width: 180px; }
.nst-bar--w-95 { min-width: 190px; }
.nst-bar--w-100 { min-width: 200px; }

.nst-good, .nst-state-good, .nst-bar.nst-good { background: #9ece6a; }
.nst-warn, .nst-state-warn, .nst-bar.nst-warn { background: #e0af68; }
.nst-bad, .nst-state-bad, .nst-bar.nst-bad { background: #f7768e; }

@keyframes nst-bar-pulse {
    0% { transform: scaleY(0.85); }
    50% { transform: scaleY(1.15); }
    100% { transform: scaleY(0.85); }
}

@keyframes nst-scanline {
    0% { background-position: 0 0; }
    100% { background-position: 0 4px; }
}

.nst-bar.nst-animate {
    animation: nst-bar-pulse 1.2s ease-in-out infinite;
    transform-origin: bottom;
}

.nst-tile {
    background: transparent;
    color: #c0caf5;
}

.nst-tile--flash {
    animation: nst-bar-pulse 0.4s ease-in-out 1;
}

.nst-corner-bracket {
    color: #7aa2f7;
    font-family: monospace;
}

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
    Handles a missing display/GTK gracefully.
    """
    try:
        import gi

        gi.require_version("Gtk", "4.0")
        from gi.repository import Gtk
    except Exception:
        return None

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


def animations_enabled(reduced_motion=False, on_battery=False, battery_pct=100.0,
                      battery_threshold=30, config=None):
    """Decide whether non-essential animations should run.

    Returns False when reduced motion is requested OR when on battery and
    battery percentage is below the threshold.
    """
    try:
        if config is not None:
            battery_threshold = getattr(config, "battery_threshold", battery_threshold)
            if getattr(config, "animation_enabled", True) is False:
                return False
    except Exception:
        pass
    try:
        if bool(reduced_motion):
            return False
        if bool(on_battery) and float(battery_pct) < float(battery_threshold):
            return False
    except Exception:
        pass
    return True


def should_animate(*args, **kwargs):
    return animations_enabled(*args, **kwargs)


__all__ = ["CSS", "install_css", "animations_enabled", "should_animate"]
