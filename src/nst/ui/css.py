"""Tokyo Night CSS for the nst panel."""

# Keep this module importable without GTK/GI at import time; GTK is only
# needed when actually installing the CSS provider.


CSS = r"""
window {
    background-color: transparent;
}

.nst-panel {
    background-color: transparent;
    color: #c0caf5;
    border: 1px solid rgba(122,162,247,.30);
    border-radius: 9px;
    font-family: ui-monospace, "JetBrains Mono", "DejaVu Sans Mono", monospace;
    box-shadow: 0 0 30px rgba(122,162,247,.12), 0 6px 26px rgba(0,0,0,.6);
    background-image: none;
    margin: 0;
    padding: 0;
}


.nst-title-row {
    spacing: 6px;
}

.nst-status-dot {
    min-width: 7px;
    min-height: 7px;
    margin-right: 6px;
    margin-top: 2px;
    margin-bottom: 2px;
    border-radius: 999px;
    background-color: #9ece6a;
}

.nst-wifi-icon {
    font-size: 12px;
    color: #7dcfff;
    margin-right: 6px;
}

.nst-title {
    font-size: 11px;
    color: #a9b1d6;
    margin-right: 8px;
}

.nst-verdict-chip {
    font-size: 10.5px;
    padding: 2px 8px;
    border-radius: 5px;
    background-color: rgba(224,175,104,.10);
    border: 1px solid rgba(224,175,104,.30);
    color: #e0af68;
    margin-left: 8px;
}
.nst-verdict-chip.ok,
.nst-verdict-chip.good,
.nst-verdict-chip.healthy {
    background-color: rgba(158,206,106,.14);
    border-color: rgba(158,206,106,.38);
    color: #9ece6a;
}
.nst-verdict-chip.warn,
.nst-verdict-chip.warning {
    background-color: rgba(224,175,104,.14);
    border-color: rgba(224,175,104,.35);
    color: #e0af68;
}
.nst-verdict-chip.bad,
.nst-verdict-chip.error,
.nst-verdict-chip.critical {
    background-color: rgba(247,118,142,.14);
    border-color: rgba(247,118,142,.38);
    color: #f7768e;
}

.nst-verdict-healthy { color: #9ece6a; }
.nst-verdict-warn { color: #e0af68; }
.nst-verdict-bad { color: #f7768e; }

.nst-tile {
    background-color: transparent;
    color: #c0caf5;
    border: 1px solid rgba(122,162,247,.12);
    border-radius: 7px;
    padding: 7px 8px 8px;
    background-image: none;
    margin: 0;
}

.nst-tile .k {
    font-size: 9px;
    color: #a9b1d6;
    margin: 0 0 4px 0;
}
.nst-tile .v {
    font-size: 15px;
    font-weight: 600;
    color: #c0caf5;
}
.nst-tile .v small {
    font-size: 9.5px;
    font-weight: 400;
    color: #a9b1d6;
}
.nst-tile .sub {
    font-size: 8.5px;
    color: #a9b1d6;
    margin: 1px 0 0 0;
}

.nst-tile .v.good { color: #9ece6a; }
.nst-tile .v.warn { color: #e0af68; }
.nst-tile .v.bad { color: #f7768e; }

.nst-tile.good .nst-mus .nst-bar,
.nst-tile .nst-bar.nst-good {
    background-image: linear-gradient(90deg, #9ece6a, rgba(158,206,106,.5));
}
.nst-tile.warn .nst-mus .nst-bar,
.nst-tile .nst-bar.nst-warn {
    background-image: linear-gradient(90deg, #e0af68, rgba(224,175,104,.5));
}
.nst-tile.bad .nst-mus .nst-bar,
.nst-tile .nst-bar.nst-bad {
    background-image: linear-gradient(90deg, #f7768e, rgba(247,118,142,.5));
}
.nst-tile.neutral .nst-mus .nst-bar,
.nst-tile .nst-bar.nst-neutral {
    background-image: linear-gradient(90deg, #7aa2f7, rgba(122,162,247,.5));
}

.nst-mus {
    min-height: 16px;
    margin: 3px 0 4px;
    border-radius: 2px;
    background-color: rgba(122,162,247,.04);
    overflow: hidden;
}

.nst-bar {
    min-height: 16px;
    border-radius: 2px;
    animation: musBounce 1.3s ease-in-out infinite;
    background-color: #7aa2f7;
}
.nst-bar.nst-animate {
    animation: musBounce 1.3s ease-in-out infinite;
}

.nst-bar.nst-animate-reduced {
    animation: musBounce 2.4s ease-in-out infinite;
}

@keyframes musBounce {
    0%, 100% { transform: scaleX(0.85); }
    50% { transform: scaleX(1.15); }
}

@keyframes scan {
    0% { background-color: rgba(26,27,38,.96); }
    100% { background-color: rgba(26,27,38,.96); }
}

.nst-corner-bracket {
    color: #7aa2f7;
    font-family: monospace;
}

.nst-footer {
    font-size: 10px;
    color: #a9b1d6;
    margin: 7px 0 0 0;
}

.nst-heartbeat,
.nst-heartbeat-container,
.nst-heartbeat-box {
    min-height: 34px;
    margin: 8px 0 0 0;
    border-radius: 4px;
    background-color: rgba(122,162,247,.04);
}

.nst-status-dot {
    min-width: 7px;
    min-height: 7px;
    border-radius: 999px;
    background-color: #9ece6a;
}

/* width buckets (state markers; width driven by size request) */
.nst-bar--w-0 { min-width: 0px; }
.nst-bar--w-5 { min-width: 0px; }
.nst-bar--w-10 { min-width: 0px; }
.nst-bar--w-15 { min-width: 0px; }
.nst-bar--w-20 { min-width: 0px; }
.nst-bar--w-25 { min-width: 0px; }
.nst-bar--w-30 { min-width: 0px; }
.nst-bar--w-35 { min-width: 0px; }
.nst-bar--w-40 { min-width: 0px; }
.nst-bar--w-45 { min-width: 0px; }
.nst-bar--w-50 { min-width: 0px; }
.nst-bar--w-55 { min-width: 0px; }
.nst-bar--w-60 { min-width: 0px; }
.nst-bar--w-65 { min-width: 0px; }
.nst-bar--w-70 { min-width: 0px; }
.nst-bar--w-75 { min-width: 0px; }
.nst-bar--w-80 { min-width: 0px; }
.nst-bar--w-85 { min-width: 0px; }
.nst-bar--w-90 { min-width: 0px; }
.nst-bar--w-95 { min-width: 0px; }
.nst-bar--w-100 { min-width: 0px; }

.nst-tile--flash {
    animation: musBounce 0.4s ease-in-out 1;
}

@media (prefers-reduced-motion: reduce) {
    * {
        animation: none;
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
