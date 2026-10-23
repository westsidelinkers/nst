"""Tokyo Night CSS for the nst panel."""

# Keep this module importable without GTK/GI at import time; GTK is only
# needed when actually installing the CSS provider.


CSS = r"""
window {
    background: transparent;
}

.nst-panel {
    background: rgba(26,27,38,.96);
    color: #c0caf5;
    border: 1px solid rgba(122,162,247,.30);
    border-radius: 9px;
    font-family: ui-monospace, "JetBrains Mono", "DejaVu Sans Mono", monospace;
    box-shadow: 0 0 30px rgba(122,162,247,.12), 0 6px 26px rgba(0,0,0,.6);
    position: relative;
    overflow: hidden;
    background-image: repeating-linear-gradient(
        0deg,
        transparent 0px,
        transparent 3px,
        rgba(122,162,247,.025) 3px,
        rgba(122,162,247,.025) 4px
    );
    animation: scan 6s linear infinite;
}

window { background: transparent; }

.nst-title {
    font-size: 11px;
    color: #a9b1d6;
    letter-spacing: .04em;
}

.nst-verdict-chip {
    font-size: 10.5px;
    padding: 2px 8px;
    border-radius: 5px;
    letter-spacing: .04em;
    background: rgba(224,175,104,.14);
    border: 1px solid rgba(224,175,104,.35);
    color: #e0af68;
}
.nst-verdict-chip.ok,
.nst-verdict-chip.good,
.nst-verdict-chip.healthy {
    background: rgba(158,206,106,.14);
    border-color: rgba(158,206,106,.38);
    color: #9ece6a;
}
.nst-verdict-chip.warn,
.nst-verdict-chip.warning {
    background: rgba(224,175,104,.14);
    border-color: rgba(224,175,104,.35);
    color: #e0af68;
}
.nst-verdict-chip.bad,
.nst-verdict-chip.error,
.nst-verdict-chip.critical {
    background: rgba(247,118,142,.14);
    border-color: rgba(247,118,142,.38);
    color: #f7768e;
}

.nst-verdict-healthy { color: #9ece6a; }
.nst-verdict-warn { color: #e0af68; }
.nst-verdict-bad { color: #f7768e; }

.nst-tile {
    background: rgba(122,162,247,.05);
    color: #c0caf5;
    border: 1px solid rgba(122,162,247,.08);
    border-radius: 7px;
    padding: 7px 8px 8px;
    position: relative;
    overflow: hidden;
}
.nst-tile::before {
    content: "";
    position: absolute;
    inset: 0;
    background: linear-gradient(180deg, rgba(122,162,247,.06) 0%, transparent 60%);
}

.nst-tile .k {
    font-size: 9px;
    color: #a9b1d6;
    letter-spacing: .05em;
    position: relative;
    margin-bottom: 4px;
}
.nst-tile .v {
    font-size: 15px;
    font-weight: 600;
    line-height: 1.25;
    position: relative;
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
    margin-top: 1px;
    position: relative;
}

.nst-tile .v.good { color: #9ece6a; }
.nst-tile .v.warn { color: #e0af68; }
.nst-tile .v.bad { color: #f7768e; }

.nst-tile.good .nst-mus .nst-bar,
.nst-tile .nst-bar.nst-good {
    background: linear-gradient(90deg, #9ece6a, rgba(158,206,106,.5));
}
.nst-tile.warn .nst-mus .nst-bar,
.nst-tile .nst-bar.nst-warn {
    background: linear-gradient(90deg, #e0af68, rgba(224,175,104,.5));
}
.nst-tile.bad .nst-mus .nst-bar,
.nst-tile .nst-bar.nst-bad {
    background: linear-gradient(90deg, #f7768e, rgba(247,118,142,.5));
}
.nst-tile.neutral .nst-mus .nst-bar,
.nst-tile .nst-bar.nst-neutral {
    background: linear-gradient(90deg, #7aa2f7, rgba(122,162,247,.5));
}

.nst-mus {
    height: 16px;
    position: relative;
    margin: 3px 0 4px;
    overflow: hidden;
    border-radius: 2px;
    background: rgba(122,162,247,.06);
}

.nst-bar {
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    border-radius: 2px;
    transform-origin: left center;
    animation: musBounce 1.3s ease-in-out infinite;
}
.nst-bar::after {
    content: "";
    position: absolute;
    inset: 0;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,.18), transparent);
    animation: sweep 1.8s linear infinite;
}

@keyframes musBounce {
    0%, 100% { transform: scaleX(.85); }
    50% { transform: scaleX(1.15); }
}

@keyframes nst-bar-pulse {
    0% { transform: scaleY(0.85); }
    50% { transform: scaleY(1.15); }
    100% { transform: scaleY(0.85); }
}
@keyframes sweep {
    0% { transform: translateX(-100%); }
    100% { transform: translateX(100%); }
}

@keyframes scan {
    0% { background-position: 0 0; }
    100% { background-position: 0 100%; }
}

@keyframes nst-scanline {
    0% { background-position: 0 0; }
    100% { background-position: 0 100%; }
}

.nst-bar.nst-animate {
    animation: musBounce 1.3s ease-in-out infinite;
    transform-origin: left center;
}

.nst-corner-bracket {
    color: #7aa2f7;
    font-family: monospace;
}

.nst-footer {
    display: flex;
    gap: 10px;
    font-size: 10px;
    color: #a9b1d6;
    margin-top: 7px;
    position: relative;
}

.nst-heartbeat,
.nst-heartbeat-container,
.nst-heartbeat-box {
    height: 34px;
    overflow: hidden;
    position: relative;
    margin-top: 8px;
    border-radius: 4px;
    background: rgba(122,162,247,.04);
}

.nst-status-dot {
    display: inline-block;
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: #9ece6a;
}

/* width buckets (min-width based) */
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

.nst-tile--flash {
    animation: musBounce 0.4s ease-in-out 1;
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
