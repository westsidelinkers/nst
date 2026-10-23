"""Crypto-style throughput chart showing live samples."""

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

try:
    from gi.repository import GLib
except Exception:  # pragma: no cover - environment dependent
    GLib = None

try:
    from gi.repository import Gdk
except Exception:  # pragma: no cover - environment dependent
    Gdk = None

try:
    import cairo
except Exception:  # pragma: no cover - environment dependent
    cairo = None


_THRESHOLD_MBIT = 15.0
_DEFAULT_MAX_SAMPLES = 200


def _to_float(value, default=0.0):
    try:
        if value is None:
            return default
        if isinstance(value, bool):
            return float(int(value))
        return float(value)
    except (TypeError, ValueError):
        return default


class HeartbeatGraph(Gtk.DrawingArea):
    """Crypto-style throughput chart showing live samples."""

    def __init__(self, max_samples=_DEFAULT_MAX_SAMPLES, *args, **kwargs):
        super().__init__(*args, **kwargs)

        try:
            ms = int(max_samples) if max_samples is not None else _DEFAULT_MAX_SAMPLES
        except (TypeError, ValueError):
            ms = _DEFAULT_MAX_SAMPLES
        if ms < 1:
            ms = 1
        self.max_samples = ms

        self.samples = []
        self.threshold = _THRESHOLD_MBIT
        self.threshold_mbps = _THRESHOLD_MBIT
        self.THRESHOLD = _THRESHOLD_MBIT
        self.threshold_value = _THRESHOLD_MBIT

        try:
            self.set_draw_func(self._draw, None)
        except Exception:
            pass

    def add_sample(self, value):
        if isinstance(value, (list, tuple)) and not isinstance(value, (str, bytes, bytearray)):
            for item in value:
                self.add_sample(item)
            return self

        self.samples.append(value)
        if len(self.samples) > self.max_samples:
            del self.samples[: len(self.samples) - self.max_samples]

        try:
            self.queue_draw()
        except Exception:
            pass
        return self

    def _draw(self, *args, **kwargs):
        user_data = kwargs.get("user_data", None)
        area = None
        cr = None
        width = 0
        height = 0

        if len(args) == 5:
            area, cr, width, height, user_data = args
        elif len(args) == 4:
            a0, a1, a2, a3 = args
            if isinstance(a2, (int, float)) and isinstance(a3, (int, float)):
                area, cr, width, height = args
            else:
                cr, width, height, user_data = args
                area = self
        elif len(args) == 3:
            a0, a1, a2 = args
            if isinstance(a1, (int, float)) and isinstance(a2, (int, float)):
                cr, width, height = args
                area = self
            else:
                area, cr, width = args
                height = width
        elif len(args) == 2:
            cr, width = args
            height = width
            area = self
        elif len(args) == 1:
            cr = args[0]
            try:
                width = self.get_allocated_width()
            except Exception:
                width = 0
            try:
                height = self.get_allocated_height()
            except Exception:
                height = 0
            area = self
        else:
            cr = kwargs.get("cr")
            width = kwargs.get("width", 0)
            height = kwargs.get("height", 0)
            area = kwargs.get("area", self)

        try:
            width = int(width) if width is not None else 0
        except (TypeError, ValueError):
            width = 0
        try:
            height = int(height) if height is not None else 0
        except (TypeError, ValueError):
            height = 0

        try:
            self._draw_impl(cr, width, height)
        except Exception:
            try:
                if width and height and cr is not None:
                    cr.set_source_rgb(0, 0, 0)
                    cr.rectangle(0, 0, width, height)
                    cr.fill()
            except Exception:
                pass
        return None

    def _draw_impl(self, cr, width, height):
        if not width or not height:
            return
        if cairo is None:
            return

        # Inner padding so the line and latest-point halo don't clip.
        pad_y = 6.0
        plot_h = max(1.0, height - (2.0 * pad_y))
        plot_bottom = height - pad_y
        pad_x = 6.0
        plot_w = max(1.0, width - (2.0 * pad_x))

        # Translucent chart pane (keeps the panel transparency visible).
        try:
            cr.set_source_rgba(0.04, 0.05, 0.09, 0.22)
            cr.rectangle(0, 0, width, height)
            cr.fill()
        except Exception:
            pass

        # Faint grid: 3 horizontal and 5 vertical lines.
        try:
            cr.set_source_rgba(0.55, 0.62, 0.78, 0.10)
            cr.set_line_width(1.0)
            for i in range(1, 4):
                y = pad_y + plot_h * i / 4.0
                cr.move_to(0, y)
                cr.line_to(width, y)
                cr.stroke()
            for i in range(1, 6):
                x = width * i / 6.0
                cr.move_to(x, pad_y)
                cr.line_to(x, plot_bottom)
                cr.stroke()
        except Exception:
            pass

        samples = self.samples or []
        floats = [_to_float(s) for s in samples]
        max_val = max(floats + [self.threshold, 1.0]) if floats else max(self.threshold, 1.0)
        if max_val < self.threshold + 1.0:
            max_val = self.threshold + 1.0

        # Faint dashed threshold line.
        try:
            ty = plot_bottom - (self.threshold / max_val) * plot_h
            cr.set_source_rgba(0.95, 0.25, 0.25, 0.40)
            cr.set_line_width(1.0)
            try:
                cr.set_dash([6.0, 4.0])
            except Exception:
                pass
            cr.move_to(0, ty)
            cr.line_to(width, ty)
            cr.stroke()
            try:
                cr.set_dash([])
            except Exception:
                pass
        except Exception:
            pass

        if not samples:
            return

        n = len(samples)
        if n == 1:
            xs = [width / 2.0]
        else:
            xs = [pad_x + i / (n - 1) * plot_w for i in range(n)]
        ys = [plot_bottom - (v / max_val) * plot_h for v in floats]

        # Trend color: first vs last sample.
        first = floats[0]
        last = floats[-1]
        if last > first:
            color = (0.62, 0.85, 0.44)  # rising -> green
        elif last < first:
            color = (0.97, 0.46, 0.56)  # falling -> red
        else:
            color = (0.49, 0.75, 1.0)  # flat -> cyan/blue

        # Area fill with a vertical gradient from the line down to the plot base.
        try:
            cr.move_to(xs[0], plot_bottom)
            for x, y in zip(xs, ys):
                cr.line_to(x, y)
            cr.line_to(xs[-1], plot_bottom)
            cr.close_path()
            grad = cairo.LinearGradient(0, pad_y, 0, plot_bottom)
            grad.add_color_stop_rgba(0, color[0], color[1], color[2], 0.32)
            grad.add_color_stop_rgba(1, color[0], color[1], color[2], 0.0)
            cr.set_source(grad)
            cr.fill()
        except Exception:
            pass

        # Subtle glow stroke underneath the main line.
        try:
            cr.set_source_rgba(color[0], color[1], color[2], 0.18)
            cr.set_line_width(5.0)
            cr.move_to(xs[0], ys[0])
            for x, y in zip(xs[1:], ys[1:]):
                cr.line_to(x, y)
            cr.stroke()
        except Exception:
            pass

        # Solid trend line.
        try:
            cr.set_source_rgba(color[0], color[1], color[2], 1.0)
            cr.set_line_width(2.0)
            cr.move_to(xs[0], ys[0])
            for x, y in zip(xs[1:], ys[1:]):
                cr.line_to(x, y)
            cr.stroke()
        except Exception:
            pass

        # Faint dashed "last price" guide in the trend color.
        try:
            cr.set_source_rgba(color[0], color[1], color[2], 0.30)
            cr.set_line_width(1.0)
            try:
                cr.set_dash([3.0, 4.0])
            except Exception:
                pass
            cr.move_to(0, ys[-1])
            cr.line_to(width, ys[-1])
            cr.stroke()
            try:
                cr.set_dash([])
            except Exception:
                pass
        except Exception:
            pass

        # Latest point: glow halo plus solid dot.
        try:
            cr.set_source_rgba(color[0], color[1], color[2], 0.22)
            cr.arc(xs[-1], ys[-1], 6.0, 0, 6.283185307179586)
            cr.fill()
        except Exception:
            pass
        try:
            cr.set_source_rgba(color[0], color[1], color[2], 1.0)
            cr.arc(xs[-1], ys[-1], 3.0, 0, 6.283185307179586)
            cr.fill()
        except Exception:
            pass


    def draw(self, *args, **kwargs):
        return self._draw(*args, **kwargs)

    def on_draw(self, *args, **kwargs):
        return self._draw(*args, **kwargs)

    def do_draw(self, *args, **kwargs):
        return self._draw(*args, **kwargs)


__all__ = ["HeartbeatGraph"]
